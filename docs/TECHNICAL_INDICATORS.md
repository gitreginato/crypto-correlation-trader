# Guia Completo de Indicadores e Metricas de Analise Grafica para Trading de Criptomoedas

Este documento cobre 27 indicadores essenciais de analise tecnica para trading de criptomoedas, com formulas, interpretacao, configuracoes e codigo Python pronto para uso.

---

## 1. Fibonacci Retracement e Extension

### O que e
Ferramenta de analise tecnica baseada na sequencia de Fibonacci para identificar niveis de suporte e resistencia potenciais.

### Formula/Calculo

**Retracements (para uptrend):**
```
D = H - L (diferenca total)
23.6% = H - (0.236 x D)
38.2% = H - (0.382 x D)
50.0% = H - (0.500 x D)
61.8% = H - (0.618 x D)
78.6% = H - (0.786 x D)
```

**Retracements (para downtrend):**
```
23.6% = L + (0.236 x D)
38.2% = L + (0.382 x D)
50.0% = L + (0.500 x D)
61.8% = L + (0.618 x D)
78.6% = L + (0.786 x D)
```

**Extensions:**
```
127.2% = C + (1.272 x AB)
161.8% = C + (1.618 x AB)
261.8% = C + (2.618 x AB)
```

### Interpretacao
- **23.6% - 38.2%**: Retracamento raso, indica momento forte
- **50%**: Ponto medio psicologico, amplamente respeitado
- **61.8%**: Nivel mais importante (Golden Ratio), reversoes saudaveis
- **78.6%**: Retracamento profundo, possivel continuacao de tendencia

### Codigo Python

```python
import pandas as pd
import numpy as np

def fibonacci_retracement(high, low, trend='up'):
    D = high - low
    levels = {
        '23.6%': high - (0.236 * D) if trend == 'up' else low + (0.236 * D),
        '38.2%': high - (0.382 * D) if trend == 'up' else low + (0.382 * D),
        '50.0%': high - (0.500 * D) if trend == 'up' else low + (0.500 * D),
        '61.8%': high - (0.618 * D) if trend == 'up' else low + (0.618 * D),
        '78.6%': high - (0.786 * D) if trend == 'up' else low + (0.786 * D)
    }
    return levels

def fibonacci_extension(A, B, C, trend='up'):
    AB = B - A
    if trend == 'up':
        levels = {
            '127.2%': C + (1.272 * AB),
            '161.8%': C + (1.618 * AB),
            '261.8%': C + (2.618 * AB)
        }
    else:
        levels = {
            '127.2%': C - (1.272 * AB),
            '161.8%': C - (1.618 * AB),
            '261.8%': C - (2.618 * AB)
        }
    return levels
```

---

## 2. Volume Profile (VPVR) e Value Area

### O que e
Volume Profile mostra a distribuicao de volume em diferentes niveis de preco, identificando onde ocorreu a maior atividade de trading.

### Formula/Calculo
- **POC**: Nivel de preco com maior volume total
- **Value Area (VA)**: 70% do volume total centrado no POC
- **VAH**: Limite superior da area de valor
- **VAL**: Limite inferior da area de valor

### Interpretacao
- **POC**: Nivel de preco mais negociado, atua como magnet
- **Dentro da VA**: Mercado em equilibrio
- **Fora da VA**: Teste de aceitacao/rejeicao

### Codigo Python

