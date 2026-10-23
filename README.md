<div align="center">

# 📱 Tabela de Preço — TIM Revendas

**Consulta de preços de aparelhos e acessórios por plano TIM**  
Atualizado semanalmente conforme tabela oficial do canal Revendas.

[![Status](https://img.shields.io/badge/status-ativo-brightgreen?style=flat-square)](https://hermes-ecaflip.github.io/Tabela-de-preco-da-TIM/)
[![Última atualização](https://img.shields.io/badge/tabela-23%2F10%2F2026-blue?style=flat-square)](https://hermes-ecaflip.github.io/Tabela-de-preco-da-TIM/)
[![Canal](https://img.shields.io/badge/canal-Revendas-orange?style=flat-square)](https://hermes-ecaflip.github.io/Tabela-de-preco-da-TIM/)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey?style=flat-square)](LICENSE)

</div>

---

## 📖 Sobre o Projeto

Ferramenta web para consulta rápida de preços de aparelhos e acessórios comercializados no canal **Revendas TIM**, com suporte a múltiplos planos (fidelizados e não fidelizados).

Desenvolvida para uso interno de vendedores e revendedores, permitindo consultar em segundos o valor de qualquer aparelho em qualquer plano disponível na tabela oficial.

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🔍 **Busca em tempo real** | Pesquisa instantânea por nome do aparelho ou acessório |
| 📱 **294 itens catalogados** | Celulares, tablets, acessórios TIM e itens de loja |
| 💰 **Preços sem fidelização** | PRÉ (balcão), Base Faturamento, Controle e Pós não fidelizados |
| 📋 **Planos fidelizados** | Mobile (celular) e TIM Fibra (internet), com todos os subplanos |
| 🏷️ **Logos das marcas** | Apple, Samsung, Motorola, Xiaomi, Nokia, JBL, Sony, PlayStation, Xbox e mais |
| 📅 **Data de vigência** | Exibe data de atualização e validade de cada produto |
| 💡 **Comparativo de economia** | Mostra a diferença entre o preço de balcão e o plano selecionado |
| 📱 **Interface responsiva** | Layout profissional adaptado para celular, tablet, notebook e desktop |
| 🌓 **Tema claro e escuro** | Botão acessível que segue o tema do aparelho na primeira visita e lembra a preferência escolhida |
| ⚡ **Boost Trade In** | Ativa/desativa o desconto de troca direto no card, quando o produto tem Boost |
| 📚 **Catálogo por plano** | Lista os produtos com o preço já aplicado ao plano do cliente, com filtros de marca, tipo e faixa de preço digitável |
| 📈 **Comparador de preços** | Gráfico de linhas com a evolução do preço de cada produto a cada tabela enviada (até 6 planos ao mesmo tempo), resumo com variação e menor/maior preço, tabela de valores e lista do que mudou na última tabela |

---

## 🖥️ Demonstração

> Acesse pelo GitHub Pages:  
> **[https://hermes-ecaflip.github.io/Tabela-de-preco-da-TIM/](https://hermes-ecaflip.github.io/Tabela-de-preco-da-TIM/)**

---

## 🚀 Como Usar

### 1. Clone o repositório

```bash
git clone https://github.com/hermes-ecaflip/Tabela-de-preco-da-TIM.git
cd Tabela-de-preco-da-TIM
```

### 2. Abra no navegador

Basta abrir o arquivo `index.html` diretamente no navegador — não requer servidor ou dependências externas.

```bash
# macOS / Linux
open index.html

# Windows
start index.html
```

### 3. Pesquise um aparelho

Digite o nome do aparelho ou acessório no campo de busca, selecione o plano desejado e o preço será exibido automaticamente.

---

## 🔄 Como Atualizar a Tabela

A tabela é atualizada semanalmente pela TIM. Para atualizar o site **e** o Comparador de preços:

1. Dê à nova planilha `.xlsx` o nome da **data**, no formato `DD.MM.xlsx` (ex.: `22.10.xlsx`)
2. Envie o arquivo para a pasta **`tabelas/`** do repositório
3. O GitHub Actions detecta o envio e roda `processar_historico.py` e `processar_planilha.py` automaticamente
4. Em ~1 minuto o site entra no ar com a tabela nova e o gráfico atualizado

> **Nota:** a data do gráfico vem do **nome do arquivo**. Se o nome não tiver o ano, ele é deduzido pela data `DATA INÍCIO` da própria planilha (aceita também `22.10.2026.xlsx` e `2026-10-22.xlsx`). Arquivos fora desse padrão são ignorados com um aviso na execução do Actions. Se uma planilha estiver quebrada, a execução falha e nada é publicado até ela ser corrigida ou removida.

**A planilha mais recente da pasta vira a tabela do site.** Quando ela é mais nova que a tabela atual, é copiada para `tabela_precos.xlsx` automaticamente. Para completar o histórico com semanas antigas, basta enviar a planilha antiga com a data dela — ela entra no gráfico sem alterar a tabela atual. Para corrigir uma semana, envie o arquivo corrigido com o mesmo nome.

O envio direto de `tabela_precos.xlsx` continua funcionando, mas não entra no histórico do gráfico.

A data de vigência é lida do campo `DATA INÍCIO`, os planos são detectados automaticamente, e o **Boost Trade In** é lido da aba `TRADE IN` e casado por código — tudo sem edição manual. O processador recria a lista de Boosts do zero em cada atualização. Quando um Boost é removido da planilha, ele também deixa de aparecer no site. O endereço do `script.js` recebe uma versão baseada no conteúdo atualizado, evitando que o navegador reutilize dados antigos do cache.

O `style.css` e o `historico.js` também recebem uma versão automática. O site valida a estrutura do HTML, a sintaxe do JavaScript, o histórico e a sincronização dos Boosts antes de publicar uma atualização. Planos novos encontrados na planilha são incluídos automaticamente nos grupos Mobile ou TIM Fibra.

### 📈 Como funciona o Comparador

O `historico.js` guarda, para cada produto e plano, apenas os pontos em que o preço **mudou**, então continua pequeno mesmo com muitas semanas. O gráfico é desenhado em SVG puro, sem bibliotecas, e se ajusta à largura da tela (celular, tablet e desktop). Passe o mouse, toque ou use as setas do teclado para ver os valores de cada tabela. Nos produtos que aparecem em uma busca, o botão **Ver histórico de preços** abre o Comparador já nesse produto.

---

## 🗂️ Estrutura do Projeto

```
Tabela-de-preco-da-TIM/
│
├── .github/
│   └── workflows/
│       └── atualizar_tabela.yml  # GitHub Actions — atualização automática
│
├── index.html              # HTML semântico (header / main / footer)
├── style.css               # Estilos organizados por seções comentadas
├── script.js               # Lógica JavaScript com comentários
├── historico.js            # Histórico de preços do Comparador (gerado automaticamente)
├── processar_planilha.py   # Script Python de extração da planilha atual
├── processar_historico.py  # Script Python que monta o histórico a partir de tabelas/
├── tests/                  # Testes de Boosts, histórico e integridade do site
├── tabelas/                # Planilhas por data (22.10.xlsx, 29.10.xlsx...) — envie aqui
├── tabela_precos.xlsx      # Tabela atual do site (atualizada sozinha a partir de tabelas/)
├── README.md               # Este arquivo
└── LICENSE                 # Licença MIT
```

---

## 📦 Tecnologias Utilizadas

- **HTML5 semântico** — `<header>`, `<main>`, `<section>`, `<article>`, `<footer>`, `<details>`
- **CSS3** — variáveis, grid, animações, responsivo mobile-first
- **JavaScript vanilla** — sem frameworks ou dependências externas (o gráfico do Comparador é SVG próprio)
- **Google Fonts** — Inter + DM Sans
- **Python + pandas + openpyxl** — extração automática dos dados do `.xlsx`
- **GitHub Actions** — CI/CD para publicação automática
- **GitHub Pages** — hospedagem estática gratuita

---

## 📋 Planos Suportados

<details>
<summary><strong>💰 Sem Fidelização</strong></summary>

- PRÉ (Balcão)
- Base Faturamento Retail
- Controle Não Fidelizado
- Pós Pago Não Fidelizado

</details>

<details>
<summary><strong>📱 Mobile / Celular (Fidelizado)</strong></summary>

- TIM Controle / Plus / Premium / Smart / Redes Sociais
- TIM Black / Plus / Premium
- TIM Black A (15GB) / B (20GB) / C (25GB) / C Ultra
- TIM Black Família / A One / Plus / Premium / C One / VIP

</details>

<details>
<summary><strong>🌐 Fibra / Internet</strong></summary>

- TIM Fibra 300M, 400M, 500M, 600M, 1GB, 2GB (diversas variações)

</details>



---

## ⚠️ Aviso Legal

Este projeto é de uso **interno e exclusivo para revendedores credenciados TIM**. Os preços exibidos são válidos para o canal Revendas conforme tabela oficial vigente. Não é uma ferramenta oficial da TIM S.A.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---

<div align="center">
  <sub>Mantido por revendedor credenciado TIM · Atualizado em 23/10/2026</sub>
</div>
