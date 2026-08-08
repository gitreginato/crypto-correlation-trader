# Fontes de Dados

Catalogo de todas as fontes de dados de criptomoedas avaliadas para o projeto.

## Fontes primarias (em uso ou planejadas)

### 1. Binance Vision (data.binance.vision)

**Tipo:** Historico, batch (CSV em ZIP)
**Custo:** Gratuito
**Cobertura:** Spot, USD-M Futures, COIN-M Futures
**Granularidade:** Klines de 1s a 1mes, trades tick-by-tick, aggTrades, bookTicker
**Historico:** Desde 2017 (BTCUSDT), varia por symbol
**Acesso:** Download direto via HTTP (curl/wget) ou scripts Python

**URL pattern:**
```
https://data.binance.vision/data/<market>/monthly/klines/<SYMBOL>/<INTERVAL>/<SYMBOL>-<INTERVAL>-<YEAR>-<MONTH>.zip
https://data.binance.vision/data/<market>/daily/klines/<SYMBOL>/<INTERVAL>/<SYMBOL>-<INTERVAL>-<YEAR>-<MONTH>-<DAY>.zip
```

**Exemplo:**
```
https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip
```

**Schema Klines CSV (12 colunas):**
1. Open time (ms timestamp)
2. Open price
3. High price
4. Low price
5. Close price
6. Volume (base asset)
7. Close time (ms timestamp)
8. Quote asset volume
9. Number of trades
10. Taker buy base asset volume
11. Taker buy quote asset volume
12. Unused field (ignore)

**Schema Trades CSV:**
1. trade_id
2. price
3. qty
4. quote_qty
5. timestamp
6. is_buyer_maker

