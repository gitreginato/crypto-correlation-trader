---
name: Order Flow Terminal
description: Dashboard profissional de microestrutura e order flow para traders de cripto.
colors:
  primary: "#7267ef"
  primary-soft: "#ede9fe"
  success: "#17c666"
  success-soft: "#d8f5e7"
  danger: "#ea4d4d"
  danger-soft: "#ffe5e5"
  warning: "#ffa21d"
  warning-soft: "#fff2dd"
  info: "#3ec9d6"
  info-soft: "#e0f7fa"
  background: "#161c25"
  surface: "#1c232f"
  surface-elevated: "#242b3a"
  border: "#2f3848"
  text-primary: "#e8eaed"
  text-secondary: "#8996a4"
  text-muted: "#5b6b79"
  sidebar-bg: "#161c25"
  sidebar-text: "#b5bdca"
  sidebar-active: "#7267ef"
typography:
  display:
    fontFamily: "Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, SF Pro Text, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, SF Pro Text, -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.04em"
  mono:
    fontFamily: "JetBrains Mono, SF Mono, Fira Code, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  card-header:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    padding: "0 0 {spacing.sm} 0"
  table-header:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
  table-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    borderColor: "{colors.border}"
  badge:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  button:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
---

# Design System: Order Flow Terminal

## 1. Overview

**Creative North Star: "The Professional Trading Cockpit"**

A interface do Order Flow Terminal e inspirada em cockpits de trading profissional: Bloomberg Terminal, TradingView e dashboards institucionais. O objetivo e maximizar densidade de informacao sem sacrificar legibilidade. Cada elemento visual tem significado semantico: verde indica pressao compradora, vermelho indica pressao vendedora, azul destaca informacao tecnica. Nao ha decoracao sem proposito.

O design serve o produto: o trader precisa ler numeros rapidamente, comparar multiplos ativos e reagir em segundos. Por isso, a tipografia e predominantemente monospace para dados numericos, com hierarquia clara entre labels, valores e contexto. O layout usa cards distintos com sombras suaves e bordas sensiveis para criar agrupamento visual sem poluir a tela.

**Key Characteristics:**
- Densidade informacional alta: multiplos paineis visiveis simultaneamente.
- Paleta escura padrao com realce semantico em verde/vermelho/azul/laranja.
- Tipografia sans-serif para UI e monospace para numeros e tabelas.
- Cards com cantos arredondados, bordas sutis e sombras leves.
- Estados claros: hover, ativo, alerta, sucesso, perigo.
- Responsividade estrutural: reflow em 1080p, 1440p e 4K.

## 2. Colors

A paleta e escura por padrao, otimizada para sessoes longas de trading e monitores secundarios. Cores de estado sao reservadas para numeros, badges e indicadores.

### Primary
- **Violet Blue** (`#7267ef`): acao primaria, links ativos, indicadores tecnicos, destaques de UI. Usado com parcimonia.

### Semantic
- **Success Green** (`#17c666`): compra, bullish, pressao compradora, funding positivo.
- **Danger Red** (`#ea4d4d`): venda, bearish, pressao vendedora, liquidacao, drawdown.
- **Warning Orange** (`#ffa21d`): atencao, sobrecompra, sobreventa, estado neutro-anomalo.
- **Info Cyan** (`#3ec9d6`): dados tecnicos, informacoes de referencia, VWAP, bandas.

### Neutral
- **Cockpit Black** (`#161c25`): fundo da aplicacao.
- **Surface Navy** (`#1c232f`): fundo dos cards e paineis.
- **Surface Elevated** (`#242b3a`): hover, estados ativos, dropdowns.
- **Border Graphite** (`#2f3848`): divisores entre cards e tabelas.
- **Text Primary** (`#e8eaed`): texto principal e numeros.
- **Text Secondary** (`#8996a4`): labels, subtitulos, timestamps.
- **Text Muted** (`#5b6b79`): dados desabilitados, metadata.

