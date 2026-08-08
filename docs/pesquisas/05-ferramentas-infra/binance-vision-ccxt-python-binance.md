# Topico: Binance Vision, CCXT e python-binance (Acesso a Dados e APIs de Exchange)

**Data:** 2026-07-15
**Categoria:** Ferramentas / Infra

## TL;DR

Para acessar dados historicos e em tempo real de criptomoedas existem tres camadas complementares. Binance Vision (`data.binance.vision`) oferece dados historicos gratuitos em CSV ZIP desde 2017, sem autenticacao, ideal para backtest e pesquisa. A Binance REST API fornece dados e execucao em tempo real com limite de 1200 weight/minuto por IP. A Binance WebSocket permite streaming com 5 conexoes por IP e 200 streams por conexao. Para abstrair multiplas exchanges, CCXT (MIT, 43k stars, 104+ exchanges) unifica a API. Para Binance especifica, python-binance (sammchardy, MIT) oferece wrapper completo com async, WS e depth cache. O risco critico para operar do Brasil e o bloqueio de IP por restricao geografica, que pode ser silencioso (HTTP 403) e derrubar o bot sem aviso.

## Explicacao para criancas

Imagina que voce quer saber o preco de um monte de balas (criptomoedas) todos os dias durante varios anos. Existem tres jeitos de conseguir isso:

1. **Binance Vision** e como uma biblioteca publica: voce entra, baixa pacotinhos ZIP com planilhas de todos os dias desde 2017, de graca, sem precisar mostrar nenhum documento. E perfeito para estudar o passado.

2. **REST API** e como pedir informacao ao balconista: voce faz um pedido e recebe a resposta na hora. Mas o balconista so atende 1200 pedidos por minuto, e se voce pedir muito rapido ele te manda esperar.

3. **WebSocket** e como uma ligacao telefonica que fica aberta: voce conecta uma vez e o balconista vai te passando os precos novos em tempo real, sem voce precisar pedir de novo.

O CCXT e como um tradutor universal: em vez de aprender a falar com cada balconista de cada loja diferente (Binance, Bybit, OKX), voce usa uma unica lingua e o CCXT traduz para cada loja. O python-binance e um tradutor especializado so na Binance, com mais recursos especificos dela.

O problema e que algumas lojas nao atendem pessoas do Brasil. A Binance pode bloquear seu IP silenciosamente, sem avisar, e seu bot fica parado sem entender o que aconteceu.

## Como funciona tecnicamente

### Binance Vision (data.binance.vision)

Binance Vision e um bucket S3 publico hospedado em `s3-ap-northeast-1.amazonaws.com/data.binance.vision`. Nao requer autenticacao, API key, ou conta. Os dados sao organizados em:

- **spot**: `/data/spot/monthly/klines/{SYMBOL}/{INTERVAL}/{SYMBOL}-{INTERVAL}-{YYYY-MM}.zip`
- **futures/um** (USD-M): `/data/futures/um/monthly/klines/{SYMBOL}/{INTERVAL}/...`
- **futures/cm** (COIN-M): `/data/futures/cm/monthly/klines/...`
- **trades**, **aggTrades**, **bookTicker**, **indexPriceKlines**

Tipos de dados disponiveis: klines (OHLCV), trades, aggTrades, bookTicker, indexPriceKlines, premiumIndex. Formato: CSV dentro de ZIP. Cada arquivo diario ou mensal contem os dados aggregados. Desde 2017 para spot, desde 2019 para futures.

Importante: a partir de 1 de janeiro de 2025, timestamps de SPOT data passaram a ser em microssegundos (antes eram em milissegundos). Scripts que nao lidam com isso podem quebrar silenciosamente, gerando datas absurdas (ano 50000+). A deteccao deve ser por magnitude: se timestamp > 1e12, provavelmente microssegundos; se < 1e12, milissegundos. Converter ambos para segundos (dividir por 1e6 ou 1e3 respectivamente) e entao criar datetime.

Estrutura de klines CSV (12 colunas):
```
open_time, open, high, low, close, volume, close_time, quote_volume, count,
taker_buy_volume, taker_buy_quote_volume, ignore
```

