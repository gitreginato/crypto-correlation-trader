# Estrategia 08: Funding Rate Arbitrage

**ID:** STRAT-08
**Categoria:** Delta-Neutral / Carry
**Timeframe ideal:** 8h (funding period), 1d
**Horizonte:** Medio prazo (dias a semanas)
**Complexidade:** Media

## 1. Conceito

Funding Rate Arbitrage e uma estrategia delta-neutral que coleta pagamentos de funding de perpetual futures sem exposicao direcional ao preco. Mantem-se long em spot e short em perpetual (ou vice-versa), de forma que o movimento de preco se cancela e o lucro vem do funding rate.

### Intuicao

Perpetual futures nao tem vencimento. Para manter o preco do perp proximo ao spot, exchanges usam funding rates: a cada 8 horas, longs pagam shorts (funding positivo) ou shorts pagam longs (funding negativo). Se voce esta long spot e short perp, e o funding e positivo, voce recebe o pagamento a cada 8 horas. O preco pode subir ou cair que seu P&L direcional e zero.

### Matematica simples

```
Capital: $10,000
Funding rate: 0.01% a cada 8h (positivo, longs pagam shorts)
Posicao: Long $5,000 spot + Short $5,000 perp

Pagamento por ciclo de 8h: $5,000 * 0.01% = $0.50
Ciclos por dia: 3
Renda diaria: $1.50
Renda anual: $547.50 (5.47% a.a.)

SE funding rate subir para 0.05% (bull market extremo):
Renda anual: $2,737.50 (27.4% a.a.)
```

## 2. Fundamentacao Teorica

### 2.1 Funding Rate

```
Funding Rate = Premium Index + Interest Rate

Premium Index = (Perp Price - Spot Price) / Spot Price
Interest Rate = 0.01% por 8h (default Binance, pode variar)

Clamp: funding rate limitado a [-0.75%, +0.75%] por 8h na Binance
```

### 2.2 Quando o funding e positivo

```
Perp > Spot (contango): longs estao alavancados e otimistas
Funding > 0: longs pagam shorts
Estrategia: LONG spot + SHORT perp = recebe funding
```

### 2.3 Quando o funding e negativo

```
Perp < Spot (backwardation): shorts estao alavancados e pessimistas
Funding < 0: shorts pagam longs
Estrategia: SHORT spot + LONG perp = recebe funding
```

### 2.4 Basis (spread spot-perp)

```
Basis = Perp Price - Spot Price
Basis % = (Perp - Spot) / Spot

Basis positivo (contango): funding tende a ser positivo
Basis negativo (backwardation): funding tende a ser negativo

A relacao nao e 1:1 porque funding tambem tem componente de interest rate.
Mas na pratica, basis extremo = funding extremo.
```

### 2.5 Riscos principais

1. **Rate Flip**: funding vira de positivo para negativo. Voce para de receber e comeca a pagar.
2. **Basis Risk**: spot e perp podem divergir temporariamente. Se voce precisa fechar a posicao no momento errado, pode ter perda.
3. **Execution Cost**: fees de abertura e fechamento (2 trades) + slippage.
4. **Liquidation Risk**: a perna short em perp pode ser liquidada se o preco subir muito (mesmo que a perna long spot compense, voce precisa de margem).
5. **Borrow Cost (short spot)**: se voce faz short spot via borrow, paga taxa de emprestimo.

## 3. Parametros

| Parametro | Default | Range | Descricao |
|-----------|---------|-------|-----------|
| `min_funding_rate` | 0.0001 | 0.00005 a 0.001 | Funding rate minimo para entrar (0.01%) |
| `min_funding_annualized` | 0.05 | 0.03 a 0.20 | Yield anualizado minimo (5%) |
| `max_funding_rate` | 0.005 | 0.001 a 0.01 | Funding maximo (acima = anormal, risco de flip) |
| `funding_lookback` | 7 | 1 a 30 | Dias para avaliar historico de funding |
| `min_funding_consistency` | 0.7 | 0.5 a 0.9 | % de ciclos com funding a favor |
| `max_position_size` | 0.20 | 0.10 a 0.40 | Max % do portfolio por par |
| `leverage_perp` | 1 | 1 a 3 | Alavancagem na perna perp (1x = sem alavancagem) |
| `rebalance_threshold` | 0.05 | 0.02 a 0.10 | Diferenca de tamanho para rebalancear (5%) |
| `close_on_flip` | true | true, false | Fechar posicao se funding flipar |
| `max_holding_days` | 30 | 7 a 90 | Maximo de dias em posicao |

## 4. Sinais de Entrada

### 4.1 Positive Funding Arbitrage (long spot + short perp)