```python
def volume_profile(df, price_bins=100, va_percentage=0.70):
    price_min = df['low'].min()
    price_max = df['high'].max()
    bin_edges = np.linspace(price_min, price_max, price_bins + 1)
    volume_by_price = np.zeros(price_bins)
    
    for _, row in df.iterrows():
        price_range = row['high'] - row['low']
        if price_range == 0:
            bin_idx = int((row['close'] - price_min) / (price_max - price_min) * price_bins)
            bin_idx = max(0, min(bin_idx, price_bins - 1))
            volume_by_price[bin_idx] += row['volume']
        else:
            for i in range(price_bins):
                overlap = min(row['high'], bin_edges[i+1]) - max(row['low'], bin_edges[i])
                if overlap > 0:
                    volume_by_price[i] += (overlap / price_range) * row['volume']
    
    poc_idx = np.argmax(volume_by_price)
    poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2
    
    total_volume = volume_by_price.sum()
    target_volume = total_volume * va_percentage
    va_lower = poc_idx
    va_upper = poc_idx
    current_volume = volume_by_price[poc_idx]
    
    while current_volume < target_volume:
        if va_lower > 0 and va_upper < price_bins - 1:
            if volume_by_price[va_lower - 1] >= volume_by_price[va_upper + 1]:
                va_lower -= 1
                current_volume += volume_by_price[va_lower]
            else:
                va_upper += 1
                current_volume += volume_by_price[va_upper]
        elif va_lower > 0:
            va_lower -= 1
            current_volume += volume_by_price[va_lower]
        elif va_upper < price_bins - 1:
            va_upper += 1
            current_volume += volume_by_price[va_upper]
        else:
            break
    
    return {
        'POC': poc_price,
        'VAL': bin_edges[va_lower],
        'VAH': bin_edges[va_upper + 1],
        'volume_by_price': volume_by_price,
        'bin_edges': bin_edges
    }
```

---

## 3. VWAP e MVWAP

### O que e
Volume Weighted Average Price: preco medio ponderado por volume, usado como benchmark de execucao e nivel de suporte/resistencia intraday.

### Formula/Calculo
```
Typical Price (TP) = (High + Low + Close) / 3
VWAP = Cumulative(TP x Volume) / Cumulative(Volume)
MVWAP = Media dos valores VWAP de N periodos anteriores
```

### Interpretacao
- **Preco acima VWAP**: Tendencia de alta, compradores no controle
- **Preco abaixo VWAP**: Tendencia de baixa, vendedores no controle

### Codigo Python

```python
def calculate_vwap(df):
    df = df.copy()
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_volume'] = df['typical_price'] * df['volume']
    df['cumulative_tp_volume'] = df['tp_volume'].cumsum()
    df['cumulative_volume'] = df['volume'].cumsum()
    df['vwap'] = df['cumulative_tp_volume'] / df['cumulative_volume']
    return df

def calculate_mvwap(df, period=10):
    df = calculate_vwap(df)
    df['mvwap'] = df['vwap'].rolling(window=period).mean()
    return df
```

---

## 4. RSI e Variacoes (Connors RSI, Stochastic RSI)

### Formula/Calculo
```
RSI Padrao:
Delta = Close - Close.shift(1)
Up = Delta.clip(lower=0)
Down = -Delta.clip(upper=0)
RS = EMA(Up) / EMA(Down)
RSI = 100 - (100 / (1 + RS))

Connors RSI = (RSI(Close, 3) + RSI(Streak, 2) + PercentRank(100)) / 3

Stochastic RSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI)
```

### Interpretacao
- **RSI > 70**: Sobrecompra, possivel reversao de baixa
- **RSI < 30**: Sobrevenda, possivel reversao de alta
- **Divergencia**: Preco faz novo high/low mas RSI nao confirma

### Codigo Python

```python
def calculate_rsi(df, period=14):
    df = df.copy()
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_stoch_rsi(df, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    df = calculate_rsi(df, period=rsi_period)
    rsi = df['rsi']
    lowest_rsi = rsi.rolling(window=stoch_period).min()
    highest_rsi = rsi.rolling(window=stoch_period).max()
    stoch_rsi = (rsi - lowest_rsi) / (highest_rsi - lowest_rsi) * 100
    df['stoch_rsi_k'] = stoch_rsi.rolling(window=k_period).mean()
    df['stoch_rsi_d'] = df['stoch_rsi_k'].rolling(window=d_period).mean()
    return df
```

---

## 5. MACD

### Formula/Calculo
```
MACD Line = EMA(Close, 12) - EMA(Close, 26)
Signal Line = EMA(MACD Line, 9)
Histogram = MACD Line - Signal Line
```

### Interpretacao
- **MACD acima de zero**: Tendencia de alta
- **Crossover bullish**: MACD cruza Signal de baixo para cima
- **Divergencia**: Preco faz novo high/low mas MACD nao confirma

