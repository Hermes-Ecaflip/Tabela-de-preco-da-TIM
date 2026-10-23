"""
═══════════════════════════════════════════════════════════════════════
 TIM Consulta de Preços — Histórico de Preços (Comparador)
═══════════════════════════════════════════════════════════════════════

 Lê todas as planilhas da pasta `tabelas/` (uma por data, ex.: 01.10.xlsx),
 extrai os preços de cada uma e gera o arquivo `historico.js`, que alimenta
 o gráfico do Comparador de Preços no site.

 NOME DOS ARQUIVOS (a data vem do nome):
   01.10.xlsx        → 01/10 (o ano é deduzido pela data de vigência da planilha)
   01.10.2026.xlsx   → 01/10/2026
   2026-10-01.xlsx   → 01/10/2026
   Arquivos fora desse padrão são ignorados com um aviso.

 O QUE ESTE SCRIPT FAZ:
   1. Lê e valida todas as planilhas da pasta (se alguma estiver quebrada,
      nada é alterado e o erro aparece no GitHub Actions).
   2. Se a planilha mais recente da pasta for mais nova que a tabela atual
      do site (`tabela_precos.xlsx`), ela é copiada para lá. Assim um único
      envio atualiza o site e o gráfico. Envios antigos (histórico) não
      sobrescrevem a tabela atual.
   3. Regera `historico.js` (só guarda os pontos em que o preço mudou, o que
      mantém o arquivo pequeno mesmo com muitas tabelas).
   4. Atualiza a versão de cache de `historico.js` no `index.html`.

 Uso:  python processar_historico.py
═══════════════════════════════════════════════════════════════════════
"""

import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple

import pandas as pd

import processar_planilha as base


# ──────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────────────────

PASTA_TABELAS = Path("tabelas")
ARQUIVO_SAIDA = Path("historico.js")
ARQUIVO_ATUAL = Path(base.ARQUIVO_XLSX)   # tabela usada pelo site (tabela_precos.xlsx)
ARQUIVO_INDEX = Path("index.html")
VERSAO_FORMATO = 1

# Campos "sem fidelização" → rótulo exibido no site (iguais ao NONFID do script.js)
ROTULOS_SEM_FIDELIZACAO = (
    ("pre",              "PRÉ (Balcão)"),
    ("base_retail",      "Base Faturamento"),
    ("controle_nao_fid", "Controle Não Fid."),
    ("pos_nao_fid",      "Pós Não Fid."),
)

# DD.MM, DD.MM.AA, DD.MM.AAAA (aceita . - _ / ou espaço como separador)
PADRAO_DIA_MES_ANO = re.compile(r"^(\d{1,2})[.\-_/ ](\d{1,2})(?:[.\-_/ ](\d{4}|\d{2}))?$")
# AAAA-MM-DD
PADRAO_ISO = re.compile(r"^(\d{4})[.\-_](\d{1,2})[.\-_](\d{1,2})$")


class Tabela(NamedTuple):
    """Uma planilha da pasta, já com a data resolvida."""
    data: date
    caminho: Path


# ──────────────────────────────────────────────────────────────────────
# MENSAGENS (viram anotações visíveis na execução do GitHub Actions)
# ──────────────────────────────────────────────────────────────────────

def aviso(mensagem):
    print(f"::warning::{mensagem}")


def erro(mensagem):
    print(f"::error::{mensagem}")


# ──────────────────────────────────────────────────────────────────────
# DATAS
# ──────────────────────────────────────────────────────────────────────

def interpretar_nome(nome):
    """
    Interpreta o nome do arquivo (sem extensão) e devolve (dia, mês, ano),
    onde o ano é None quando não está no nome. Retorna None se o nome não
    seguir nenhum padrão aceito.
    """
    nome = nome.strip()
    iso = PADRAO_ISO.match(nome)
    if iso:
        return int(iso.group(3)), int(iso.group(2)), int(iso.group(1))

    dma = PADRAO_DIA_MES_ANO.match(nome)
    if not dma:
        return None
    ano = dma.group(3)
    if ano is not None:
        ano = int(ano) + 2000 if len(ano) == 2 else int(ano)
    return int(dma.group(1)), int(dma.group(2)), ano