**Repo de referencia:** [binance/binance-public-data](https://github.com/binance/binance-public-data)
- Scripts Python prontos: `python/download-kline.py`
- Scripts shell: `shell/fetch-all-trading-pairs.sh`

**Veredito:** Fonte principal para dados historicos. Gratis, completo, oficial.

---

### 2. Binance REST API (api.binance.com)

**Tipo:** Sob demanda (REST)
**Custo:** Gratuito (rate limit: 1200 req/min com API key, 120 req/min sem)
**Cobertura:** Spot, Futures, Margin
**Endpoints uteis:**
- `GET /api/v3/klines` - klines historicos (limite 1000 por request)
- `GET /api/v3/ticker/24hr` - estatisticas 24h
- `GET /api/v3/depth` - order book
- `GET /api/v3/trades` - trades recentes
- `GET /fapi/v1/klines` - klines de futures

**Rate limits:**
- Sem API key: 1200 weight/min (klines = weight 1-2)
- Com API key: 6000 weight/min
- IP ban se exceder por 5 min

**Veredito:** Complementar a Binance Vision. Usar para dados recentes (ultimo dia) e dados nao disponiveis em Vision.

---

### 3. Binance WebSocket (stream.binance.com)

**Tipo:** Tempo real (streaming)
**Custo:** Gratuito
**Cobertura:** Spot, Futures
**Streams uteis:**
- `<symbol>@kline_<interval>` - kline stream (1s a 1mes)
- `<symbol>@depth` - order book diff
- `<symbol>@depth20@100ms` - top 20 levels a 100ms
- `<symbol>@trade` - trades em tempo real
- `<symbol>@ticker` - ticker 24h rolling
- `!ticker@arr` - todos os tickers (array)

**Conexao:**
```
wss://stream.binance.com:9443/ws
wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1m/ethusdt@kline_1m
```

**Limite:** 5 conexoes por IP, 200 streams por conexao

**Veredito:** Fonte principal para tempo real. Usar no bot (Fase 4+).

---

### 4. CCXT (biblioteca)

**Tipo:** Biblioteca Python que unifica 100+ exchanges
**Custo:** Gratuito (MIT)
**Repo:** [ccxt/ccxt](https://github.com/ccxt/ccxt) (43k+ stars)
**Funcionalidades:**
- `fetch_ohlcv(symbol, timeframe, since, limit)` - klines unificados
- `fetch_ticker(symbol)` - ticker
- `fetch_order_book(symbol)` - order book
- `create_order(symbol, type, side, amount, price)` - execucao
- `fetch_balance()` - saldo
- WebSocket via CCXT Pro (async)

**Exchanges suportadas:** Binance, Bybit, OKX, Kraken, Coinbase, Gate.io, +100 outras

**Veredito:** Usar para abstracao multi-exchange e execucao. Para dados historicos em massa, Binance Vision direto e mais eficiente.

---

## Fontes complementares (avaliadas)

### 5. CoinGecko API

**Tipo:** REST
**Custo:** Gratuito (30 req/min) / Pro ($129/mes, 500 req/min)
**Cobertura:** Preco agregado, market cap, metadata, DeFi
**Endpoints:**
- `/coins/markets` - top N moedas por market cap
- `/coins/{id}/market_chart` - historico de preco
- `/simple/price` - preco spot

**Veredito:** Util para metadata (setor, categoria) e dados de moedas menores nao listadas na Binance. Nao usar para dados de preco de trading (dados agregados, nao raw da exchange).

---

### 6. Coinpaprika API

**Tipo:** REST
**Custo:** Gratuito (25k req/mes)
**Cobertura:** Similar ao CoinGecko, foco em dados on-chain e eventos

**Veredito:** Alternativa ao CoinGecko se rate limit for problema. Nao prioritario.

---

### 7. Bybit API

**Tipo:** REST + WebSocket
**Custo:** Gratuito
**Cobertura:** Spot, Futures (USDT perpetuals)
**Rate limit:** Mais generoso que Binance em 2026
**Fees:** Menores que Binance em USDT perpetuals

**Veredito:** Fallback se Binance bloquear IP BR. Considerar como exchange primaria para futures se fees forem melhores. Avaliar na Fase 4.

---

### 8. OKX API

**Tipo:** REST + WebSocket
**Custo:** Gratuito
**Cobertura:** Spot, Futures, Options, Swap

**Veredito:** Terceira opcao. Boa para diversificacao de exchange. Nao prioritario agora.

---

## Fontes descartadas (nao servem para cripto)

### B3 / Cedro / HG Brasil / Economatica
- Descartadas para este projeto: foco em B3 (acoes/indices/futuros brasileiros)
- Dados caros, burocraticos, nao cobrem cripto
- Ver comparativo em `docs/research/api-comparison-b3.md`

### Alpha Vantage / Polygon.io
- Cobertura de cripto limitada e com delay
- Qualidade inferior a Binance direto
- Rate limits restritivos no plano gratuito

### Yahoo Finance
- Dados de cripto via yfinance: delay 15min, nao confiavel para trading
- Util apenas para prototipacao rapida

---

## Estrutura de armazenamento local

```
data/
├── parquet/                    # Dados historicos em Parquet
│   └── binance/
│       └── spot/
│           ├── BTCUSDT/
│           │   └── 1m/
│           │       └── year=2024/
│           │           ├── month=01.parquet
│           │           └── month=02.parquet
│           └── ETHUSDT/
│               └── 1m/
│                   └── year=2024/
│                       └── ...
├── raw/                        # CSVs baixados da Binance Vision (temporario)
│   └── binance/
│       └── spot/
│           └── monthly/
│               └── klines/
│                   └── BTCUSDT/
│                       └── 1h/
│                           └── BTCUSDT-1h-2024-01.zip
├── graphs/                     # Grafos HTML gerados pelo Pyvis
│   └── correlation_2024-01.html
└── bot_state/                  # Estado do bot (Fase 4+)
    ├── positions.json
    └── orders.json
```

## Volume estimado de dados

| Symbol | Timeframe | Periodo | Tamanho Parquet | Tamanho CSV |
|--------|-----------|---------|-----------------|-------------|
| BTCUSDT | 1m | 1 ano | ~50 MB | ~200 MB |
| BTCUSDT | 1m | 3 anos | ~150 MB | ~600 MB |
| 30 symbols | 1m | 3 anos | ~4.5 GB | ~18 GB |
| 30 symbols | 5m | 3 anos | ~900 MB | ~3.6 GB |
| 30 symbols | 1h | 3 anos | ~75 MB | ~300 MB |

**Recomendacao:** comecar com 5m (bom compromisso entre granularidade e volume). Adicionar 1m depois se necessario.