### Codigo Python

```python
def calculate_macd(df, fast=12, slow=26, signal=9):
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    return df
```

---

## 6. Bollinger Bands e Bandwidth

### Formula/Calculo
```
Middle Band = SMA(Close, 20)
Upper Band = Middle Band + (2 x StdDev)
Lower Band = Middle Band - (2 x StdDev)
Bandwidth = (Upper Band - Lower Band) / Middle Band x 100
```

### Interpretacao
- **Squeeze (Bandwidth baixa)**: Volatilidade baixa, possivel breakout
- **Preco na banda superior**: Sobrecompra potencial
- **Preco na banda inferior**: Sobrevenda potencial

### Codigo Python

```python
def calculate_bollinger_bands(df, period=20, std_dev=2):
    df = df.copy()
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (std_dev * df['bb_std'])
    df['bb_lower'] = df['bb_middle'] - (std_dev * df['bb_std'])
    df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
    return df
```

---

## 7. ATR e Choppiness Index

### Formula/Calculo
```
ATR:
TR = MAX(High - Low, |High - PrevClose|, |Low - PrevClose|)
ATR = SMA(TR, 14)

Choppiness Index:
CHOP = 100 x LOG10(ATR_SUM / (HH - LL)) / LOG10(n)
```

### Interpretacao
- **ATR alto**: Alta volatilidade
- **CHOP > 61.8**: Mercado lateral (choppy)
- **CHOP < 38.2**: Mercado em tendencia

### Codigo Python

```python
def calculate_atr(df, period=14):
    df = df.copy()
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=period).mean()
    return df

def calculate_choppiness_index(df, length=14):
    df = calculate_atr(df, period=1)
    hh = df['high'].rolling(window=length).max()
    ll = df['low'].rolling(window=length).min()
    atr_sum = df['atr'].rolling(window=length).sum()
    df['chop'] = 100 * np.log10(atr_sum / (hh - ll)) / np.log10(length)
    return df
```

---

## 8. OBV (On Balance Volume)

### Formula/Calculo
```
Se Close > Close anterior: OBV = OBV anterior + Volume
Se Close < Close anterior: OBV = OBV anterior - Volume
```

### Interpretacao
- **OBV em alta**: Acumulacao (compra)
- **OBV em baixa**: Distribuicao (venda)
- **Divergencia**: Preco faz novo high mas OBV nao confirma

### Codigo Python

```python
def calculate_obv(df):
    df = df.copy()
    obv = np.where(df['close'] > df['close'].shift(1), df['volume'],
                   np.where(df['close'] < df['close'].shift(1), -df['volume'], 0))
    df['obv'] = pd.Series(obv, index=df.index).cumsum()
    return df
```

---

## 9. MFI (Money Flow Index)

### Formula/Calculo
```
TP = (High + Low + Close) / 3
RMF = TP x Volume
MFR = Positive MF / Negative MF
MFI = 100 - (100 / (1 + MFR))
```

### Interpretacao
- **MFI > 80**: Sobrecompra
- **MFI < 20**: Sobrevenda

### Codigo Python

```python
def calculate_mfi(df, period=14):
    df = df.copy()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['rmf'] = df['tp'] * df['volume']
    df['positive_mf'] = df['rmf'].where(df['tp'] > df['tp'].shift(1), 0)
    df['negative_mf'] = df['rmf'].where(df['tp'] < df['tp'].shift(1), 0)
    positive_mf_sum = df['positive_mf'].rolling(window=period).sum()
    negative_mf_sum = df['negative_mf'].rolling(window=period).sum()
    mfr = positive_mf_sum / negative_mf_sum
    df['mfi'] = 100 - (100 / (1 + mfr))
    return df
```

---

## 10. Ichimoku Cloud

### Formula/Calculo
```
Tenkan-sen = (Highest High 9 + Lowest Low 9) / 2
Kijun-sen = (Highest High 26 + Lowest Low 26) / 2
Senkou Span A = (Tenkan + Kijun) / 2 (shifted 26 forward)
Senkou Span B = (Highest High 52 + Lowest Low 52) / 2 (shifted 26 forward)
Chikou Span = Close (shifted 26 backward)
```