def _data_valida(ano, mes, dia):
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def resolver_data(dia, mes, ano, referencia):
    """
    Monta a data completa. Quando o nome não traz o ano, escolhe o ano
    (anterior, atual ou seguinte à referência) que deixa a data mais perto
    da referência. Isso evita erro na virada do ano (ex.: tabela com vigência
    em 30/12 enviada como 02.01.xlsx).
    """
    if ano is not None:
        return _data_valida(ano, mes, dia)
    candidatas = [
        data for data in (_data_valida(referencia.year + delta, mes, dia) for delta in (-1, 0, 1))
        if data is not None
    ]
    if not candidatas:
        return None
    return min(candidatas, key=lambda data: abs((data - referencia).days))


def _para_data(valor):
    """Converte o valor de uma célula (datetime ou texto) em date, ou None."""
    if valor is None or (not isinstance(valor, (date, datetime)) and pd.isna(valor)):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip().split(" ")[0]
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler_vigencia(caminho):
    """Lê o campo 'DATA INÍCIO:' da aba REV. Retorna None se não existir ou se o arquivo não abrir."""
    try:
        bruto = pd.read_excel(caminho, sheet_name="REV", header=None, nrows=13)
    except Exception:
        return None
    for _, linha in bruto.iterrows():
        valores = list(linha)
        for posicao, valor in enumerate(valores):
            if str(valor).strip() == "DATA INÍCIO:" and posicao + 1 < len(valores):
                return _para_data(valores[posicao + 1])
    return None


# ──────────────────────────────────────────────────────────────────────
# LISTAGEM DAS PLANILHAS
# ──────────────────────────────────────────────────────────────────────

def listar_tabelas(pasta=PASTA_TABELAS, hoje=None):
    """
    Devolve (tabelas, avisos): as planilhas válidas ordenadas por data e
    uma lista de avisos sobre arquivos ignorados.
    """
    hoje = hoje or date.today()
    avisos = []
    if not pasta.is_dir():
        return [], [f"A pasta '{pasta}/' não foi encontrada."]

    por_data = {}
    for caminho in sorted(pasta.iterdir(), key=lambda item: item.name.lower()):
        if not caminho.is_file() or caminho.suffix.lower() != ".xlsx" or caminho.name.startswith("~$"):
            continue

        partes = interpretar_nome(caminho.stem)
        if partes is None:
            avisos.append(f"'{caminho.name}' foi ignorado: nome fora do padrão. Use a data, ex.: 01.10.xlsx")
            continue

        dia, mes, ano = partes
        referencia = hoje if ano is not None else (ler_vigencia(caminho) or hoje)
        data = resolver_data(dia, mes, ano, referencia)
        if data is None:
            avisos.append(f"'{caminho.name}' foi ignorado: a data {dia:02d}/{mes:02d} não existe.")
            continue

        if data in por_data:
            avisos.append(
                f"'{caminho.name}' e '{por_data[data].caminho.name}' têm a mesma data "
                f"({data:%d/%m/%Y}). Foi usado '{caminho.name}'."
            )
        por_data[data] = Tabela(data, caminho)

    return [por_data[data] for data in sorted(por_data)], avisos


# ──────────────────────────────────────────────────────────────────────
# EXTRAÇÃO DOS PREÇOS DE UMA PLANILHA
# ──────────────────────────────────────────────────────────────────────