Intervalos disponiveis: 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M. Para o crypto-correl-bot, 5m e o intervalo primario (balance entre granularidade e volume de dados).

Download paralelo e trivial: cada arquivo e independente, sem dependencia entre eles. Scripts como `gcoban/binance-public-data-downloader` fazem download paralelo (5 concorrentes) com cache, retry e verificacao SHA-256. Cada arquivo ZIP mensal de 5m para um symbol ativo contem ~105k linhas (30 dias * 24h * 12 candles/h) e ocupa ~5-15MB descomprimido, ~1-3MB em ZIP.

Exemplo de download programatico:
```bash
# Baixar 1 mes de BTCUSDT 5m spot
curl -s "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2024-06.zip" -o BTCUSDT-5m-2024-06.zip
# Verificar checksum
curl -s "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2024-06.zip.CHECKSUM"
```

Estrategia otimizada de download: usar arquivos mensais para meses completos (12 requests/ano em vez de 365) e arquivos diarios apenas para as bordas do range (inicio e fim parciais). Isso reduz o numero de requests em ~30x comparado a download diario puro.

### Binance REST API

A REST API opera em `api.binance.com` (spot), `fapi.binance.com` (USD-M futures), `dapi.binance.com` (COIN-M futures). Autenticacao via HMAC-SHA256, RSA, ou Ed25519. O sistema de rate limit e por peso (weight), nao por requisicao bruta:

| Limite | Janela | Comportamento ao exceder |
|---|---|---|
| Request Weight: 1200 | 1 minuto | HTTP 429 (Too Many Requests) |
| Raw Requests: 6100 | 5 minutos | HTTP 429 |
| Orders: 10/seg | 1 segundo | HTTP 429 |
| Orders: 100000/dia | 1 dia | HTTP 429 |

Cada endpoint tem um peso. `GET /api/v3/ticker/price` custa 1 weight. `GET /api/v3/depth?limit=5000` custa 250 weight. Ou seja, em 1 minuto voce pode fazer 1200 chamadas de preco, mas so 4 chamadas de orderbook profundo.

Se ignorar o 429, Binance escala para HTTP 418 ("I'm a Teapot"), que e o banimento real de IP. A duracao escala: primeiro ~2 minutos, depois ~30 minutos, depois horas, e violacoes persistentes resultam em ban permanente.

Klines via REST: maximo 1000 candles por chamada. Para 3 anos de 5m: ~315k candles = ~315 chamadas. Com peso 1 cada (klines custam weight 1-2 dependendo do endpoint), cabe folgadamente no limite de 1200/min.

### Binance WebSocket

WebSocket em `wss://stream.binance.com:9443` (spot) ou `wss://fstream.binance.com` (futures). Limite de 5 conexoes por IP, 200 streams por conexao (1024 streams total por IP com 5 conexoes).

Streams principais: `@trade`, `@kline_{interval}`, `@ticker`, `@depth`, `@bookTicker`. O stream `@kline_5m` envia um evento a cada 5 minutos com o candle fechado, mas tambem envia updates intermediarios durante a formacao do candle.

Reconexao: python-binance implementa reconexao automatica com maximo 5 retries e exponential backoff. O WebSocket pode ser combinado com REST para resiliencia: WS para tempo real, REST para validacao e recovery.

### CCXT

CCXT unifica 104+ exchanges em uma API comum. Metodos padronizados: `fetch_ohlcv()`, `fetch_ticker()`, `fetch_order_book()`, `create_order()`, `fetch_balance()`. Cada exchange herda da classe base `Exchange` e implementa seus metodos. Os dados sao normalizados para um formato comum (OHLCV como lista de [timestamp, o, h, l, c, v]).

Exemplo de uso multi-exchange:
```python
import ccxt

# Inicializar exchanges
binance = ccxt.binance()
bybit = ccxt.bybit()
okx = ccxt.okx()

# Mesma API para todas
for exchange in [binance, bybit, okx]:
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "5m", limit=100)
    ticker = exchange.fetch_ticker("BTC/USDT")
    print(f"{exchange.id}: last={ticker['last']}")
```