### Interpretacao
- **Preco acima da nuvem**: Tendencia de alta
- **Preco abaixo da nuvem**: Tendencia de baixa
- **TK Cross**: Tenkan cruza Kijun (sinal de entrada)

### Codigo Python

```python
def calculate_ichimoku(df, tenkan=9, kijun=26, senkou=52, displacement=26):
    df = df.copy()
    df['tenkan_sen'] = (df['high'].rolling(window=tenkan).max() + df['low'].rolling(window=tenkan).min()) / 2
    df['kijun_sen'] = (df['high'].rolling(window=kijun).max() + df['low'].rolling(window=kijun).min()) / 2
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(displacement)
    df['senkou_span_b'] = ((df['high'].rolling(window=senkou).max() + df['low'].rolling(window=senkou).min()) / 2).shift(displacement)
    df['chikou_span'] = df['close'].shift(-displacement)
    return df
```

---

## 11. Stochastic Oscillator

### Formula/Calculo
```
%K = 100 x (Close - Lowest Low) / (Highest High - Lowest Low)
%D = SMA(%K, 3)
```

### Interpretacao
- **%K > 80**: Sobrecompra
- **%K < 20**: Sobrevenda
- **Crossover bullish**: %K cruza %D de baixo para cima

### Codigo Python

```python
def calculate_stochastic(df, k_period=14, d_period=3, smooth_k=3):
    df = df.copy()
    lowest_low = df['low'].rolling(window=k_period).min()
    highest_high = df['high'].rolling(window=k_period).max()
    fast_k = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
    df['stoch_k'] = fast_k.rolling(window=smooth_k).mean()
    df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
    return df
```

---

## 12. ADX e DMI

### Formula/Calculo
```
+DI = 100 x EMA(+DM, 14) / ATR(14)
-DI = 100 x EMA(-DM, 14) / ATR(14)
DX = |+DI - -DI| / (+DI + -DI) x 100
ADX = EMA(DX, 14)
```

### Interpretacao
- **ADX > 25**: Tendencia forte
- **ADX < 20**: Tendencia fraca ou lateral
- **+DI > -DI**: Tendencia de alta

### Codigo Python

```python
def calculate_adx(df, period=14):
    df = df.copy()
    plus_dm = df['high'] - df['high'].shift()
    minus_dm = df['low'].shift() - df['low']
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    df['adx'] = dx.ewm(alpha=1/period, adjust=False).mean()
    return df
```

---

## 13. CCI (Commodity Channel Index)

### Formula/Calculo
```
TP = (High + Low + Close) / 3
CCI = (TP - SMA(TP)) / (0.015 x Mean Deviation)
```

### Interpretacao
- **CCI > 100**: Sobrecompra
- **CCI < -100**: Sobrevenda

### Codigo Python

```python
def calculate_cci(df, period=20, constant=0.015):
    df = df.copy()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_sma'] = df['tp'].rolling(window=period).mean()
    df['mean_deviation'] = (df['tp'] - df['tp_sma']).abs().rolling(window=period).mean()
    df['cci'] = (df['tp'] - df['tp_sma']) / (constant * df['mean_deviation'])
    return df
```

---

## 14. Williams %R

### Formula/Calculo
```
%R = -100 x (Highest High - Close) / (Highest High - Lowest Low)
```

### Interpretacao
- **%R > -20**: Sobrecompra
- **%R < -80**: Sobrevenda

### Codigo Python

```python
def calculate_williams_r(df, period=14):
    df = df.copy()
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    df['williams_r'] = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
    return df
```

---

## 15. Parabolic SAR

### Formula/Calculo
```
Uptrend: SAR = SAR anterior + AF x (EP - SAR anterior)
AF: inicia em 0.02, aumenta 0.02 a cada novo EP, maximo 0.20
EP: Highest high em uptrend, Lowest low em downtrend
```

### Interpretacao
- **SAR abaixo do preco**: Tendencia de alta
- **Preco cruza SAR**: Reversao de tendencia