```
CONDICOES (todas):
1. Funding rate atual > min_funding_rate (0.01% por 8h)
2. Funding anualizado > min_funding_annualized (5% a.a.)
3. Funding rate < max_funding_rate (nao tao alto que e anormal)
4. Nos ultimos funding_lookback dias:
   - >= min_funding_consistency (70%) dos ciclos foram positivos
5. Volume 24h do par > min_volume (liquidez)
6. Basis atual > 0 (perp em premium, confirma direcao)

ENTRY:
  - Comprar $X no spot
  - Vender $X no perp (mesmo valor em USD)
  - Delta-neutral: preco sobe = spot ganha, perp perde, net = 0
```

### 4.2 Negative Funding Arbitrage (short spot + long perp)

```
CONDICOES:
1. Funding rate atual < -min_funding_rate
2. Funding anualizado < -min_funding_annualized
3. Funding rate > -max_funding_rate
4. Historico: >= 70% dos ciclos foram negativos
5. Volume e liquidez ok
6. Basis < 0 (perp em discount)

ENTRY:
  - Vender spot (via borrow ou ja tem a moeda)
  - Comprar perp
  - Delta-neutral: preco cai = short spot ganha, long perp perde, net = 0
```

### 4.3 Filtro de consistencia

```python
def check_funding_consistency(funding_history: pd.Series, threshold: float = 0.7) -> bool:
    """Check if funding rate has been consistently in one direction."""
    positive_ratio = (funding_history > 0).mean()
    negative_ratio = (funding_history < 0).mean()
    return max(positive_ratio, negative_ratio) >= threshold
```

## 5. Sinais de Saida

### 5.1 Saida por funding flip

```
SE close_on_flip = true:
    Posicao long spot + short perp:
        SE funding rate vira negativo por 2 ciclos consecutivos:
            FECHAR ambas as pernas
            RAZAO: comecou a pagar em vez de receber
```

### 5.2 Saida por yield baixo

```
SE funding_anualizado < min_funding_annualized * 0.5 (caiu para metade do minimo):
    FECHAR posicao
    RAZAO: yield nao compensa o risco de basis
```

### 5.3 Saida por tempo

```
SE dias_em_posicao > max_holding_days:
    FECHAR
    RAZAO: funding rate pode ter mudado de regime
```

### 5.4 Saida por basis extremo

```
SE |basis| > 5% (spot e perp divergiram muito):
    FECHAR
    RAZAO: basis extremo indica estresse, risco de liquidacao
```

### 5.5 Saida por drawdown

```
SE drawdown_da_posicao > 3% (custo de funding + basis):
    FECHAR
    RAZAO: perda nao esperada em estrategia delta-neutral
```

## 6. Gestao de Risco

### 6.1 Margin Management (perna perp)

```python
# A perna short em perp precisa de margem
# Se preco subir, a perna perp perde (unrealized loss)
# Mas a perna spot ganha (compensa)
# O problema e que a exchange so ve a perna perp

margin_required = position_value / leverage
maintenance_margin = margin_required * 0.4  # 40% maintenance

# Monitorar: se unrealized_loss > margin - maintenance_margin:
#   ADD MARGEM ou REDUZIR POSICAO
```

### 6.2 Rebalanceamento

```
SE preco subir 10%:
    Perna spot: +10% (ganho)
    Perna perp: -10% (perda)
    Net: 0
    MAS: a perna perp agora tem mais exposicao que a spot

SE |size_spot - size_perp| / size_spot > rebalance_threshold (5%):
    REBALANCEAR: ajustar perna perp para igualar spot
    CUSTO: fee de rebalanceamento
```

### 6.3 Maximo de posicoes

```
max_concurrent_positions = 5
max_per_asset = 1 (nao duplicar no mesmo par)
max_correlated = 2 (BTC spot+perp e BTC perp1+perp2 = correlacionado)
```

### 6.4 Kill switch

```
SE drawdown_total > 5%:
    PAUSAR (delta-neutral nao deveria ter 5% DD)
    Investigar: basis risk? funding flip? erro de execucao?
```

## 7. Implementacao Tecnica

### 7.1 Obter funding rate (Binance)

```python
import ccxt

def get_funding_rate(symbol: str = "BTC/USDT:USDT") -> dict:
    """Get current funding rate from Binance Futures."""
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    funding = exchange.fetch_funding_rate(symbol)
    return {
        "symbol": symbol,
        "funding_rate": funding["fundingRate"],
        "next_funding_time": funding["fundingDatetime"],
        "mark_price": funding["markPrice"],
    }

def get_funding_history(symbol: str, days: int = 7) -> pd.DataFrame:
    """Get funding rate history."""
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    since = exchange.milliseconds() - days * 24 * 60 * 60 * 1000
    history = exchange.fetch_funding_rate_history(symbol, since=since)
    return pd.DataFrame(history)
```

### 7.2 Calculo de yield anualizado

```python
def annualize_funding(daily_funding_rate: float) -> float:
    """Convert daily funding rate to annualized yield."""
    # Binance: 3 funding cycles per 8h = 3 per day
    # Daily rate = sum of 3 cycles
    # Annual = daily * 365
    return daily_funding_rate * 365
```

### 7.3 Execucao da arbitragem