CCXT Pro (addon pago, nao open source) adiciona suporte a WebSocket para JS, PHP e Python. Sem o Pro, CCXT so faz REST. A partir da v4, CCXT Pro foi integrado ao CCXT principal como open source, eliminando a necessidade de licenca separada para WebSocket em Python.

Trade-offs do CCXT vs bibliotecas nativas:
- **Vantagem**: unificacao de API, migracao de exchange trivial, comunidade massiva (43k stars, 350+ contributors)
- **Desvantagem**: abstracao adiciona overhead (parsing, normalizacao), nem todos os endpoints especificos de cada exchange estao implementados, lag na adocao de novos endpoints (Binance adiciona endpoint, CCXT demora dias/semanas para implementar)
- **Quando usar CCXT**: multi-exchange, prototipagem rapida, insurance policy contra geoblock
- **Quando usar nativa (python-binance)**: single-exchange Binance, maxima performance, endpoints especificos nao cobertos pelo CCXT

Para o nosso caso, CCXT e util como camada de abstracao: se precisarmos migrar de Binance para Bybit ou OKX no futuro, o codigo muda minimamente. Mas para WebSocket em Python, precisamos ou do CCXT Pro ou de uma solucao nativa como python-binance.

### python-binance (sammchardy)

Wrapper nao-oficial da Binance REST API v3. Implementa todos os endpoints de General, Market Data e Account. Features principais:

- Asyncio nativo (AsyncClient)
- WebSocket com reconexao automatica e multiplexing (ThreadedWebsocketManager e BinanceSocketManager)
- CRUD via WebSocket (create/fetch/edit orders com latencia minima)
- Symbol Depth Cache (mantem orderbook local sincronizado)
- Historical Kline fetching (com paginacao automatica)
- Suporte a demo trading (`demo=True`)
- Suporte a RSA e EdDSA para autenticacao
- Proxy support (REST e WS)
- Orjson para JSON parsing mais rapido

Exemplo de WebSocket streaming:
```python
from binance import ThreadedWebsocketManager

def handle_message(msg):
    # msg e um dict com o evento do stream
    print(f"{msg['s']} close={msg['k']['c']}")

twm = ThreadedWebsocketManager()
twm.start()

# Subscrever a multiplas klines streams
twm.start_kline_socket(
    callback=handle_message,
    symbol="BTCUSDT",
    interval="5m"
)
# Adicionar mais symbols...
twm.join()
```

Exemplo de depth cache (orderbook local):
```python
from binance import ThreadedDepthCacheManager

dcm = ThreadedDepthCacheManager()
dcm.start()

depth_cache = dcm.start_depth_cache(
    symbol="BTCUSDT",
    callback=lambda cache: print(f"Bid: {cache.get_bids()}, Ask: {cache.get_asks()}")
)
```

Dependencias: requests, aiohttp, websockets, pycryptodome, dateparser. Licenca MIT.

### Comparativo de exchanges

| Aspecto | Binance | Bybit V5 | OKX V5 | dYdX | Hyperliquid |
|---|---|---|---|---|---|
| REST base | api.binance.com | api.bybit.com | www.okx.com | api.dydx.exchange | api.hyperliquid.xyz |
| Rate limit | 1200 weight/min | 120 req/5s | 20-60 req/2s | nao confirmado | nao confirmado |
| WS subs/conn | 5 streams | 10 topics | varia | nao confirmado | nao confirmado |
| Klines/call | 1000 | 1000 | 300 | nao confirmado | nao confirmado |
| Auth | HMAC/RSA/Ed25519 | HMAC + timestamp | HMAC + passphrase | API key + secret | wallet signing |
| Spot + Futures | APIs separadas | Unificado V5 | Unificado V5 | Perps apenas | Perps apenas |
| CEX/DEX | CEX | CEX | CEX | DEX | DEX |
| Custodia | Custodial | Custodial | Custodial | Non-custodial | Non-custodial |
| Dados gratis | Vision (CSV ZIP) | Nao confirmado | Nao confirmado | API publica | API publica |
| Risco BR | Alto (geoblock) | Medio | Medio | Baixo (DEX) | Baixo (DEX) |

## Estado do mercado em 2026

A Binance permanece a exchange dominante para trading algoritmico em 2026, com o maior volume e a API mais documentada. O sistema de weight-based de rate limit e o mais flexivel uma vez compreendido, mas tambem o mais complexo para iniciantes.