### Codigo Python

```python
def calculate_parabolic_sar(df, af_start=0.02, af_increment=0.02, af_max=0.2):
    df = df.copy()
    high, low, close = df['high'].values, df['low'].values, df['close'].values
    n = len(df)
    sar = np.zeros(n)
    ep = np.zeros(n)
    af = np.zeros(n)
    uptrend = np.zeros(n, dtype=bool)
    sar[0], ep[0], af[0], uptrend[0] = low[0], high[0], af_start, True
    for i in range(1, n):
        if uptrend[i-1]:
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
            sar[i] = min(sar[i], low[i-1], low[i])
            if low[i] < sar[i]:
                uptrend[i] = False
                sar[i], ep[i], af[i] = ep[i-1], low[i], af_start
            else:
                uptrend[i] = True
                if high[i] > ep[i-1]:
                    ep[i], af[i] = high[i], min(af[i-1] + af_increment, af_max)
                else:
                    ep[i], af[i] = ep[i-1], af[i-1]
        else:
            sar[i] = sar[i-1] - af[i-1] * (sar[i-1] - ep[i-1])
            sar[i] = max(sar[i], high[i-1], high[i])
            if high[i] > sar[i]:
                uptrend[i] = True
                sar[i], ep[i], af[i] = ep[i-1], high[i], af_start
            else:
                uptrend[i] = False
                if low[i] < ep[i-1]:
                    ep[i], af[i] = low[i], min(af[i-1] + af_increment, af_max)
                else:
                    ep[i], af[i] = ep[i-1], af[i-1]
    df['psar'] = sar
    df['psar_uptrend'] = uptrend
    return df
```

---

## 16. SuperTrend

### Formula/Calculo
```
HL2 = (High + Low) / 2
Basic Upper Band = HL2 + (Multiplier x ATR)
Basic Lower Band = HL2 - (Multiplier x ATR)
Final Upper/Lower Band depende da tendencia anterior
```

### Interpretacao
- **SuperTrend verde**: Tendencia de alta
- **SuperTrend vermelho**: Tendencia de baixa
- **Mudanca de cor**: Sinal de entrada/saida

### Codigo Python

```python
def calculate_supertrend(df, atr_period=10, multiplier=3):
    df = calculate_atr(df, period=atr_period)
    df = df.copy()
    hl2 = (df['high'] + df['low']) / 2
    df['basic_upper_band'] = hl2 + (multiplier * df['atr'])
    df['basic_lower_band'] = hl2 - (multiplier * df['atr'])
    final_upper = df['basic_upper_band'].copy()
    final_lower = df['basic_lower_band'].copy()
    supertrend = np.zeros(len(df))
    trend = np.zeros(len(df))
    trend[0] = 1
    supertrend[0] = final_lower.iloc[0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > final_upper.iloc[i-1]:
            trend[i] = 1
        elif df['close'].iloc[i] < final_lower.iloc[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
        if trend[i] == 1:
            final_lower.iloc[i] = min(df['basic_lower_band'].iloc[i], final_lower.iloc[i-1])
            supertrend[i] = final_lower.iloc[i]
        else:
            final_upper.iloc[i] = max(df['basic_upper_band'].iloc[i], final_upper.iloc[i-1])
            supertrend[i] = final_upper.iloc[i]
    df['supertrend'] = supertrend
    df['supertrend_trend'] = trend
    return df
```

---

## 17. Volume Spread Analysis (VSA)

### O que e
Metodologia que analisa relacao entre volume, spread (range) e localizacao do fechamento.

### Interpretacao
- **Alto volume + spread largo + fechamento alto**: Forca compradora
- **Alto volume + spread largo + fechamento baixo**: Forca vendedora
- **Baixo volume + spread largo**: Fraqueza (no demand/no supply)
- **Alto volume + spread estreito**: Absorcao

### Codigo Python