def extrair_precos(caminho):
    """
    Lê uma planilha e devolve {descrição: {plano: preço}}, usando as mesmas
    regras do site (mesmas colunas, mesma junção de variantes de cor), então
    os nomes e preços do histórico batem com os da consulta.
    """
    df_rev = pd.read_excel(caminho, sheet_name="REV", header=base.HEADER_REV)
    df_acc = pd.read_excel(caminho, sheet_name="ACESSÓRIOS REV", header=base.HEADER_ACC)

    # process_sheet imprime um resumo; silenciamos para não poluir o log
    with contextlib.redirect_stdout(io.StringIO()):
        produtos = (
            base.dedup(base.process_sheet(df_rev, "aparelho", True, {}))
            + base.dedup(base.process_sheet(df_acc, "acessorio", False, {}))
        )

    precos = {}
    for produto in produtos:
        planos = {}
        for campo, rotulo in ROTULOS_SEM_FIDELIZACAO:
            if produto.get(campo) is not None:
                planos[rotulo] = produto[campo]
        planos.update(produto["planos"])

        existente = precos.setdefault(produto["descricao"], {})
        for plano, preco in planos.items():
            existente[plano] = min(preco, existente.get(plano, preco))

    if not precos:
        raise ValueError("nenhum produto foi encontrado (confira as abas REV e ACESSÓRIOS REV)")
    return precos


# ──────────────────────────────────────────────────────────────────────
# CODIFICAÇÃO DO HISTÓRICO
# ──────────────────────────────────────────────────────────────────────

def _numero(valor):
    """Arredonda para centavos e usa inteiro quando não há centavos (JSON menor)."""
    if valor is None:
        return None
    valor = round(float(valor), 2)
    return int(valor) if valor == int(valor) else valor


def construir_historico(tabelas):
    """
    Monta a estrutura do histórico a partir de uma lista ordenada de
    (data, nome_do_arquivo, {descrição: {plano: preço}}).

    Formato compacto: para cada produto e plano, guarda só os pontos em que
    o valor muda — [índice_da_data, preço] — e [índice, null] quando o
    produto deixa de ter preço naquele plano. O site reconstrói a linha
    completa a partir disso.
    """
    vistos = []
    for _, _, snapshot in tabelas:
        for planos in snapshot.values():
            for plano in planos:
                if plano not in vistos:
                    vistos.append(plano)
    rotulos_fixos = [rotulo for _, rotulo in ROTULOS_SEM_FIDELIZACAO if rotulo in vistos]
    planos = rotulos_fixos + [plano for plano in vistos if plano not in rotulos_fixos]
    indice = {plano: posicao for posicao, plano in enumerate(planos)}

    descricoes = sorted({descricao for _, _, snapshot in tabelas for descricao in snapshot})
    produtos = {}
    for descricao in descricoes:
        planos_do_produto = {
            plano for _, _, snapshot in tabelas for plano in snapshot.get(descricao, {})
        }
        series = {}
        for plano in sorted(planos_do_produto, key=indice.get):
            pontos, anterior = [], None
            for posicao, (_, _, snapshot) in enumerate(tabelas):
                valor = _numero(snapshot.get(descricao, {}).get(plano))
                if valor != anterior:
                    pontos.append([posicao, valor])
                    anterior = valor
            series[str(indice[plano])] = pontos
        produtos[descricao] = series

    return {
        "versao": VERSAO_FORMATO,
        "datas": [data.isoformat() for data, _, _ in tabelas],
        "arquivos": [arquivo for _, arquivo, _ in tabelas],
        "planos": planos,
        "produtos": produtos,
    }


def decodificar_historico(historico):
    """Operação inversa de construir_historico: devolve um {descrição: {plano: preço}} por data."""
    total = len(historico["datas"])
    resultado = [{} for _ in range(total)]
    for descricao, series in historico["produtos"].items():
        for chave, pontos in series.items():
            plano = historico["planos"][int(chave)]
            atual, cursor = None, 0
            for posicao in range(total):
                while cursor < len(pontos) and pontos[cursor][0] <= posicao:
                    atual = pontos[cursor][1]
                    cursor += 1
                if atual is not None:
                    resultado[posicao].setdefault(descricao, {})[plano] = atual
    return resultado


