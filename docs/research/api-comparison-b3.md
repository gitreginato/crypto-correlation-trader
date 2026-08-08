# Comparativo de APIs: B3 vs Cripto

**Data:** 2026-07-15
**Decisao:** Usar dados de cripto (Binance) ao inves de B3 (Bovespa)

## Contexto

O usuario precisa de dados solidos para:
1. Criar grafos de correlacao entre ativos
2. Alimentar um bot de trading automatizado

Requisitos originais: indices de contratos da Bovespa, dolar, e indices da Bovespa.

## APIs da B3 avaliadas

### B3 Oficial (UP2DATA + UMDF + APIs)

| Aspecto | Detalhe |
|---------|---------|
| Cobertura | Acoes, futuros (indice, dolar, juros, commodities), opcoes, cripto (2026+) |
| Tempestividade | Tempo real, atraso continuo, atraso snapshot, EOD |
| Preco (uso proprio, tempo real) | R$ 3.200/mes por dataset (Futuros) |
| Preco (distribuicao, tempo real) | R$ 6.000/mes por dataset |
| Preco (atraso continuo) | R$ 1.920/mes por dataset |
| Preco (atraso snapshot) | R$ 320/mes por dataset |
| Burocracia | Contrato comercial, reporte de fees, auditoria, VPN para alguns endpoints |
| Dados publicos gratuitos | COTAHIST (acoes EOD desde 1986), precos de ajuste de futuros (EOD) |

**Veredito:** Dado mais confiavel e de menor latencia, mas caro (R$ 3.840/ano minimo, R$ 38.400/ano tempo real) e burocratico. So faz sentido para PJ com volume que justifica.

### Cedro Technologies (Market Data Cloud)

| Aspecto | Detalhe |
|---------|---------|
| Cobertura | Bovespa (acoes/opcoes) + BM&F (futuros/opcoes) + moedas + indicadores |
| Interfaces | REST (JSON/XML), WebSocket, Socket (TCP/UDP, book L2) |
| Simbolos | WIN, WDO, DOL, IND, PETR4, etc. |
| Plano Basic PF | R$ 439,90/mes (20k req REST, WS 50 ativos, candles 1 ano) |
| Plano PRO PF | R$ 579,90/mes (100k req REST, WS 100 ativos, book L2, candles 5 anos) |
| Plano PREMIUM PF | R$ 689,00/mes (500k req REST, tick-by-tick, EOD 5 anos) |
| Trial | 7 dias gratis |
| Restricao | Planos PF sao uso proprio (sujeito a auditoria). PJ necessario para redistribuicao |
| Lib | Python e .NET |

**Veredito:** Melhor opcao para PF que quer tempo real de WIN/WDO. Custo R$ 5.280-8.268/ano. Ainda caro comparado a cripto (gratis).

### HG Brasil (HG Finance)

| Aspecto | Detalhe |
|---------|---------|
| Cobertura | Acoes, BDRs, FIIs, ETFs, IBOV, IFIX, indices globais, moedas spot, CDI/Selic |
| Limitacao | NAO cobre contratos futuros da B3 (WIN, WDO, DOL, IND) |
| Interface | REST (JSON), simples |
| Preco | Free limitado / Pro pago (valor nao publico claramente) |

**Veredito:** Util para indices globais e moedas spot, mas nao serve para futuros da B3. Descartado como fonte primaria.

### Economatica API

| Aspecto | Detalhe |
|---------|---------|
| Cobertura | 4 dominios: Noticias, Fundamentos & Mercado, Fundos, Renda Fixa |
| Features | 100+ indicadores fundamentalistas, OHLC EOD, benchmarks B3, Markowitz |
| Interface | REST + WebSocket, HMAC/Bearer auth |
| Preco | Comercial sob negocicao (interno / B2B / B2B2C) |
| Foco | Institucional, fundamentalista, EOD |

**Veredito:** Excelente para pesquisa fundamentalista, mas nao e otimo para tick de futuros em tempo real. Preco nao publico, provavelmente alto. Descartado para este caso.

### Backtester.com.br

| Aspecto | Detalhe |
|---------|---------|
| Cobertura | 300+ acoes, indices, ETFs, BDRs, commodities, WIN, WDO (series continuas) |
| Formato | CSV (download), timeframes D1/H1/M30/M15/M5/M1 |
| B3 Essencial | Gratis (D1 ate 3 meses) |
| B3 Trader | R$ 718,80/ano (D1 ate 5 anos, H1 ate 2 anos) |
| B3 Pro | R$ 1.078,80/ano (D1 ate 20 anos, H1 ate 4 anos, M1 ate 3 meses) |