```python
def calculate_vsa(df, lookback=20):
    df = df.copy()
    df['spread'] = df['high'] - df['low']
    df['close_position'] = (df['close'] - df['low']) / df['spread']
    df['volume_avg'] = df['volume'].rolling(window=lookback).mean()
    df['volume_ratio'] = df['volume'] / df['volume_avg']
    df.loc[(df['volume_ratio'] < 0.8) & (df['close_position'] < 0.3), 'vsa_signal'] = 'No Demand'
    df.loc[(df['volume_ratio'] < 0.8) & (df['close_position'] > 0.7), 'vsa_signal'] = 'No Supply'
    df.loc[(df['volume_ratio'] > 1.5) & (df['close_position'] > 0.5), 'vsa_signal'] = 'Stopping Volume'
    df.loc[df['volume_ratio'] > 2.0, 'vsa_signal'] = 'Climax'
    return df
```

---

## 18. Order Flow / Footprint Charts

### O que e
Visualizacao detalhada de volume bid/ask em cada nivel de preco dentro de uma vela.

### Interpretacao
- **Delta positivo**: Mais compras agressivas
- **Delta negativo**: Mais vendas agressivas
- **Imbalance**: Delta extremo em um nivel
- **Absorption**: Delta em uma direcao mas preco nao move

---

## 19. Delta Volume e CVD

### Formula/Calculo
```
Delta = Volume Ask (compras agressivas) - Volume Bid (vendas agressivas)
CVD = SUM(Delta, desde inicio do periodo)
```

### Interpretacao
- **CVD em alta**: Pressao compradora acumulada
- **CVD em baixa**: Pressao vendedora acumulada
- **Divergencia Preco/CVD**: Potencial reversao

### Codigo Python

```python
def calculate_delta_cvd(df):
    df = df.copy()
    df['delta'] = np.where(df['close'] > df['open'], df['volume'],
                           np.where(df['close'] < df['open'], -df['volume'], 0))
    df['cvd'] = df['delta'].cumsum()
    return df
```

---

## 20. Put/Call Ratio e Fear & Greed Index

### Interpretacao
- **PCR > 1**: Mais puts que calls (bearish)
- **FGI < 20**: Extreme Fear (oportunidade de compra)
- **FGI > 80**: Extreme Greed (oportunidade de venda)

### Codigo Python

```python
def get_fear_greed_index():
    import requests
    try:
        response = requests.get('https://api.alternative.me/fng/')
        data = response.json()
        return int(data['data'][0]['value'])
    except:
        return None
```

---

## 21. Funding Rate como Indicador

### Interpretacao
- **Funding positivo**: Longs pagam shorts (sentimento bullish)
- **Funding extremo (>0.05%)**: Overcrowded trade, possivel reversao
- **Funding extremo (<-0.05%)**: Overcrowded trade, possivel squeeze

### Codigo Python

```python
def analyze_funding_rate(df, extreme_threshold=0.05):
    df = df.copy()
    df['funding_extreme_long'] = df['funding_rate'] > extreme_threshold
    df['funding_extreme_short'] = df['funding_rate'] < -extreme_threshold
    df['funding_ma'] = df['funding_rate'].rolling(window=8).mean()
    return df
```

---

## 22. Open Interest como Indicador

### Interpretacao
- **OI em alta + Preco em alta**: Novo dinheiro entrando (tendencia forte)
- **OI em alta + Preco em baixa**: Novo dinheiro vendendo (tendencia forte)
- **OI em baixa + Preco em alta**: Short covering (tendencia fraca)
- **OI em baixa + Preco em baixa**: Long liquidation (tendencia fraca)

### Codigo Python

```python
def analyze_open_interest(df):
    df = df.copy()
    df['oi_change'] = df['open_interest'].pct_change()
    df.loc[(df['oi_change'] > 0) & (df['close'] > df['close'].shift()), 'oi_signal'] = 'Strong Bull'
    df.loc[(df['oi_change'] > 0) & (df['close'] < df['close'].shift()), 'oi_signal'] = 'Strong Bear'
    df.loc[(df['oi_change'] < 0) & (df['close'] > df['close'].shift()), 'oi_signal'] = 'Short Covering'
    df.loc[(df['oi_change'] < 0) & (df['close'] < df['close'].shift()), 'oi_signal'] = 'Long Liquidation'
    return df
```