O movimento regulatorio (MiCA na Europa, CFTC/SEC nos EUA, CVM no Brasil) esta forçando exchanges centralizadas a restringir acesso por jurisdicao. Binance passou a aplicar geoblocks mais agressivos em 2025-2026, e o erro "Service unavailable from a restricted location" ou HTTP 403 silencioso tornou-se um problema real para bots rodando de IPs brasileiros.

Um relato documentado em 2026 (DEV Community) descreve um bot que ficou parado por 14 dias devido a um geoblock silencioso da Binance. O servidor recebia HTTP 403 (nao 429 de rate limit, nao 451 de legal), e o error handler tratava como falha transitoria, fazendo retry a cada 5 minutos por duas semanas. O diagnostico correto: `curl -v https://api.binance.com/api/v3/ping` do servidor revelou que o endpoint nem sequer era acessivel da regiao. A correcao foi migrar 6 funcoes para Coinbase Advanced Trade API, com uma camada de adapter para manter o resto do codigo agnostico a exchange. Licoes: (1) 403 de CDN pode ser geoblock, nao falha de auth, (2) tratar 403 diferente de 429 no error handler, (3) ter adapter layer para troca de exchange.

Exchanges DEX (dYdX, Hyperliquid) ganharam tracao como alternativa sem risco de geoblock, pois operam on-chain sem verificacao de KYC para API. Hyperliquid em particular cresceu significativamente em 2025-2026, com CCXT adicionando suporte certificado. Hyperliquid usa wallet signing (nao API key + secret), o que muda o modelo de autenticacao mas elimina risco de geoblock.

CCXT continua a biblioteca de referencia para multi-exchange, com 104+ exchanges e releases frequentes (v4.5.65 em julho 2026, 239 releases totais, 350+ contributors). A partir da v4, CCXT Pro (WebSocket) tornou-se open source, eliminando a necessidade de licenca paga para WS em Python. python-binance mantem atividade moderada (v1.0.37), mas e a opcao mais completa para Binance-especifico em Python.

O risco de bloqueio de IP brasileiro e o trade-off mais critico. A estrategia de mitigacao recomendada e: (1) usar Binance Vision para dados historicos (nao tem geoblock, e S3 publico), (2) ter um adapter layer que permite trocar de exchange sem reescrever o bot, (3) monitorar ativamente HTTP 403/418 e ter fallback automatico, (4) considerar DEX (Hyperliquid) como fallback sem risco de geoblock.

Um ponto adicional sobre restricoes: Binance usa geolocalizacao sofisticada (GPS, IP, SIM data) e tentar bypassar com VPN tem 78% de chance de outcome negativo segundo dados de 2026, incluindo banimento permanente e congelamento de fundos. A estrategia de VPN nao e viavel para producao.

## Ferramentas e APIs disponiveis

| Ferramenta | Versao | Licenca | Repo | Custo | Maturidade |
|---|---|---|---|---|---|
| Binance Vision | N/A (S3 publico) | Dados gratuitos | github.com/binance/binance-public-data | $0 | Alta (desde 2017) |
| Binance REST API | v3 (spot), v1 (futures) | Proprietaria | binance-docs.github.io/apidocs | $0 (dados), taxas de trade | Alta |
| Binance WebSocket | Streams API | Proprietaria | binance-docs.github.io/apidocs | $0 (dados), taxas de trade | Alta |
| CCXT | v4.5.65 (jul 2026) | MIT | github.com/ccxt/ccxt | $0 | Muito alta (43k stars, 350+ contributors) |
| CCXT Pro | Incluido em v4+ | MIT (open source desde v4) | github.com/ccxt/ccxt | $0 | Alta |
| python-binance | v1.0.37 | MIT | github.com/sammchardy/python-binance | $0 | Alta (7k stars) |
| binance-public-data-downloader | N/A | Nao confirmado | github.com/gcoban/binance-public-data-downloader | $0 | Media |
| binance-data-loader | N/A | Nao confirmado | github.com/HuakunShen/binance-data-loader | $0 | Baixa |

## Por que importa para o crypto-correl-bot