**Veredito:** Melhor custo-beneficio para historico de WIN/WDO. So historico, nao tempo real. Se fosse operar B3, seria a fonte historica + Cedro para tempo real.

### B3 dados publicos (gratuito)

| Aspecto | Detalhe |
|---------|---------|
| COTAHIST | Acoes EOD desde 1986, download em ZIP, layout TXT |
| Precos de ajuste | Futuros EOD, publicado diariamente na web |
| rb3 (R) | Pacote que baixa e estrutura dados publicos da B3 automaticamente |

**Veredito:** Gratis e oficial, mas so EOD e preco de ajuste (nao OHLC intradiario de futuros). Bom para comecar, limitado para bot intradiario.

### Alpha Vantage / Polygon.io

| Aspecto | Detalhe |
|---------|---------|
| Alpha Vantage | Acoes brasileiras via sufixo .SA, intradiario com delay 5-15min. SEM futuros da B3 |
| Polygon.io | Forte em futuros US, forex, crypto. SEM futuros da B3 |

**Veredito:** Descartados. Nao cobrem o necessario.

---

## APIs de Cripto avaliadas

### Binance Vision

| Aspecto | Detalhe |
|---------|---------|
| Custo | Gratuito |
| Cobertura | Spot, USD-M Futures, COIN-M Futures |
| Granularidade | Klines 1s a 1mes, trades tick-by-tick, aggTrades, bookTicker |
| Historico | Desde 2017 (BTCUSDT), varia por symbol |
| Acesso | Download HTTP direto (curl/wget/scripts) |
| Volume | ~21 GB para todos os trades de BTCUSDT |

**Veredito:** Fonte ideal para historico. Gratis, granular, oficial, sem burocracia.

### Binance REST API

| Aspecto | Detalhe |
|---------|---------|
| Custo | Gratuito |
| Rate limit | 1200 weight/min sem key, 6000 com key |
| Endpoints | klines, ticker, depth, trades |
| Limite por request | 1000 klines |

**Veredito:** Complementar a Vision. Para dados recentes e sob demanda.

### Binance WebSocket

| Aspecto | Detalhe |
|---------|---------|
| Custo | Gratuito |
| Streams | klines, depth, trades, ticker |
| Limite | 5 conexoes/IP, 200 streams/conexao |

**Veredito:** Fonte ideal para tempo real. Gratis, baixa latencia.

### CCXT

| Aspecto | Detalhe |
|---------|---------|
| Custo | Gratuito (MIT) |
| Cobertura | 100+ exchanges unificadas |
| Funcoes | fetch_ohlcv, create_order, fetch_balance, WebSocket (Pro) |

**Veredito:** Abstracao multi-exchange. Usar para execucao e fallback.

---

## Tabela comparativa final

| Criterio | B3 (Cedro PRO) | B3 (publico) | Cripto (Binance) |
|----------|----------------|--------------|-------------------|
| Custo mensal | R$ 580 | R$ 0 | R$ 0 |
| Custo anual | R$ 6.960 | R$ 0 | R$ 0 |
| Tempo real | Sim (WS + Socket) | Nao | Sim (WS) |
| Historico tick | Sim (3 meses 1min) | Nao | Sim (desde 2017) |
| Historico EOD | Sim (5 anos) | Sim (desde 1986) | Sim (desde 2017) |
| Burocracia | Alta (auditoria PF) | Baixa | Nenhuma |
| Execucao | Via corretora (MT5/FIX) | N/A | Direto na exchange |
| Latencia | Media (Cedro) | N/A | Baixa (direto Binance) |
| Regulacao | CVM (seguro) | CVM | Nenhuma (risco custodia) |
| Ativos | WIN, WDO, DOL, IND, acoes | Acoes, ajuste futuros | 200+ pares USDT |

## Decisao

**Cripto (Binance) vence em:**
- Custo (gratis vs R$ 580/mes)
- Burocracia (nenhuma vs auditoria)
- Historico (desde 2017 vs 3 meses de tick)
- Execucao (direto vs corretora intermediaria)
- Disponibilidade (API publica vs contrato comercial)

**B3 vence em:**
- Regulacao (CVM vs nada)
- Custodia (camara compensadora vs risco exchange)
- Diversidade de estrategias (setores descorrelacionados vs BTC domina)

**Conclusao:** Para o objetivo imediato (grafos de correlacao + bot), cripto e a escolha pragmaticamente melhor. O custo zero e a ausencia de burocracia permitem iterar rapido. A B3 pode ser reconsiderada no futuro se houver necessidade de diversificacao para ativos regulados.
