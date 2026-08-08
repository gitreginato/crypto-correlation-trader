# Product

## Register

product

## Users

Day traders e analistas de criptomoedas que precisam de visualizacao em tempo real de order flow, microestrutura de mercado e indicadores tecnicos. Usam o dashboard em monitores secundarios durante sessoes de trading, precisando de leitura rapida e precisa de dados densos. Contexto: ambiente de trading profissional, multi-tela, necessidade de identificar rapidamente mudancas de momentum, liquidacoes e fluxo de ordens.

## Product Purpose

Dashboard de analise de microestrutura de mercado em tempo real que coleta dados de WebSocket (order book, trades) e REST (funding rate, open interest, long/short ratio, liquidations) da Binance. O produto existe para revelar "o jogo atras das velas": quem esta posicionando ordens, quem esta agredindo o book, onde estao os clusters de liquidez, e quando liquidacoes em cascada ocorrem. Sucesso = trader toma decisao mais informada em segundos.

## Brand Personality

Profissional, denso, preciso. Nao entretenimento. Estilo Bloomberg Terminal / TradingView: dark theme, cores semanticas (verde/vermelho para direcao), tipografia monospace para numeros, informacao hierarquica. 3 palavras: preciso, denso, acionavel.

## Anti-references

- NAO parecer um app de cripto casual com gradientes roxos e animacoes excessivas
- NAO usar cores aleatorias sem significado semantico
- NAO ter graficos lentos ou que travam com muitos pontos
- NAO parecer um tutorial ou onboarding (usuarios sao traders experientes)

## Design Principles

1. **Densidade sobre espaco**: cada pixel entrega informacao. Traders preferem mais dados visiveis a mais espaco em branco.
2. **Cor semantica**: verde = compra/bullish, vermelho = venda/bearish, amarelo = atencao, azul = neutro. Nunca usar cor decorativa.
3. **Numeros monospace**: alinhamento decimal e essencial para comparacao rapida entre linhas.
4. **Auto-refresh confiavel**: dados devem atualizar sem flash branco ou scroll jump.
5. **Responsividade real**: funciona em 1080p, 1440p e 4K. Cards reflowam sem perder legibilidade.

## Accessibility & Inclusion

- Contraste WCAG AA minimo (4.5:1 texto, 3:1 elementos grandes)
- Nao depender apenas de cor para informacao (usar icones/texto junto com verde/vermelho)
- Suporte a prefers-reduced-motion (desativar pulse animations)
- Fonte legivel em tamanhos pequenos (12px minimo para dados)