def gerar_js(historico):
    """Texto final de historico.js (determinístico: sem mudança real, sem commit)."""
    dados = json.dumps(historico, ensure_ascii=False, separators=(",", ":"))
    return (
        "/* Gerado automaticamente por processar_historico.py a partir da pasta tabelas/ — não edite. */\n"
        f"const HISTORICO = {dados};\n"
    )


# ──────────────────────────────────────────────────────────────────────
# ATUALIZAÇÃO DOS ARQUIVOS DO SITE
# ──────────────────────────────────────────────────────────────────────

def _hash_arquivo(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def sincronizar_tabela_atual(tabelas, destino=ARQUIVO_ATUAL):
    """
    Copia a planilha mais recente da pasta para `tabela_precos.xlsx` (a que
    alimenta a consulta), quando ela for mais nova que a tabela atual.
    Retorna True se copiou.
    """
    mais_recente = tabelas[-1]
    destino = Path(destino)

    if destino.exists():
        if _hash_arquivo(destino) == _hash_arquivo(mais_recente.caminho):
            return False
        vigencia_atual = ler_vigencia(destino)
        if vigencia_atual is not None and mais_recente.data < vigencia_atual:
            return False

    shutil.copyfile(mais_recente.caminho, destino)
    return True


def atualizar_index_html(versao, caminho=ARQUIVO_INDEX):
    """Atualiza a versão de cache de historico.js no index.html."""
    caminho = Path(caminho)
    html = caminho.read_text(encoding="utf-8")
    novo, substituicoes = re.subn(
        r'<script src="historico\.js(?:\?v=[^"]*)?"></script>',
        f'<script src="historico.js?v={versao}"></script>',
        html,
        count=1,
    )
    if substituicoes != 1:
        raise RuntimeError("Não foi possível localizar a inclusão de historico.js em index.html.")
    if novo != html:
        caminho.write_text(novo, encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# FLUXO PRINCIPAL
# ──────────────────────────────────────────────────────────────────────

def main():
    print(f"🗂️  Lendo a pasta {PASTA_TABELAS}/ ...")
    tabelas, avisos = listar_tabelas()
    for mensagem in avisos:
        aviso(mensagem)

    if not tabelas:
        aviso("Nenhuma planilha válida em tabelas/. O histórico não foi alterado.")
        return 0

    extraidas, falhas = [], 0
    for tabela in tabelas:
        try:
            precos = extrair_precos(tabela.caminho)
        except Exception as exc:  # noqa: BLE001 — qualquer falha de leitura deve ser reportada
            erro(f"Não foi possível ler '{tabela.caminho.name}': {exc}")
            falhas += 1
            continue
        extraidas.append((tabela.data, tabela.caminho.name, precos))
        print(f"   • {tabela.data:%d/%m/%Y} ← {tabela.caminho.name}: {len(precos)} produtos")

    if falhas:
        erro("Corrija ou remova a(s) planilha(s) com erro e envie novamente. Nada foi alterado.")
        return 1

    if sincronizar_tabela_atual(tabelas):
        print(f"🔁 Tabela atual do site atualizada com '{tabelas[-1].caminho.name}'")
    else:
        print("ℹ️  A tabela atual do site já está em dia.")

    historico = construir_historico(extraidas)
    conteudo = gerar_js(historico)
    versao = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:12]

    if not ARQUIVO_SAIDA.exists() or ARQUIVO_SAIDA.read_text(encoding="utf-8") != conteudo:
        ARQUIVO_SAIDA.write_text(conteudo, encoding="utf-8")
        print(f"✅ {ARQUIVO_SAIDA} atualizado")
    else:
        print(f"ℹ️  {ARQUIVO_SAIDA} já estava em dia")
    atualizar_index_html(versao)

    primeira, ultima = historico["datas"][0], historico["datas"][-1]
    print(f"\n🎉 Concluído! {len(tabelas)} tabela(s), de {primeira} a {ultima}, "
          f"{len(historico['produtos'])} produtos no comparador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
