import json
import re
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import processar_historico as hist

ROOT = Path(__file__).resolve().parents[1]


class NomeEDataTests(unittest.TestCase):
    def test_nomes_aceitos(self):
        self.assertEqual(hist.interpretar_nome("01.10"), (1, 10, None))
        self.assertEqual(hist.interpretar_nome("1.10"), (1, 10, None))
        self.assertEqual(hist.interpretar_nome("01-10-2026"), (1, 10, 2026))
        self.assertEqual(hist.interpretar_nome("01.10.26"), (1, 10, 2026))
        self.assertEqual(hist.interpretar_nome("2026-10-01"), (1, 10, 2026))

    def test_nomes_recusados(self):
        for nome in ("tabela_precos", "tabela 01.10", "anotacoes", "1"):
            self.assertIsNone(hist.interpretar_nome(nome), nome)

    def test_ano_deduzido_pela_vigencia(self):
        self.assertEqual(hist.resolver_data(1, 10, None, date(2026, 10, 21)), date(2026, 10, 1))
        # virada do ano: vigência em 30/12/2025, arquivo enviado como 02.01
        self.assertEqual(hist.resolver_data(2, 1, None, date(2025, 12, 30)), date(2026, 1, 2))
        self.assertEqual(hist.resolver_data(30, 12, None, date(2026, 1, 2)), date(2025, 12, 30))

    def test_data_invalida(self):
        self.assertIsNone(hist.resolver_data(31, 2, 2026, date(2026, 1, 1)))
        self.assertIsNone(hist.resolver_data(31, 2, None, date(2026, 1, 1)))


class ListagemTests(unittest.TestCase):
    def test_lista_ordenada_e_avisa_sobre_arquivos_fora_do_padrao(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp)
            for nome in ("08.10.xlsx", "01.10.xlsx", "~$01.10.xlsx", "anotacoes.xlsx", "leia-me.md"):
                (pasta / nome).write_bytes(b"")
            tabelas, avisos = hist.listar_tabelas(pasta, hoje=date(2026, 10, 22))
        self.assertEqual([t.data for t in tabelas], [date(2026, 10, 1), date(2026, 10, 8)])
        self.assertEqual(len(avisos), 1)
        self.assertIn("anotacoes.xlsx", avisos[0])

    def test_mesma_data_gera_aviso(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp)
            for nome in ("01.10.xlsx", "01.10.2026.xlsx"):
                (pasta / nome).write_bytes(b"")
            tabelas, avisos = hist.listar_tabelas(pasta, hoje=date(2026, 10, 22))
        self.assertEqual(len(tabelas), 1)
        self.assertEqual(len(avisos), 1)


class CodificacaoTests(unittest.TestCase):
    def setUp(self):
        self.tabelas = [
            (date(2026, 10, 1), "01.10.xlsx", {"A": {"PRÉ (Balcão)": 100.0, "TIM BLACK": 80.5}}),
            (date(2026, 10, 8), "08.10.xlsx", {"A": {"PRÉ (Balcão)": 100.0, "TIM BLACK": 79.0}, "B": {"PRÉ (Balcão)": 50.0}}),
            (date(2026, 10, 15), "15.10.xlsx", {"B": {"PRÉ (Balcão)": 55.0}}),
        ]

    def test_ida_e_volta(self):
        historico = hist.construir_historico(self.tabelas)
        esperado = [snapshot for _, _, snapshot in self.tabelas]
        self.assertEqual(hist.decodificar_historico(historico), esperado)

    def test_guarda_apenas_mudancas(self):
        historico = hist.construir_historico(self.tabelas)
        indice = historico["planos"].index("PRÉ (Balcão)")
        # A: preço igual nas duas primeiras tabelas e some na terceira
        self.assertEqual(historico["produtos"]["A"][str(indice)], [[0, 100], [2, None]])
        # B: só aparece na segunda tabela e muda na terceira
        self.assertEqual(historico["produtos"]["B"][str(indice)], [[1, 50], [2, 55]])

    def test_planos_sem_fidelizacao_vem_primeiro(self):
        historico = hist.construir_historico(self.tabelas)
        self.assertEqual(historico["planos"][0], "PRÉ (Balcão)")

    def test_saida_e_deterministica(self):
        self.assertEqual(
            hist.gerar_js(hist.construir_historico(self.tabelas)),
            hist.gerar_js(hist.construir_historico(self.tabelas)),
        )


class SincronizacaoTests(unittest.TestCase):
    def test_copia_apenas_quando_a_mais_recente_e_diferente(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp)
            nova = pasta / "08.10.xlsx"
            nova.write_bytes(b"nova")
            destino = pasta / "tabela_precos.xlsx"
            tabela = hist.Tabela(date(2026, 10, 8), nova)

            destino.write_bytes(b"antiga")
            self.assertTrue(hist.sincronizar_tabela_atual([tabela], destino))
            self.assertEqual(destino.read_bytes(), b"nova")
            self.assertFalse(hist.sincronizar_tabela_atual([tabela], destino))


class RepositorioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        texto = (ROOT / "historico.js").read_text(encoding="utf-8")
        match = re.search(r"const HISTORICO = (.*);\s*$", texto, flags=re.DOTALL)
        assert match, "historico.js não tem o formato esperado"
        cls.historico = json.loads(match.group(1))
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "script.js").read_text(encoding="utf-8")

    def test_estrutura_do_historico(self):
        h = self.historico
        total = len(h["datas"])
        self.assertGreaterEqual(total, 1)
        self.assertEqual(h["datas"], sorted(set(h["datas"])))
        self.assertEqual(len(h["arquivos"]), total)
        for series in h["produtos"].values():
            for chave, pontos in series.items():
                self.assertLess(int(chave), len(h["planos"]))
                indices = [p[0] for p in pontos]
                self.assertEqual(indices, sorted(set(indices)))
                self.assertTrue(all(0 <= i < total for i in indices))
                self.assertTrue(all(p[1] is None or p[1] >= 0 for p in pontos))

    def test_todas_as_datas_tem_planilha_na_pasta(self):
        arquivos = {p.name for p in (ROOT / "tabelas").glob("*.xlsx")}
        self.assertTrue(set(self.historico["arquivos"]) <= arquivos)

    def test_rotulos_iguais_aos_do_javascript(self):
        for _, rotulo in hist.ROTULOS_SEM_FIDELIZACAO:
            self.assertIn(f"label: '{rotulo}'", self.script)

    def test_historico_e_carregado_antes_do_script(self):
        posicao_historico = self.html.index('src="historico.js?v=')
        posicao_script = self.html.index('src="script.js?v=')
        self.assertLess(posicao_historico, posicao_script)
        self.assertRegex(self.html, r'src="historico\.js\?v=[0-9a-f]{12}"')

    def test_versao_do_historico_no_html_bate_com_o_arquivo(self):
        import hashlib
        conteudo = (ROOT / "historico.js").read_text(encoding="utf-8")
        versao = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:12]
        self.assertIn(f'src="historico.js?v={versao}"', self.html)


if __name__ == "__main__":
    unittest.main()