### O que usamos hoje

O projeto usa Binance Vision como fonte primaria de dados historicos (CSV ZIP para backtest), com REST API e WebSocket para dados em tempo real. python-binance e o wrapper de escolha pela riqueza de features (async, depth cache, CRUD via WS). CCXT esta disponivel como camada de abstracao para multi-exchange, mas nao e a interface primaria.

### Trade-offs e consideracoes

**Binance Vision vs REST API para dados historicos:** Vision e infinitamente mais eficiente para backfill massivo. Baixar 30 symbols x 3 anos x 5m via REST exigiria ~9450 chamadas (315 por symbol x 30), o que leva ~8 minutos no limite de peso. Via Vision, sao 1080 arquivos ZIP (30 symbols x 36 meses), baixaveis em paralelo em ~2 minutos. Alem disso, Vision nao consume cota de rate limit da API.

**python-binance vs CCXT para tempo real:** python-binance e mais completo para Binance (depth cache, CRUD via WS, multiplexing), mas trava o projeto a uma exchange. CCXT unifica mas exige CCXT Pro para WS em Python (que era pago e agora e open source desde v4). Se o risco de geoblock da Binance se materializar, migrar para Bybit ou OKX via CCXT e trivial. Com python-binance, exigiria reescrever toda a camada de dados.

**Risco de geoblock (BR):** Este e o trade-off mais critico descoberto. A Binance pode bloquear IP brasileiro silenciosamente (HTTP 403, nao 429). Um relato de 2026 documenta 14 dias de bot parado por geoblock silencioso tratado como erro transitorio. Mitigacoes: (1) Binance Vision nao tem geoblock (S3 publico), entao dados historicos estao seguros. (2) Para tempo real, implementar adapter layer com CCXT para troca rapida de exchange. (3) Monitorar HTTP 403 explicitamente e nao tratar como retry transitorio. (4) Considerar DEX (Hyperliquid) como fallback sem risco de geoblock.

**Timestamps em microssegundos (2025+):** A mudanca de milissegundos para microssegundos em SPOT data a partir de 2025 pode quebrar parsers silenciosamente. O codigo de parsing deve detectar a magnitude do timestamp e converter adequadamente.

### O que poderiamos migrar

1. **Curto prazo:** Adicionar CCXT como adapter layer paralelo, mantendo python-binance para Binance-especifico. Custo baixo, beneficio alto (insurance policy para geoblock).

2. **Medio prazo:** Se geoblock se materializar, migrar inteiramente para CCXT + Bybit/OKX. Dados historicos continuam via Binance Vision (S3, sem geoblock).

3. **Longo prazo:** Avaliar Hyperliquid (DEX, sem geoblock, sem KYC) como fonte primaria, especialmente para dados de perps. CCXT ja tem suporte certificado.

## Referencias

1. Binance Public Data Repository: https://github.com/binance/binance-public-data
2. Binance Data Collection (S3): https://data.binance.vision/?prefix=data
3. CCXT Repository: https://github.com/ccxt/ccxt
4. CCXT Documentation: https://docs.ccxt.com
5. python-binance Repository: https://github.com/sammchardy/python-binance
6. python-binance PyPI: https://pypi.org/project/python-binance/
7. VoiceOfChain: API Rate Limits Comparison (Binance vs Bybit vs OKX): https://voiceofchain.com/academy/crypto-exchange-api-rate-limits-comparison
8. DEV Community: A Developer's Guide to Comparing Crypto Exchange APIs in 2026: https://dev.to/steven_hansen_04c7f869e72/a-developers-guide-to-comparing-crypto-exchange-apis-in-2026
9. VoiceOfChain: Binance API IP Ban Duration Explained: https://voiceofchain.com/academy/binance-api-ip-ban-duration
10. DEV Community: How I Fixed a 14-Day Trading Outage (Binance Geoblock): https://dev.to/whoffagents/how-i-fixed-a-14-day-trading-outage-by-swapping-binance-api-for-coinbase-geoblock-war-story-3ea6
11. gcoban/binance-public-data-downloader: https://github.com/gcoban/binance-public-data-downloader
12. HuakunShen/binance-data-loader: https://github.com/HuakunShen/binance-data-loader