### Soft Accents
- Cores suaves (`*-soft`) sao usadas para fundos de badges, chips e indicadores de estado que precisam de baixo contraste.

## 3. Typography

**Display Font:** Inter (com SF Pro e system-ui fallback)
**Body Font:** Inter
**Label/Mono Font:** JetBrains Mono

**Character:** Inter fornece legibilidade em tamanhos pequenos e densos; JetBrains Mono alinha numeros decimais para comparacao rapida entre linhas.

### Hierarchy
- **Display** (700, 1.75rem, 1.2): titulo da aplicacao no header.
- **Title** (600, 1rem, 1.4): titulos de cards e secoes.
- **Body** (400, 0.875rem, 1.5): texto explicativo e labels.
- **Label** (500, 0.75rem, 1.4, uppercase, 0.04em): headers de tabela, badges, tags.
- **Mono** (500, 0.8125rem, 1.4): precos, retornos, indicadores numericos, valores tecnicos.

## 4. Elevation

O sistema usa sombras sutis e camadas de superficie para criar profundidade sem efeitos de vidro ou neon. Cards repousam levemente acima do fundo da aplicacao. Hover e foco adicionam leve elevacao. Nao ha blur/backdrop-filter por padrao.

### Shadow Vocabulary
- **Card Rest** (`0 2px 8px rgba(0, 0, 0, 0.18)`): sombra dos cards em estado normal.
- **Card Hover** (`0 4px 16px rgba(0, 0, 0, 0.24)`): elevacao no hover de cards.
- **Dropdown** (`0 8px 24px rgba(0, 0, 0, 0.32)`): menus e tooltips.

## 5. Components

### Cards
- **Corner Style:** 8px de raio.
- **Background:** `#1c232f`.
- **Shadow Strategy:** Card Rest em repouso, Card Hover no hover.
- **Border:** 1px solid `#2f3848`.
- **Internal Padding:** 16px.
- **Header:** titulo em Title, badge de secao a direita, separador de 1px na parte inferior.

### Tables
- **Header:** texto em Label, cor Text Secondary, fundo Surface, sem uppercase forcado.
- **Row:** texto em Body/Mono, cor Text Primary, border-bottom 1px Border Graphite.
- **Hover:** fundo muda para Surface Elevated.
- **Numeric cells:** alinhados a direita, fonte Mono.

### Badges
- **Style:** fundo `*-soft`, texto na cor correspondente, raio 4px, padding 2px 8px.
- **State:** bull (verde), bear (vermelho), warn (laranja), info (azul), neutral (cinza).

### Buttons
- **Shape:** 4px de raio.
- **Primary:** fundo Violet Blue, texto branco, padding 8px 16px.
- **Secondary:** fundo transparente, texto Text Secondary, hover com Surface Elevated.
- **Transition:** 150ms ease-in-out para background, color, box-shadow.

### Navigation
- **Header:** altura 70px, fundo Sidebar Background, sombra leve.
- **Sidebar:** largura 260px, fundo Cockpit Black, texto Text Secondary, item ativo com barra lateral violet e fundo Surface Elevated.

## 6. Do's and Don'ts

### Do:
- **Do** usar verde apenas para compra/bullish e vermelho apenas para venda/bearish.
- **Do** manter numeros em Mono e alinhados a direita em tabelas.
- **Do** usar badges para estados (Live, Bullish, Bearish, Extreme Fear).
- **Do** respeitar a hierarquia: titulo maior, labels menores, numeros claros.
- **Do** usar `prefers-reduced-motion` para desativar pulse e animacoes.

### Don't:
- **Don't** usar gradientes roxos ou animacoes excessivas (relevo de PRODUCT.md: app casual de cripto).
- **Don't** usar cores sem significado semantico.
- **Don't** deixar graficos lentos ou que travam com muitos pontos.
- **Don't** parecer um tutorial ou onboarding (usuarios sao traders experientes).
- **Don't** misturar fontes similares (duas sans-serif geometricas, por exemplo).
