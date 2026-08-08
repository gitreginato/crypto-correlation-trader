# Comparativo de APIs de Cripto

**Data:** 2026-07-15

## Exchanges avaliadas

### Binance (escolhida como primaria)

| Aspecto | Detalhe |
|---------|---------|
| Volume 24h | Maior do mundo (~$30B+ spot, ~$80B+ futures) |
| Pares USDT | 200+ |
| Fees | 0.1% taker, 0.075% maker (0.075% taker com BNB) |
| API REST | Gratuita, 6000 weight/min com key |
| WebSocket | Gratuito, 5 conexoes/IP, 200 streams/conexao |
| Dados historicos | Binance Vision (gratis, tick-by-tick desde 2017) |
| Acesso BR | Possivel bloqueio de IP (usar VPN ou fallback Bybit) |
| Custodia | Exchange centralizada (risco de hack/quebra) |

### Bybit (fallback / alternativa)

| Aspecto | Detalhe |
|---------|---------|
| Volume 24h | Top 3 (~$15B+ futures) |
| Pares USDT | 150+ |
| Fees | 0.055% taker, 0.02% maker (menores que Binance em 2026) |
| API | Gratuita, rate limit mais generoso que Binance |
| Acesso BR | Sem bloqueio conhecido |
| Dados historicos | Disponivel via API, menos granular que Binance Vision |

### OKX (terceira opcao)

| Aspecto | Detalhe |
|---------|---------|
| Volume 24h | Top 5 |
| Pares USDT | 100+ |
| Fees | 0.1% taker, 0.08% maker |
| Features | Spot, futures, options, swap |

## Decisao: Binance como primaria

**Motivos:**
1. Maior volume = maior liquidez = menor slippage
2. Binance Vision oferece historico tick-by-tick gratis desde 2017 (nenhuma outra exchange tem isso)
3. CCXT suporta Binance nativamente
4. python-binance e a lib mais madura para uma exchange especifica

**Risco: bloqueio de IP BR**
- Binance ja restringiu alguns servicos para usuarios BR no passado
- Mitigacao: VPN, ou migrar para Bybit (CCXT abstrai a troca)
- Para dados publicos (Vision + WS), bloqueio e menos provavel que para trading

## Fontes de dados agregados (complementares)

### CoinGecko
- Preco agregado de 10k+ moedas
- Metadata (setor, categoria, plataforma)
- Rate limit: 30 req/min gratuito
- Uso: enriquecer universo com metadata, nao para preco de trading

### Coinpaprika
- Alternativa ao CoinGecko
- 25k req/mes gratuito
- Uso: fallback se CoinGecko rate limit for problema

## Estrutura de dados da Binance

### Klines (candles OHLCV)
```
Colunas: open_time, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_base, taker_buy_quote, ignore
```

### Trades (tick-by-tick)
```
Colunas: trade_id, price, qty, quote_qty, timestamp, is_buyer_maker
```

### Order Book (depth)
```
Niveis: [price, qty] para bids e asks
Updates: diff a cada 100ms ou 1000ms
```

## Endpoints chave

### REST
```
GET /api/v3/klines?symbol=BTCUSDT&interval=5m&startTime=...&endTime=...&limit=1000
GET /api/v3/ticker/24hr?symbol=BTCUSDT
GET /api/v3/depth?symbol=BTCUSDT&limit=20
GET /api/v3/trades?symbol=BTCUSDT&limit=1000
```

### WebSocket
```
wss://stream.binance.com:9443/ws/btcusdt@kline_5m
wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms
wss://stream.binance.com:9443/ws/btcusdt@trade
wss://stream.binance.com:9443/stream?streams=btcusdt@kline_5m/ethusdt@kline_5m
```

### Binance Vision
```
https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2024-01.zip
https://data.binance.vision/data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2024-01.zip
https://data.binance.vision/data/spot/monthly/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2024-01.zip
```