```python
async def execute_funding_arb(symbol: str, size_usd: float, direction: str):
    """Execute funding rate arbitrage."""
    spot_symbol = symbol.replace(":USDT", "/USDT")
    perp_symbol = symbol

    if direction == "positive_funding":
        # Long spot, Short perp
        spot_order = await exchange_spot.create_market_buy_order(spot_symbol, size_usd / spot_price)
        perp_order = await exchange_perp.create_market_sell_order(perp_symbol, size_usd / perp_price)
    elif direction == "negative_funding":
        # Short spot (borrow), Long perp
        # Note: short spot requires borrowing the asset
        borrow_order = await exchange_spot.borrow(base_asset, size_usd / spot_price)
        spot_order = await exchange_spot.create_market_sell_order(spot_symbol, size_usd / spot_price)
        perp_order = await exchange_perp.create_market_buy_order(perp_symbol, size_usd / perp_price)

    return {"spot": spot_order, "perp": perp_order}
```

### 7.4 Monitoramento de P&L

```python
def compute_arb_pnl(
    entry_spot: float, entry_perp: float,
    current_spot: float, current_perp: float,
    size: float, funding_received: float,
    fees_paid: float,
) -> dict:
    """Compute P&L of funding arbitrage position."""
    # Directional P&L (should be ~0)
    spot_pnl = (current_spot - entry_spot) * size / entry_spot
    perp_pnl = -(current_perp - entry_perp) * size / entry_perp  # short
    directional_pnl = spot_pnl + perp_pnl

    # Total P&L
    total_pnl = funding_received + directional_pnl - fees_paid

    return {
        "directional_pnl": directional_pnl,
        "funding_received": funding_received,
        "fees_paid": fees_paid,
        "total_pnl": total_pnl,
        "roi": total_pnl / size,
    }
```

## 8. Metricas de Avaliacao

| Metrica | Target | Minimo Aceitavel |
|---------|--------|------------------|
| Yield anualizado | 10%+ | 5%+ |
| Sharpe ratio | 2.0+ | 1.5 (baixa volatilidade) |
| Max drawdown | < 3% | < 5% |
| Profit factor | 5.0+ | 3.0 |
| Avg holding period | 7-30 dias | 3-60 dias |
| Funding flip rate | < 10% | < 20% |
| Basis risk | < 1% | < 2% |

## 9. Backtest: O que validar

### 9.1 Yield por regime de mercado

```
Bull market (funding positivo alto):  yield esperado > 20% a.a.
Bear market (funding negativo):        yield esperado > 15% a.a. (short spot + long perp)
Lateral (funding baixo):               yield esperado < 5% a.a. (dificil)
```

### 9.2 Impacto de custos

```
Rodar com:
  - 0% fees (teorico)
  - 0.1% spot + 0.04% perp maker (Binance)
  - 0.1% spot + 0.075% perp taker (Binance)

Custo de entrada: 2 trades = ~0.14% a 0.175%
Custo de saida:   2 trades = ~0.14% a 0.175%
Custo total:      ~0.28% a 0.35%

SE yield_anualizado < 5%: custos comem o lucro
```

### 9.3 Validar frequency de flip

```
Para cada par:
  - Contar quantas vezes funding flipou de positivo para negativo (ou vice-versa)
  - Calcular tempo medio entre flips
  - Calcular % do tempo com funding a favor

Target: funding a favor >= 70% do tempo
```

## 10. Vantagens e Desvantagens

### Vantagens
- Delta-neutral (sem risco direcional)
- Yield previsivel (funding rate e conhecido a cada 8h)
- Sharpe ratio muito alto (baixa volatilidade)
- Funciona em qualquer mercado (bull, bear, lateral)
- Simples de entender e executar

### Desvantagens
- Renda baixa em mercados laterais (funding baixo)
- Risco de liquidacao na perna perp (precisa de margem)
- Short spot requer borrow (custo adicional)
- Basis risk em momentos de estresse
- Capital imobilizado (posicao pode durar semanas)
- Nao funciona bem com pouco capital (custos fixos relativos)

## 11. Combinacao com outras estrategias

| Combinacao | Sinergia | Como |
|------------|----------|------|
| + Todas as estrategias direcionais | Alta | Diversificacao (delta-neutral + direcional) |
| + Mean Reversion (STRAT-01) | Media | Funding extremo pode causar descolamento |
| + StatArb (STRAT-03) | Media | Funding como filtro para pares |
| + Liquidity Sweep (STRAT-08) | Media | Funding extremo = liquidez para sweep |

## 12. Referencias

- Kraken: "Funding rate arbitrage in crypto: how the strategy works"
- Hyperdash: "Basis Trading & Funding Rate Arbitrage Guide"
- BackQuant: "The Basis Trade Explained: Cash and Carry in Crypto"
- Button.xyz: "Funding Rate Arbitrage: Capture Perp Funding at Scale"
- NYXANCE: "Basis Trading in Crypto Perps"