---

## 23. Liquidations como Indicador

### Interpretacao
- **Alta liquidacao de longs**: Pressao vendedora, possivel fundo local
- **Alta liquidacao de shorts**: Pressao compradora, possivel topo local
- **Cascade**: Sequencia de liquidacoes causando movimento violento

---

## 24. Market Structure (HH, HL, LH, LL)

### Interpretacao
- **HH + HL**: Uptrend forte
- **LH + LL**: Downtrend forte
- **BOS (Break of Structure)**: Rompimento de swing anterior
- **CHoCH (Change of Character)**: Primeiro HL em downtrend ou LH em uptrend

### Codigo Python

```python
def identify_swing_points(df, n=3):
    df = df.copy()
    df['swing_high'] = (df['high'] == df['high'].rolling(window=2*n+1, center=True).max())
    df['swing_low'] = (df['low'] == df['low'].rolling(window=2*n+1, center=True).min())
    return df
```

---

## 25. Smart Money Concepts: Order Blocks, FVG, Liquidity Sweeps

### Interpretacao
- **Order Block**: Zona onde instituicoes entraram, atua como S/R
- **FVG (Fair Value Gap)**: Imbalance de preco, tende a ser preenchido
- **Liquidity Sweep**: Stop hunt antes de movimento real

### Codigo Python

```python
def identify_fvg(df):
    df = df.copy()
    df['bullish_fvg'] = False
    df['bearish_fvg'] = False
    for i in range(1, len(df) - 1):
        if df.iloc[i-1]['high'] < df.iloc[i+1]['low']:
            df.iloc[i, df.columns.get_loc('bullish_fvg')] = True
        if df.iloc[i-1]['low'] > df.iloc[i+1]['high']:
            df.iloc[i, df.columns.get_loc('bearish_fvg')] = True
    return df

def identify_order_blocks(df, min_impulse=2):
    df = df.copy()
    df['bullish_ob'] = False
    df['bearish_ob'] = False
    for i in range(len(df) - min_impulse - 1):
        if df.iloc[i]['close'] < df.iloc[i]['open']:
            impulse = all(df.iloc[j]['close'] > df.iloc[j]['open'] for j in range(i+1, i+1+min_impulse))
            if impulse:
                df.iloc[i, df.columns.get_loc('bullish_ob')] = True
        if df.iloc[i]['close'] > df.iloc[i]['open']:
            impulse = all(df.iloc[j]['close'] < df.iloc[j]['open'] for j in range(i+1, i+1+min_impulse))
            if impulse:
                df.iloc[i, df.columns.get_loc('bearish_ob')] = True
    return df
```

---

## 26. Elliott Wave Theory (Basico)

### O que e
Teoria que movimentos de mercado seguem padroes repetitivos de 5 ondas (impulso) e 3 ondas (correcao).

### Regras
- Onda 2 nao pode ir alem do inicio da onda 1
- Onda 3 nunca e a mais curta
- Onda 4 nao pode sobrepor o fim da onda 1

### Relacoes Fibonacci
- Onda 2 = 50%, 61.8% ou 78.6% da onda 1
- Onda 3 = 161.8% ou 261.8% da onda 1
- Onda 4 = 38.2% ou 50% da onda 3
- Onda 5 = 61.8% ou 100% da onda 1-3

---

## 27. Harmonic Patterns (Gartley, Bat, Butterfly)

### Gartley
```
AB = 61.8% de XA
BC = 38.2% - 88.6% de AB
CD = 127.2% - 161.8% de BC
D = 78.6% de XA
```

### Bat
```
AB = 38.2% - 50% de XA
BC = 38.2% - 88.6% de AB
CD = 161.8% - 261.8% de BC
D = 88.6% de XA
```

### Butterfly
```
AB = 78.6% de XA
BC = 38.2% - 88.6% de AB
CD = 161.8% - 261.8% de BC
D = 127.2% - 161.8% de XA
```

### Interpretacao
- Ponto D e a zona de reversao potencial (PRZ)
- Sempre procurar confluencia com outros indicadores
