#!/usr/bin/env python3
"""
Scientific Order Flow Dashboard - Professional Quantitative Trading Terminal

Features:
- Real-time WebSocket data from Binance Spot + Futures REST
- Microstructure: CVD, VWAP, Order Flow, VPIN, Kyle's Lambda, Amihud
- Technical: RSI, MACD, Bollinger, VWAP, SuperTrend, Fibonacci
- Statistical: ADF, KPSS, Hurst, Half-life, GARCH, VaR, Drawdowns
- Regime Detection: HMM (3 states), Structural Breakpoints
- Volume Profile: POC, VAH, VAL, Liquidity Heatmap
- Cross-sectional: Correlation, Lead-Lag, Granger, PCA
- Scientific Analysis Panel with interpretations
- Professional color theory (WCAG AA compliant)
- Responsive grid layout (1/3/4 columns)
- 50ms batched WebSocket updates
- Auto-refresh every 10s with meta tag
"""

import glob
import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Dict, List

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# ─── Constants & Configuration ──────────────────────────────────

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
DATA_DIR = Path("data/live")
UPDATE_INTERVAL_MS = 10000  # HTML meta refresh
WS_BATCH_MS = 50            # JavaScript batch interval

# Professional color palette (WCAG AA compliant on dark bg #0B0E14)
COLORS = {
    'bg': '#0B0E14',
    'surface': '#131722',
    'surface2': '#1A1E2D',
    'border': '#232838',
    'text': '#D1D4DC',
    'text_dim': '#787B86',
    'bull': '#26A69A',
    'bear': '#EF5350',
    'warn': '#FF9800',
    'info': '#42A5F5',
    'purple': '#AB47BC',
    'cyan': '#26C6DA',
    'orange': '#FF7043',
    'grid': '#1E222D',
}

SYM_COLORS = ['#42A5F5', '#26A69A', '#AB47BC', '#FF9800', '#26C6DA', '#FF7043', '#66BB6A', '#EC407A']

# ─── Technical Indicators ──────────────────────────────────────

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig

def calc_bollinger(series: pd.Series, period: int = 20, std_dev: float = 2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    return mid + std_dev * std, mid, mid - std_dev * std

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df['high'] + df['low'] + df['close']) / 3
    return (tp * df['volume']).cumsum() / df['volume'].cumsum()

def calc_supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3):
    atr = calc_atr(df, atr_period)
    hl2 = (df['high'] + df['low']) / 2
    upper = (hl2 + multiplier * atr).values
    lower = (hl2 - multiplier * atr).values
    close = df['close'].values

    trend = [1] * len(df)
    st = [float(lower[0])] * len(df)
    final_upper = upper.copy()
    final_lower = lower.copy()

    for i in range(1, len(df)):
        if close[i] > final_upper[i-1]:
            trend[i] = 1
        elif close[i] < final_lower[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]

        if trend[i] == 1:
            final_lower[i] = min(lower[i], final_lower[i-1])
            st[i] = float(final_lower[i])
        else:
            final_upper[i] = max(upper[i], final_upper[i-1])
            st[i] = float(final_upper[i])

    return pd.Series(st, index=df.index), pd.Series(trend, index=df.index)

def calc_fibonacci(high: float, low: float) -> Dict[str, float]:
    d = high - low
    return {
        '0%': high,
        '23.6%': high - 0.236*d,
        '38.2%': high - 0.382*d,
        '50%': high - 0.5*d,
        '61.8%': high - 0.618*d,
        '78.6%': high - 0.786*d,
        '100%': low,
    }

# ─── Microstructure Metrics ────────────────────────────────────

def calc_cvd(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    buys = trades[~trades['is_buyer_maker']]['quantity'].sum()
    sells = trades[trades['is_buyer_maker']]['quantity'].sum()
    return float(buys - sells)

def calc_kyle_lambda(returns: pd.Series, volumes: pd.Series) -> float:
    aligned = pd.DataFrame({'ret': returns.abs(), 'vol': volumes}).dropna()
    if len(aligned) < 20 or aligned['vol'].std() == 0:
        return 0.0
    try:
        lambda_est = np.linalg.lstsq(aligned[['vol']], aligned['ret'], rcond=None)[0][0]
        return float(lambda_est)
    except (np.linalg.LinAlgError, ValueError, IndexError) as e:
        logger.warning("Kyle lambda calculation failed: %s", e)
        return 0.0

def calc_amihud(returns: pd.Series, volumes: pd.Series, window: int = 20) -> float:
    aligned = pd.DataFrame({'ret': returns.abs(), 'vol': volumes}).dropna()
    if len(aligned) < window:
        return 0.0
    illiq = (aligned['ret'] / aligned['vol']).rolling(window).mean()
    return float(illiq.iloc[-1]) if not np.isnan(illiq.iloc[-1]) else 0.0

def calc_volume_profile(trades: pd.DataFrame, bins: int = 50) -> Dict:
    if trades.empty:
        return {}

    price_min = trades['price'].min()
    price_max = trades['price'].max()
    bin_edges = np.linspace(price_min, price_max, bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    volume_profile = np.zeros(bins)
    for _, row in trades.iterrows():
        idx = np.searchsorted(bin_edges, row['price']) - 1
        if 0 <= idx < bins:
            volume_profile[idx] += row['quantity']

    poc_idx = np.argmax(volume_profile)
    poc_price = bin_centers[poc_idx]

    total_vol = volume_profile.sum()
    target_vol = total_vol * 0.7
    cum_vol = volume_profile[poc_idx]
    low_idx = high_idx = poc_idx

    while cum_vol < target_vol and (low_idx > 0 or high_idx < bins - 1):
        if low_idx > 0 and (high_idx >= bins - 1 or volume_profile[low_idx-1] >= volume_profile[high_idx+1]):
            low_idx -= 1
            cum_vol += volume_profile[low_idx]
        elif high_idx < bins - 1:
            high_idx += 1
            cum_vol += volume_profile[high_idx]
        else:
            break

    return {
        'poc_price': float(poc_price),
        'vah_price': float(bin_centers[high_idx]),
        'val_price': float(bin_centers[low_idx]),
        'bins': bin_centers.tolist(),
        'volumes': volume_profile.tolist(),
        'total_volume': float(total_vol),
        'volume_in_va': float(cum_vol),
        'poc_idx': int(poc_idx),
        'vah_idx': int(high_idx),
        'val_idx': int(low_idx),
    }

def calc_order_book_metrics(ob: pd.DataFrame) -> Dict:
    if ob.empty:
        return {}

    latest = ob.iloc[-1]
    bid_px = [latest.get(f'bid_{i}_price', 0) for i in range(5)]
    bid_qty = [latest.get(f'bid_{i}_qty', 0) for i in range(5)]
    ask_px = [latest.get(f'ask_{i}_price', 0) for i in range(5)]
    ask_qty = [latest.get(f'ask_{i}_qty', 0) for i in range(5)]

    spread = ask_px[0] - bid_px[0]
    mid = (ask_px[0] + bid_px[0]) / 2
    spread_bps = (spread / mid) * 10000 if mid > 0 else 0

    bid_depth = sum(bid_qty)
    ask_depth = sum(ask_qty)
    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0

    return {
        'mid_price': float(mid),
        'spread': float(spread),
        'spread_bps': float(spread_bps),
        'bid_depth': float(bid_depth),
        'ask_depth': float(ask_depth),
        'imbalance': float(imbalance),
    }

# ─── Statistical Analysis ──────────────────────────────────────

def test_stationarity_adf(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import adfuller
    series = series.dropna()
    if len(series) < 20:
        return {'error': 'Insufficient data'}
    result = adfuller(series, autolag='AIC')
    return {
        'statistic': float(result[0]),
        'p_value': float(result[1]),
        'critical_values': {k: float(v) for k, v in result[4].items()},
        'stationary': result[1] < 0.05,
    }

def test_stationarity_kpss(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import kpss
    series = series.dropna()
    if len(series) < 20:
        return {'error': 'Insufficient data'}
    stat, pval, lags, crit = kpss(series, regression='c', nlags='auto')
    return {
        'statistic': float(stat),
        'p_value': float(pval),
        'critical_values': {k: float(v) for k, v in crit.items()},
        'stationary': pval > 0.05,
    }

def calc_hurst(series: pd.Series) -> Dict:
    series = series.dropna().values
    if len(series) < 30:
        return {'hurst': 0.5, 'interpretation': 'Insufficient data'}

    max_lag = min(100, len(series) // 4)
    max_lag = max(max_lag, 3)
    lags = np.logspace(np.log10(2), np.log10(max_lag), 20).astype(int)
    lags = np.unique(lags[lags >= 2])

    rs_vals = []
    for lag in lags:
        if lag >= len(series):
            continue
        n_chunks = len(series) // lag
        if n_chunks < 2:
            continue
        chunk_rs = []
        for i in range(n_chunks):
            chunk = series[i*lag:(i+1)*lag]
            if len(chunk) < 2:
                continue
            mean_chunk = np.mean(chunk)
            cumsum = np.cumsum(chunk - mean_chunk)
            R = np.max(cumsum) - np.min(cumsum)
            S = np.std(chunk)
            if S > 0:
                chunk_rs.append(R / S)
        if chunk_rs:
            rs_vals.append(np.mean(chunk_rs))

    if len(rs_vals) < 3:
        return {'hurst': 0.5, 'interpretation': 'Insufficient data'}

    log_lags = np.log(lags[:len(rs_vals)])
    log_rs = np.log(rs_vals)
    slope, intercept, r_val, p_val, std_err = __import__('scipy.stats').stats.linregress(log_lags, log_rs)
    hurst = slope

    if hurst < 0.45:
        interp = "Anti-persistent (mean reverting)"
    elif hurst < 0.55:
        interp = "Random walk (no memory)"
    elif hurst < 0.65:
        interp = "Persistent (trending)"
    else:
        interp = "Strongly persistent (strong trend memory)"

    return {
        'hurst': float(hurst),
        'r_squared': float(r_val**2),
        'p_value': float(p_val),
        'interpretation': interp,
    }

def calc_half_life(series: pd.Series) -> Dict:
    series = series.dropna().values
    if len(series) < 30:
        return {'half_life': float('inf'), 'interpretation': 'Insufficient data'}

    y = series[1:] - series[:-1]
    x = series[:-1]

    if np.std(x) == 0:
        return {'half_life': float('inf'), 'interpretation': 'Zero variance'}

    try:
        X = np.column_stack([x, np.ones_like(x)])
        theta_mu, theta, *_ = np.linalg.lstsq(X, y, rcond=None)[0]
        theta = -theta

        if theta <= 0:
            return {'half_life': float('inf'), 'theta': float(theta), 'interpretation': 'No mean reversion'}

        hl = np.log(2) / theta
        return {
            'half_life': float(hl),
            'theta': float(theta),
            'mu': float(-theta_mu/theta) if theta != 0 else float('nan'),
            'interpretation': f"Mean reversion half-life: {hl:.1f} periods",
        }
    except (np.linalg.LinAlgError, ValueError, IndexError) as e:
        logger.warning("Half-life calculation failed: %s", e)
        return {'half_life': float('inf'), 'interpretation': 'Calculation failed'}

def calc_var_cvar(returns: pd.Series, confidence: float = 0.95) -> Dict:
    returns = returns.dropna()
    if len(returns) < 30:
        return {'var': 0, 'cvar': 0}

    var = np.percentile(returns, (1 - confidence) * 100)
    cvar = returns[returns <= var].mean()

    mu, sigma = returns.mean(), returns.std()
    from scipy.stats import norm
    z = norm.ppf(1 - confidence)
    var_param = mu + z * sigma

    return {
        'var_historical': float(var),
        'cvar_historical': float(cvar),
        'var_parametric': float(var_param),
        'confidence': confidence,
        'n_obs': len(returns),
    }

def calc_drawdowns(prices: pd.Series) -> Dict:
    prices = prices.dropna()
    if len(prices) < 2:
        return {}

    cummax = prices.expanding().max()
    dd = (prices - cummax) / cummax

    max_dd = dd.min()
    max_dd_idx = dd.idxmin()
    peak_idx = prices.loc[:max_dd_idx].idxmax()

    current_dd = dd.iloc[-1]

    in_dd = dd < 0
    dd_durations = []
    current_duration = 0
    for is_in in in_dd:
        if is_in:
            current_duration += 1
        elif current_duration > 0:
            dd_durations.append(current_duration)
            current_duration = 0
    if current_duration > 0:
        dd_durations.append(current_duration)

    return {
        'max_drawdown': float(max_dd),
        'max_dd_date': str(max_dd_idx),
        'peak_date': str(peak_idx),
        'current_drawdown': float(current_dd),
        'avg_dd_duration': float(np.mean(dd_durations)) if dd_durations else 0,
        'max_dd_duration': int(max(dd_durations)) if dd_durations else 0,
        'drawdown_series': dd.values.tolist(),
    }

def detect_regimes_hmm(returns: pd.Series, n_states: int = 3) -> Dict:
    returns = returns.dropna().values.reshape(-1, 1)
    if len(returns) < 30:
        return {
            'error': 'Insufficient data',
            'regimes': [],
            'current_regime': -1,
            'current_probs': [],
            'transition_matrix': [],
        }

    try:
        from hmmlearn import hmm
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        scaled = scaler.fit_transform(returns)

        model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type='full',
            n_iter=100,
            random_state=42,
            tol=1e-4
        )
        model.fit(scaled)

        hidden_states = model.predict(scaled)
        probs = model.predict_proba(scaled)

        regime_stats = []
        for i in range(n_states):
            mask = hidden_states == i
            reg_returns = returns[mask].flatten()
            regime_stats.append({
                'state': i,
                'mean': float(np.mean(reg_returns)),
                'std': float(np.std(reg_returns)),
                'skew': float(__import__('scipy.stats').stats.skew(reg_returns)),
                'count': int(np.sum(mask)),
                'pct': float(np.mean(mask)),
            })

        # Sort by mean return but keep the original state index so current_regime matches
        state_to_rank = {stat['state']: idx for idx, stat in enumerate(regime_stats)}
        regime_stats_sorted = sorted(regime_stats, key=lambda x: x['mean'])

        return {
            'regimes': regime_stats_sorted,
            'current_regime': int(state_to_rank[hidden_states[-1]]),
            'current_probs': probs[-1].tolist(),
            'transition_matrix': model.transmat_.tolist(),
            'original_state': int(hidden_states[-1]),
        }
    except Exception as e:
        return {
            'error': str(e),
            'regimes': [],
            'current_regime': -1,
            'current_probs': [],
            'transition_matrix': [],
        }

def detect_breakpoints(series: pd.Series) -> List[int]:
    series = series.dropna().values
    if len(series) < 40:
        return []

    try:
        import ruptures as rpt
        model = "l2"
        min_size = max(10, len(series) // 4)
        algo = rpt.Pelt(model=model, min_size=min_size).fit(series)
        bkps = algo.predict(pen=10)
        return [int(b) for b in bkps[:-1]]
    except (ImportError, ValueError, RuntimeError) as e:
        logger.warning("Breakpoint detection failed: %s", e)
        return []

# ─── Cross-Sectional Analysis ──────────────────────────────────

def cross_sectional_analysis(symbols_data: Dict[str, pd.DataFrame]) -> Dict:
    returns_dict = {}
    for sym, df in symbols_data.items():
        if 'close' in df.columns:
            ret = df['close'].pct_change().dropna()
            returns_dict[sym] = ret

    if len(returns_dict) < 2:
        return {}

    returns_df = pd.DataFrame(returns_dict).dropna()
    if len(returns_df) < 30:
        return {}

    corr = returns_df.corr()

    lead_lag = {}
    syms = list(returns_dict.keys())
    for i, s1 in enumerate(syms):
        for s2 in syms[i+1:]:
            cc = cross_correlation(returns_dict[s1], returns_dict[s2])
            lead_lag[f'{s1}-{s2}'] = cc

    granger_results = {}
    for i, s1 in enumerate(syms):
        for s2 in syms[i+1:]:
            gc = granger_causality(returns_dict[s1], returns_dict[s2])
            granger_results[f'{s2}_causes_{s1}'] = gc

    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=min(3, len(syms)))
        pca.fit(returns_df)
        pca_result = {
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'components': pca.components_.tolist(),
        }
    except (ValueError, np.linalg.LinAlgError) as e:
        logger.warning("PCA fit failed: %s", e)
        pca_result = {}

    return {
        'correlation_matrix': corr.to_dict(),
        'avg_correlation': float(corr.values[np.triu_indices_from(corr.values, 1)].mean()),
        'max_correlation': float(corr.values[np.triu_indices_from(corr.values, 1)].max()),
        'min_correlation': float(corr.values[np.triu_indices_from(corr.values, 1)].min()),
        'lead_lag': lead_lag,
        'granger': granger_results,
        'pca': pca_result,
    }

def cross_correlation(s1: pd.Series, s2: pd.Series, max_lag: int = 20) -> Dict:
    df = pd.DataFrame({'s1': s1, 's2': s2}).dropna()
    if len(df) < 30:
        return {'error': 'Insufficient data'}

    corrs = []
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            c = np.corrcoef(df['s1'][:lag], df['s2'][-lag:])[0, 1]
        elif lag > 0:
            c = np.corrcoef(df['s1'][lag:], df['s2'][:-lag])[0, 1]
        else:
            c = np.corrcoef(df['s1'], df['s2'])[0, 1]
        corrs.append(float(c) if not np.isnan(c) else 0)

    max_corr = max(corrs, key=abs)
    max_lag_idx = corrs.index(max_corr) - max_lag

    return {
        'correlations': corrs,
        'lags': list(range(-max_lag, max_lag + 1)),
        'max_correlation': float(max_corr),
        'optimal_lag': int(max_lag_idx),
    }

def granger_causality(s1: pd.Series, s2: pd.Series, max_lag: int = 10) -> Dict:
    from statsmodels.tsa.stattools import grangercausalitytests
    df = pd.DataFrame({'s1': s1, 's2': s2}).dropna()
    if len(df) < 30:
        return {'error': 'Insufficient data'}

    try:
        gc_21 = grangercausalitytests(df[['s1', 's2']], maxlag=max_lag, verbose=False)
        gc_12 = grangercausalitytests(df[['s2', 's1']], maxlag=max_lag, verbose=False)

        pvals_21 = [gc_21[i+1][0]['ssr_ftest'][1] for i in range(max_lag)]
        pvals_12 = [gc_12[i+1][0]['ssr_ftest'][1] for i in range(max_lag)]

        return {
            's2_causes_s1': min(pvals_21) < 0.05,
            's1_causes_s2': min(pvals_12) < 0.05,
            'min_pval_s2_to_s1': float(min(pvals_21)),
            'min_pval_s1_to_s2': float(min(pvals_12)),
        }
    except (ValueError, ImportError, RuntimeError) as e:
        logger.warning("Granger causality test failed: %s", e)
        return {'error': 'Test failed'}

# ─── Data Loading ──────────────────────────────────────────────

def load_live_data(data_dir: str = "data/live", recent_hours: float = 1.0) -> Dict[str, pd.DataFrame]:
    import time as _time
    cutoff = _time.time() - recent_hours * 3600 if recent_hours > 0 else 0

    data = {}
    categories = ["order_book", "trades", "funding", "liquidations", "open_interest", "long_short", "fear_greed"]

    for cat in categories:
        files = sorted(glob.glob(f"{data_dir}/{cat}/*.parquet"))
        if recent_hours > 0:
            files = [f for f in files if Path(f).stat().st_mtime > cutoff]
        if files:
            dfs = [pd.read_parquet(f) for f in files]
            data[cat] = pd.concat(dfs, ignore_index=True)
        else:
            data[cat] = pd.DataFrame()

    return data

def build_ohlcv_from_trades(trades: pd.DataFrame, freq: str = "1min") -> Dict[str, pd.DataFrame]:
    ohlcv_dict = {}
    for sym in SYMBOLS:
        sym_df = trades[trades['symbol'] == sym].copy()
        if sym_df.empty:
            continue
        sym_df['timestamp'] = pd.to_datetime(sym_df['timestamp'])
        sym_df = sym_df.set_index('timestamp').sort_index()
        sym_df['is_buyer_maker'] = sym_df['is_buyer_maker'].astype(bool)

        # Aggressive volume split: buyer is taker when is_buyer_maker == False
        buy_vol = sym_df[~sym_df['is_buyer_maker']]['quantity'].resample(freq).sum()
        sell_vol = sym_df[sym_df['is_buyer_maker']]['quantity'].resample(freq).sum()

        ohlcv = sym_df.resample(freq).agg({
            'price': 'ohlc',
            'quantity': 'sum',
            'is_buyer_maker': 'count',
        })
        ohlcv.columns = ['open', 'high', 'low', 'close', 'volume', 'trade_count']
        ohlcv['buy_volume'] = buy_vol.reindex(ohlcv.index, fill_value=0)
        ohlcv['sell_volume'] = sell_vol.reindex(ohlcv.index, fill_value=0)
        ohlcv['net_volume'] = ohlcv['buy_volume'] - ohlcv['sell_volume']
        ohlcv['cvd'] = ohlcv['net_volume'].cumsum()
        ohlcv['imbalance'] = ohlcv['net_volume'] / (ohlcv['buy_volume'] + ohlcv['sell_volume']).replace(0, np.nan)
        ohlcv = ohlcv.dropna(subset=['open', 'high', 'low', 'close'])

        if len(ohlcv) >= 10:
            ohlcv_dict[sym] = ohlcv

    return ohlcv_dict

# ─── Analysis Pipeline ─────────────────────────────────────────

def analyze_symbol(symbol: str,
                   ohlcv: pd.DataFrame,
                   trades: pd.DataFrame,
                   order_book: pd.DataFrame,
                   funding: pd.DataFrame,
                   oi: pd.DataFrame,
                   ls: pd.DataFrame) -> Dict:

    close = ohlcv['close']
    returns = close.pct_change().dropna()

    # Technical indicators
    rsi = calc_rsi(close, 14)
    macd, macd_sig, macd_hist = calc_macd(close)
    bb_upper, bb_mid, bb_lower = calc_bollinger(close)
    atr = calc_atr(ohlcv, 14)
    vwap = calc_vwap(ohlcv)
    st, st_trend = calc_supertrend(ohlcv)
    fib = calc_fibonacci(close.tail(50).max(), close.tail(50).min())

    # Microstructure
    cvd = calc_cvd(trades)
    kyle_lambda = calc_kyle_lambda(returns, ohlcv['volume'])
    amihud = calc_amihud(returns, ohlcv['volume'])
    vol_profile = calc_volume_profile(trades)
    ob_metrics = calc_order_book_metrics(order_book)

    # Statistical
    adf = test_stationarity_adf(close)
    kpss = test_stationarity_kpss(close)
    adf_ret = test_stationarity_adf(returns)
    hurst = calc_hurst(returns)
    half_life = calc_half_life(close)
    var_cvar = calc_var_cvar(returns)
    drawdowns = calc_drawdowns(close)
    regimes = detect_regimes_hmm(returns)
    breakpoints = detect_breakpoints(close)

    # Funding/OI/LS
    funding_latest = funding[funding['symbol'] == symbol].sort_values('timestamp').iloc[-1] if not funding.empty and symbol in funding['symbol'].values else None
    oi_latest = oi[oi['symbol'] == symbol].sort_values('timestamp').iloc[-1] if not oi.empty and symbol in oi['symbol'].values else None
    ls_latest = ls[ls['symbol'] == symbol].sort_values('timestamp').iloc[-1] if not ls.empty and symbol in ls['symbol'].values else None

    # Sampling for charts (max 100 points)
    step = max(1, len(ohlcv) // 100)
    idx = ohlcv.index[::step].strftime("%H:%M")

    def _sample(series, default_value=0):
        return [float(x) if not np.isnan(x) else default_value for x in series.values[::step]]

    return {
        'symbol': symbol,
        'current_price': float(close.iloc[-1]),
        'price_change_pct': float((close.iloc[-1] / close.iloc[0] - 1) * 100),

        # Technical
        'rsi': float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50,
        'macd': float(macd.iloc[-1]) if not np.isnan(macd.iloc[-1]) else 0,
        'macd_signal': float(macd_sig.iloc[-1]) if not np.isnan(macd_sig.iloc[-1]) else 0,
        'macd_histogram': float(macd_hist.iloc[-1]) if not np.isnan(macd_hist.iloc[-1]) else 0,
        'bb_upper': float(bb_upper.iloc[-1]) if not np.isnan(bb_upper.iloc[-1]) else 0,
        'bb_lower': float(bb_lower.iloc[-1]) if not np.isnan(bb_lower.iloc[-1]) else 0,
        'bb_mid': float(bb_mid.iloc[-1]) if not np.isnan(bb_mid.iloc[-1]) else 0,
        'atr': float(atr.iloc[-1]) if not np.isnan(atr.iloc[-1]) else 0,
        'vwap': float(vwap.iloc[-1]) if not np.isnan(vwap.iloc[-1]) else 0,
        'supertrend': float(st.iloc[-1]) if not np.isnan(st.iloc[-1]) else 0,
        'supertrend_trend': 'UP' if st_trend.iloc[-1] == 1 else 'DOWN',
        'fib_levels': fib,

        # Microstructure
        'cvd': cvd,
        'kyle_lambda': kyle_lambda,
        'amihud': amihud,
        'volume_profile': vol_profile,
        'order_book': ob_metrics,

        # Statistical
        'stationarity': {
            'price_adf': adf,
            'price_kpss': kpss,
            'returns_adf': adf_ret,
        },
        'hurst': hurst,
        'half_life': half_life,
        'risk': var_cvar,
        'drawdowns': drawdowns,
        'regimes': regimes,
        'breakpoints': breakpoints[:10],

        # Positioning
        'funding_rate': float(funding_latest['funding_rate']) if funding_latest is not None else 0,
        'funding_class': 'Extreme Long' if (funding_latest is not None and funding_latest['funding_rate'] > 0.0005) else ('Extreme Short' if (funding_latest is not None and funding_latest['funding_rate'] < -0.0005) else 'Neutral'),
        'open_interest': float(oi_latest['open_interest']) if oi_latest is not None else 0,
        'oi_change_24h': float(oi_latest['open_interest'] / oi['open_interest'].iloc[0] - 1) if oi_latest is not None and len(oi) > 1 else 0,
        'long_short_ratio': float(ls_latest['long_short_ratio']) if ls_latest is not None else 1,
        'long_pct': float(ls_latest['long_account_pct']) if ls_latest is not None else 0.5,

        # Chart data (aliases for JS compatibility and proper names)
        'chart_data': {
            'timestamps': idx.tolist(),
            'close': _sample(close),
            'close_series': _sample(close),
            'rsi': _sample(rsi, 50),
            'rsi_series': _sample(rsi, 50),
            'macd': _sample(macd),
            'macd_series': _sample(macd),
            'macd_signal': _sample(macd_sig),
            'macd_sig_series': _sample(macd_sig),
            'macd_hist': _sample(macd_hist),
            'bb_upper': _sample(bb_upper),
            'bb_upper_series': _sample(bb_upper),
            'bb_lower': _sample(bb_lower),
            'bb_lower_series': _sample(bb_lower),
            'vwap': _sample(vwap),
            'vwap_series': _sample(vwap),
            'supertrend': _sample(st),
            'supertrend_series': _sample(st),
            'volume': _sample(ohlcv['volume']),
            'buy_vol_series': _sample(ohlcv['buy_volume']),
            'sell_vol_series': _sample(ohlcv['sell_volume']),
            'imbalance_series': _sample(ohlcv['imbalance'].fillna(0), 0),
            'cvd_series': _sample(ohlcv['cvd']),
        }
    }

def analyze_all(data: Dict[str, pd.DataFrame]) -> Dict:
    ohlcv = build_ohlcv_from_trades(data.get('trades', pd.DataFrame()))

    symbols = [s for s in SYMBOLS if s in ohlcv]
    results = {'symbols': symbols, 'analyses': {}, 'cross_sectional': {}}

    for sym in symbols:
        sym_trades = data['trades'][data['trades']['symbol'] == sym] if 'trades' in data else pd.DataFrame()
        sym_ob = data['order_book'][data['order_book']['symbol'] == sym] if 'order_book' in data else pd.DataFrame()

        results['analyses'][sym] = analyze_symbol(
            sym, ohlcv[sym], sym_trades, sym_ob,
            data.get('funding', pd.DataFrame()),
            data.get('open_interest', pd.DataFrame()),
            data.get('long_short', pd.DataFrame())
        )

    # Cross-sectional analysis
    if len(symbols) >= 2:
        symbols_ohlcv = {s: ohlcv[s] for s in symbols}
        results['cross_sectional'] = cross_sectional_analysis(symbols_ohlcv)

    # Fear & Greed
    fg = data.get('fear_greed', pd.DataFrame())
    if not fg.empty:
        fg = fg.sort_values('timestamp')
        results['fear_greed'] = {
            'current': int(fg['value'].iloc[-1]),
            'classification': fg['classification'].iloc[-1],
            'history_values': fg['value'].tail(30).tolist(),
            'history_dates': fg['timestamp'].dt.strftime('%m/%d').tail(30).tolist(),
        }

    # Liquidations
    liq = data.get('liquidations', pd.DataFrame())
    if not liq.empty:
        latest = liq.sort_values('timestamp').iloc[-1]
        results['liquidations'] = {
            'total_usd': float(latest.get('total_usd', 0)),
            'long_usd': float(latest.get('long_usd', 0)),
            'short_usd': float(latest.get('short_usd', 0)),
            'max_single_usd': float(latest.get('max_single_usd', 0)),
            'timestamp': str(latest.get('timestamp', '')),
        }

    return results

# ─── HTML Generation ───────────────────────────────────────────

def fmt_usd(v: float) -> str:
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.2f}M"
    if v >= 1e3:
        return f"${v/1e3:.1f}K"
    return f"${v:.0f}"


def generate_html(analysis: Dict) -> str:
    symbols = analysis['symbols']
    analyses = analysis['analyses']
    cs = analysis.get('cross_sectional', {})
    fg = analysis.get('fear_greed', {})
    liq = analysis.get('liquidations', {})

    def badge(text: str, color: str) -> str:
        return f'<span class="badge" style="--bdg-color: {color}; --bdg-bg: {color}22;">{text}</span>'

    def fmt_usd(v: float) -> str:
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        if v >= 1e3:
            return f"${v/1e3:.1f}K"
        return f"${v:.0f}"

    def class_for_value(v: float) -> str:
        if v > 0:
            return 'bull'
        if v < 0:
            return 'bear'
        return 'neutral'

    # KPI cards
    kpi_cards = ""
    for sym in symbols:
        a = analyses[sym]
        price = a['current_price']
        change = a['price_change_pct']
        rsi = a['rsi']
        cvd = a['cvd']
        imb = a['order_book'].get('imbalance', 0)
        trend = a['supertrend_trend']
        regime = a['regimes'].get('current_regime', -1)
        regime_text = {0: 'Bear', 1: 'Neutral', 2: 'Bull'}.get(regime, 'No Data')
        regime_color = {0: COLORS['bear'], 1: COLORS['text_dim'], 2: COLORS['bull']}.get(regime, COLORS['text_dim'])
        rsi_class = 'warn' if rsi > 70 else ('bull' if rsi < 30 else 'neutral')
        kpi_cards += f'''<div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-symbol">{sym}</span>
                {badge(regime_text, regime_color)}
            </div>
            <div class="kpi-price">{price:,.2f}</div>
            <div class="kpi-change {class_for_value(change)}">{change:+.2f}%</div>
            <div class="kpi-grid">
                <div class="kpi-item"><div class="kpi-label">RSI</div><div class="kpi-val {rsi_class}">{rsi:.1f}</div></div>
                <div class="kpi-item"><div class="kpi-label">OB Imb</div><div class="kpi-val {class_for_value(imb)}">{imb:+.3f}</div></div>
                <div class="kpi-item"><div class="kpi-label">CVD</div><div class="kpi-val {class_for_value(cvd)}">{cvd:+.2f}</div></div>
                <div class="kpi-item"><div class="kpi-label">ST</div><div class="kpi-val {('bull' if trend == 'UP' else 'bear')}">{trend}</div></div>
            </div>
        </div>'''

    # Summary table rows
    summary_rows = ""
    for sym in symbols:
        a = analyses[sym]
        rsi = a['rsi']
        rsi_class = 'warn' if rsi > 70 else ('bull' if rsi < 30 else 'neutral')
        rsi_signal = 'SELL' if rsi > 70 else ('BUY' if rsi < 30 else 'HOLD')
        imb = a['order_book'].get('imbalance', 0)
        cvd = a['cvd']
        trend = a['supertrend_trend']
        regime = a['regimes'].get('current_regime', -1)
        regime_text = {0: 'Bear', 1: 'Neutral', 2: 'Bull'}.get(regime, 'No Data')
        summary_rows += f'''<tr>
            <td class="sym"><strong>{sym}</strong></td>
            <td class="num mono">{a['current_price']:,.2f}</td>
            <td class="num mono {class_for_value(a['price_change_pct'])}">{a['price_change_pct']:+.2f}%</td>
            <td class="num mono {class_for_value(imb)}">{imb:+.4f}</td>
            <td class="num mono {class_for_value(cvd)}">{cvd:+.2f}</td>
            <td class="num mono {rsi_class}">{rsi:.1f}</td>
            <td class="mono {rsi_class}">{rsi_signal}</td>
            <td class="mono {('bull' if trend == 'UP' else 'bear')}">{trend}</td>
            <td class="mono"><span class="badge" style="--bdg-color: {COLORS['text_dim']};--bdg-bg: {COLORS['text_dim']}22;">{regime_text}</span></td>
        </tr>'''

    # Fibonacci rows
    fib_rows = ""
    for sym in symbols:
        a = analyses[sym]
        fib = a['fib_levels']
        price = a['current_price']
        for level, fp in fib.items():
            dist = ((price - fp) / price * 100) if price > 0 else 0
            near = 'near' if abs(dist) < 2 else ''
            fib_rows += f'<tr class="{near}"><td class="sym">{sym}</td><td class="num">{level}</td><td class="num mono">{fp:,.2f}</td><td class="num {class_for_value(dist)}">{dist:+.1f}%</td></tr>'

    # Positioning rows
    pos_rows = ""
    for sym in symbols:
        a = analyses[sym]
        fr = a['funding_rate'] * 100
        ratio = a['long_short_ratio']
        long_pct = a['long_pct'] * 100
        oi = a['open_interest']
        oi_chg = a['oi_change_24h'] * 100
        pos_rows += f'''<tr>
            <td class="sym"><strong>{sym}</strong></td>
            <td class="num mono {class_for_value(-fr)}">{fr:.4f}%</td>
            <td class="num mono">{ratio:.3f}</td>
            <td class="num mono">{long_pct:.1f}%</td>
            <td class="num mono">{fmt_usd(oi)}</td>
            <td class="num mono {class_for_value(oi_chg)}">{oi_chg:+.2f}%</td>
        </tr>'''

    # Liquidations
    if liq:
        total = liq['total_usd']
        long_l = liq['long_usd']
        short_l = liq['short_usd']
        max_s = liq['max_single_usd']
        long_pct = long_l / (total + 0.01) * 100
        short_pct = short_l / (total + 0.01) * 100
        liq_html = f'''<div class="stat-grid">
            <div class="stat-box"><span class="stat-label">Total 24h</span><span class="stat-value">{fmt_usd(total)}</span></div>
            <div class="stat-box"><span class="stat-label">Longs</span><span class="stat-value bear">{fmt_usd(long_l)}</span></div>
            <div class="stat-box"><span class="stat-label">Shorts</span><span class="stat-value bull">{fmt_usd(short_l)}</span></div>
            <div class="stat-box"><span class="stat-label">Max Single</span><span class="stat-value">{fmt_usd(max_s)}</span></div>
        </div>
        <div class="liq-bar"><div class="liq-long" style="width: {long_pct:.1f}%"></div><div class="liq-short" style="width: {short_pct:.1f}%"></div></div>
        <div class="liq-legend">Long: {long_pct:.1f}% · Short: {short_pct:.1f}%</div>'''
    else:
        liq_html = '<div class="empty-state">Aguardando liquidacoes...</div>'

    # Fear & Greed
    fg_color = COLORS['text_dim']
    if fg:
        val = fg['current']
        cls = fg['classification']
        fg_color = COLORS['bear'] if val < 25 else (COLORS['warn'] if val < 45 else (COLORS['info'] if val < 55 else (COLORS['bull'] if val < 75 else COLORS['purple'])))
        fg_html = f'''<div class="fg-gauge" style="--fg-color: {fg_color}">
            <div class="fg-value">{val}</div>
            <div class="fg-label">{cls}</div>
        </div>
        <div id="chart-fg" class="chart small"></div>'''
    else:
        fg_html = '<div class="empty-state">Aguardando Fear & Greed...</div>'

    # Correlation matrix
    corr_html = ""
    if cs.get('correlation_matrix'):
        corr = cs['correlation_matrix']
        corr_html = "<table class='data-table'><thead><tr><th></th>" + "".join(f"<th>{s}</th>" for s in symbols) + "</tr></thead><tbody>"
        for s1 in symbols:
            corr_html += f"<tr><td class='sym'><strong>{s1}</strong></td>"
            for s2 in symbols:
                v = corr[s1][s2]
                c = "bull" if v > 0.5 else ("bear" if v < -0.5 else "neutral")
                corr_html += f"<td class='num mono {c}'>{v:.2f}</td>"
            corr_html += "</tr>"
        corr_html += "</tbody></table>"

    # PCA
    pca_html = ""
    if cs.get('pca', {}).get('explained_variance'):
        pca = cs['pca']
        pca_html = "<table class='data-table'><thead><tr><th>Component</th><th>Variance</th></tr></thead><tbody>"
        for i, var in enumerate(pca['explained_variance']):
            pca_html += f"<tr><td>PC{i+1}</td><td class='num mono'>{var*100:.1f}%</td></tr>"
        pca_html += "</tbody></table>"

    # Scientific panels
    sci_panels = ""
    for sym in symbols:
        a = analyses[sym]
        adf = a['stationarity']['price_adf']
        adf_ret = a['stationarity']['returns_adf']
        hurst = a['hurst']['hurst']
        hurst_class = "ok" if hurst > 0.55 else ("warn" if hurst > 0.45 else "bad")
        hl = a['half_life'].get('half_life', float('inf'))
        hl_class = "ok" if not np.isinf(hl) and hl < 100 else ("warn" if not np.isinf(hl) and hl < 500 else "bad")
        hl_text = f"{hl:.1f} periods" if not np.isinf(hl) else "No MR"
        regimes_dict = a.get('regimes', {})
        regime = regimes_dict.get('current_regime', -1)
        regime_name = {0: "Bear", 1: "Neutral", 2: "Bull"}.get(regime, "No Data")
        if regimes_dict.get('error'):
            regime_name = "No Data"
        risk = a['risk']
        dd = a['drawdowns']
        kyle = a.get('kyle_lambda', 0)
        amihud = a.get('amihud', 0)
        cvd = a.get('cvd', 0)
        sci_panels += f'''<div class="sci-panel">
            <div class="sci-title">{sym} <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Scientific</span></div>
            <div class="sci-grid">
                <div class="sci-group">
                    <div class="sci-group-title">Stationarity & Memory</div>
                    <div class="sci-row"><span class="sci-key">ADF Price</span><span class="sci-val">p={adf.get('p_value', 1):.4f}</span></div>
                    <div class="sci-row"><span class="sci-key">ADF Returns</span><span class="sci-val">p={adf_ret.get('p_value', 1):.4f}</span></div>
                    <div class="sci-row"><span class="sci-key">Hurst</span><span class="sci-val {hurst_class}">{hurst:.3f}</span></div>
                    <div class="sci-row"><span class="sci-key">Half-Life</span><span class="sci-val {hl_class}">{hl_text}</span></div>
                </div>
                <div class="sci-group">
                    <div class="sci-group-title">Regime & Risk</div>
                    <div class="sci-row"><span class="sci-key">Regime</span><span class="sci-val">{regime_name}</span></div>
                    <div class="sci-row"><span class="sci-key">VaR 95%</span><span class="sci-val">{risk.get('var_historical', 0)*100:.2f}%</span></div>
                    <div class="sci-row"><span class="sci-key">CVaR 95%</span><span class="sci-val">{risk.get('cvar_historical', 0)*100:.2f}%</span></div>
                    <div class="sci-row"><span class="sci-key">Max DD</span><span class="sci-val">{dd.get('max_drawdown', 0)*100:.2f}%</span></div>
                </div>
                <div class="sci-group">
                    <div class="sci-group-title">Microstructure</div>
                    <div class="sci-row"><span class="sci-key">Kyle's λ</span><span class="sci-val">{kyle:.2e}</span></div>
                    <div class="sci-row"><span class="sci-key">Amihud</span><span class="sci-val">{amihud:.2e}</span></div>
                    <div class="sci-row"><span class="sci-key">CVD</span><span class="sci-val {('bull' if cvd > 0 else 'bear')}">{cvd:+.2f}</span></div>
                    <div class="sci-row"><span class="sci-key">Breakpoints</span><span class="sci-val">{len(a.get('breakpoints', []))} detected</span></div>
                </div>
            </div>
        </div>'''

    chart_data_json = json.dumps({k: v['chart_data'] for k, v in analysis['analyses'].items()})
    volume_profile_json = json.dumps({k: v['volume_profile'] for k, v in analysis['analyses'].items()})
    fg_json = json.dumps(fg)

    sidebar_items = ""
    for sym in symbols:
        a = analyses[sym]
        sidebar_items += f'<div class="nav-item"><span>{sym}</span><span class="nav-trend {class_for_value(a["price_change_pct"])}">{a["price_change_pct"]:+.2f}%</span></div>'
    fg_sidebar_value = fg.get('current', 'N/A') if fg else 'N/A'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="{UPDATE_INTERVAL_MS//1000}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Flow Terminal | Scientific Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: {COLORS['bg']};
            --surface: {COLORS['surface']};
            --surface-2: {COLORS['surface2']};
            --border: {COLORS['border']};
            --text: {COLORS['text']};
            --text-dim: {COLORS['text_dim']};
            --bull: {COLORS['bull']};
            --bear: {COLORS['bear']};
            --warn: {COLORS['warn']};
            --info: {COLORS['info']};
            --purple: {COLORS['purple']};
            --cyan: {COLORS['cyan']};
            --orange: {COLORS['orange']};
            --grid: {COLORS['grid']};
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
            --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.18);
            --shadow-hover: 0 4px 16px rgba(0, 0, 0, 0.24);
            --mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', Consolas, monospace;
            --sans: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--sans);
            background: var(--bg);
            color: var(--text);
            font-size: 14px;
            line-height: 1.5;
            min-height: 100vh;
            overflow-x: hidden;
        }}
        .app {{
            display: grid;
            grid-template-columns: 260px 1fr;
            min-height: 100vh;
        }}
        .sidebar {{
            background: #161c25;
            border-right: 1px solid var(--border);
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            gap: 24px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 18px;
            font-weight: 700;
            color: #e8eaed;
        }}
        .brand-dot {{
            width: 10px; height: 10px; background: var(--bull); border-radius: 50%;
            box-shadow: 0 0 8px var(--bull);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
        @media (prefers-reduced-motion: reduce) {{ .brand-dot {{ animation: none; }} }}
        .nav-section {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .nav-title {{
            font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
            color: var(--text-dim); font-weight: 600;
        }}
        .nav-item {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 12px; border-radius: var(--radius-md);
            color: #b5bdca; font-size: 13px; font-weight: 500;
            cursor: pointer; transition: all 0.15s ease;
        }}
        .nav-item:hover, .nav-item.active {{
            background: #242b3a; color: #e8eaed;
            border-left: 3px solid var(--info);
        }}
        .nav-item .nav-trend {{
            font-family: var(--mono); font-size: 11px;
        }}
        .main {{
            display: flex;
            flex-direction: column;
        }}
        .topbar {{
            height: 70px;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            position: sticky;
            top: 0;
            z-index: 50;
            box-shadow: var(--shadow-card);
        }}
        .topbar-left {{ display: flex; align-items: center; gap: 16px; }}
        .topbar-title {{ font-size: 18px; font-weight: 700; color: #e8eaed; }}
        .topbar-sub {{ font-size: 12px; color: var(--text-dim); margin-top: 2px; }}
        .topbar-right {{ display: flex; align-items: center; gap: 20px; }}
        .status-pill {{
            display: flex; align-items: center; gap: 8px;
            padding: 6px 12px; background: #242b3a;
            border-radius: 20px; font-size: 12px; color: #b5bdca;
            border: 1px solid var(--border);
        }}
        .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--bull); }}
        .timestamp {{ font-family: var(--mono); font-size: 12px; color: var(--text-dim); }}
        .content {{
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px;
            box-shadow: var(--shadow-card);
            transition: box-shadow 0.15s ease, transform 0.15s ease;
        }}
        .kpi-card:hover {{ box-shadow: var(--shadow-hover); transform: translateY(-1px); }}
        .kpi-header {{
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 10px;
        }}
        .kpi-symbol {{ font-size: 13px; font-weight: 600; color: #e8eaed; }}
        .kpi-price {{
            font-family: var(--mono); font-size: 24px; font-weight: 600;
            color: #e8eaed; margin-bottom: 4px;
        }}
        .kpi-change {{ font-family: var(--mono); font-size: 13px; font-weight: 600; }}
        .kpi-grid {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 10px; margin-top: 14px;
            padding-top: 14px; border-top: 1px solid var(--border);
        }}
        .kpi-item {{ display: flex; flex-direction: column; gap: 2px; }}
        .kpi-label {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; }}
        .kpi-val {{ font-family: var(--mono); font-size: 13px; font-weight: 500; }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-card);
            overflow: hidden;
        }}
        .card-header {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .card-title {{
            font-size: 14px; font-weight: 600; color: #e8eaed;
            display: flex; align-items: center; gap: 8px;
        }}
        .card-body {{ padding: 18px; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
            grid-auto-flow: row dense;
        }}
        .grid-2 {{ grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); }}
        .card.full {{ grid-column: 1 / -1; }}
        .card.two-third {{ grid-column: span 2; }}
        .badge {{
            display: inline-flex; align-items: center;
            padding: 2px 8px; border-radius: var(--radius-sm);
            font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
            color: var(--bdg-color); background: var(--bdg-bg);
            border: 1px solid var(--bdg-color);
        }}
        .data-table {{
            width: 100%; border-collapse: collapse; font-size: 13px;
        }}
        .data-table th {{
            text-align: left; padding: 10px 12px;
            color: var(--text-dim); font-weight: 600;
            text-transform: uppercase; font-size: 11px; letter-spacing: 0.04em;
            border-bottom: 1px solid var(--border);
            background: var(--surface);
        }}
        .data-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}
        .data-table tr:hover td {{ background: #242b3a; }}
        .data-table .num {{ text-align: right; }}
        .data-table .sym {{ font-weight: 600; color: #e8eaed; }}
        .data-table .mono {{ font-family: var(--mono); }}
        .data-table tr.near td {{ background: rgba(255, 152, 0, 0.08); }}
        .chart {{ width: 100%; height: 260px; }}
        .chart.large {{ height: 340px; }}
        .chart.small {{ height: 140px; }}
        .stat-grid {{
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
            margin-bottom: 14px;
        }}
        .stat-box {{
            background: #242b3a; border-radius: var(--radius-md);
            padding: 12px; display: flex; flex-direction: column; gap: 4px;
        }}
        .stat-label {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; }}
        .stat-value {{ font-family: var(--mono); font-size: 18px; font-weight: 600; color: #e8eaed; }}
        .liq-bar {{
            display: flex; height: 28px; border-radius: var(--radius-sm); overflow: hidden;
            background: #242b3a; border: 1px solid var(--border);
        }}
        .liq-long {{ background: var(--bear); transition: width 0.3s ease; }}
        .liq-short {{ background: var(--bull); transition: width 0.3s ease; }}
        .liq-legend {{
            font-size: 11px; color: var(--text-dim); margin-top: 8px;
            text-align: right; font-family: var(--mono);
        }}
        .fg-gauge {{ text-align: center; padding: 8px 0 16px; }}
        .fg-value {{ font-size: 42px; font-weight: 700; font-family: var(--mono); color: var(--fg-color); }}
        .fg-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }}
        .sci-panels {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 16px;
        }}
        .sci-panel {{
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px;
        }}
        .sci-title {{
            font-size: 14px; font-weight: 600; color: #e8eaed;
            margin-bottom: 14px; display: flex; align-items: center; gap: 10px;
        }}
        .sci-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 16px;
        }}
        .sci-group {{ display: flex; flex-direction: column; gap: 8px; }}
        .sci-group-title {{
            font-size: 11px; color: var(--info); text-transform: uppercase;
            letter-spacing: 0.04em; font-weight: 600; margin-bottom: 4px;
        }}
        .sci-row {{
            display: flex; justify-content: space-between; align-items: center;
            font-size: 12px;
        }}
        .sci-key {{ color: var(--text-dim); }}
        .sci-val {{ font-family: var(--mono); font-weight: 500; color: #e8eaed; }}
        .sci-val.ok {{ color: var(--bull); }}
        .sci-val.warn {{ color: var(--warn); }}
        .sci-val.bad {{ color: var(--bear); }}
        .bull, .pos {{ color: var(--bull); }}
        .bear, .neg {{ color: var(--bear); }}
        .warn {{ color: var(--warn); }}
        .info {{ color: var(--info); }}
        .neutral {{ color: var(--text-dim); }}
        .overbought {{ color: var(--bear); }}
        .oversold {{ color: var(--bull); }}
        .empty-state {{
            text-align: center; padding: 32px; color: var(--text-dim);
            font-style: italic; font-size: 13px;
        }}
        @media (max-width: 1200px) {{
            .app {{ grid-template-columns: 1fr; }}
            .sidebar {{ display: none; }}
            .grid, .grid-2 {{ grid-template-columns: 1fr; }}
            .card.two-third {{ grid-column: 1 / -1; }}
            .kpi-row {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
        }}
        @media (min-width: 1800px) {{
            .grid {{ grid-template-columns: repeat(3, 1fr); }}
            .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
            .card.two-third {{ grid-column: span 2; }}
        }}
    </style>
</head>
<body>
    <div class="app">
        <aside class="sidebar">
            <div class="brand">
                <span class="brand-dot"></span>
                <span>Order Flow</span>
            </div>
            <div class="nav-section">
                <div class="nav-title">Mercado</div>
                {sidebar_items}
            </div>
            <div class="nav-section">
                <div class="nav-title">Sentimento</div>
                <div class="nav-item">
                    <span>Fear & Greed</span>
                    <span class="nav-trend" style="color: {fg_color}">{fg_sidebar_value}</span>
                </div>
            </div>
        </aside>
        <main class="main">
            <header class="topbar">
                <div class="topbar-left">
                    <div>
                        <div class="topbar-title">Order Flow Terminal</div>
                        <div class="topbar-sub">Microestrutura de mercado em tempo real</div>
                    </div>
                </div>
                <div class="topbar-right">
                    <div class="status-pill">
                        <span class="status-dot" id="ws-status"></span>
                        <span id="ws-state">Connecting...</span>
                    </div>
                    <div class="timestamp" id="timestamp"></div>
                    <div class="status-pill">Symbols: {len(symbols)}</div>
                </div>
            </header>

            <div class="content">
                <div class="kpi-row">
                    {kpi_cards}
                </div>

                <div class="card full">
                    <div class="card-header">
                        <div class="card-title">Market Summary <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Real-time</span></div>
                    </div>
                    <div class="card-body" style="padding: 0; overflow-x: auto;">
                        <table class="data-table">
                            <thead><tr>
                                <th>Symbol</th>
                                <th class="num">Price</th>
                                <th class="num">24h Chg</th>
                                <th class="num">OB Imb</th>
                                <th class="num">CVD</th>
                                <th class="num">RSI</th>
                                <th>Signal</th>
                                <th>Trend</th>
                                <th>Regime</th>
                            </tr></thead>
                            <tbody>{summary_rows}</tbody>
                        </table>
                    </div>
                </div>

                <div class="grid grid-2">
                    <div class="card two-third">
                        <div class="card-header">
                            <div class="card-title">Price + Bollinger Bands + VWAP</div>
                        </div>
                        <div class="card-body">
                            <div id="chart-price" class="chart large"></div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Fear & Greed Index</div>
                        </div>
                        <div class="card-body">
                            {fg_html}
                        </div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Order Book Imbalance <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">5-level depth</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-imbalance" class="chart large"></div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Trade Flow: Aggressive Buy vs Sell <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">15s buckets</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-cvd" class="chart large"></div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Volume Profile <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">POC/VAH/VAL</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-vp" class="chart"></div>
                        </div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">RSI (14) <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Momentum</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-rsi" class="chart"></div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">MACD <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">12/26/9</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-macd" class="chart"></div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">SuperTrend + ATR <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Trend/Volatility</span></div>
                        </div>
                        <div class="card-body">
                            <div id="chart-st" class="chart"></div>
                        </div>
                    </div>
                </div>

                <div class="grid grid-2">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Funding & Positioning</div>
                        </div>
                        <div class="card-body" style="padding: 0; overflow-x: auto;">
                            <table class="data-table">
                                <thead><tr>
                                    <th>Symbol</th>
                                    <th class="num">Funding</th>
                                    <th class="num">L/S Ratio</th>
                                    <th class="num">Long%</th>
                                    <th class="num">Open Interest</th>
                                    <th class="num">OI 24h Chg</th>
                                </tr></thead>
                                <tbody>{pos_rows}</tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Liquidations 24h <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Xoomar</span></div>
                        </div>
                        <div class="card-body">
                            {liq_html}
                        </div>
                    </div>
                </div>

                <div class="grid grid-2">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Fibonacci Retracement <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">50 bars</span></div>
                        </div>
                        <div class="card-body" style="padding: 0; overflow-x: auto;">
                            <table class="data-table">
                                <thead><tr>
                                    <th>Symbol</th>
                                    <th class="num">Level</th>
                                    <th class="num">Price</th>
                                    <th class="num">Distance</th>
                                </tr></thead>
                                <tbody>{fib_rows}</tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">Correlation Matrix</div>
                        </div>
                        <div class="card-body" style="padding: 0; overflow-x: auto;">
                            {corr_html if corr_html else '<div class="empty-state">Insufficient data</div>'}
                        </div>
                    </div>
                </div>

                <div class="card full">
                    <div class="card-header">
                        <div class="card-title">Scientific Analysis <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Per Symbol</span></div>
                    </div>
                    <div class="card-body">
                        <div class="sci-panels">
                            {sci_panels}
                        </div>
                    </div>
                </div>

                <div class="card full">
                    <div class="card-header">
                        <div class="card-title">Cross-Sectional Analysis <span class="badge" style="--bdg-color: {COLORS['info']};--bdg-bg: {COLORS['info']}22;">Correlation / PCA</span></div>
                    </div>
                    <div class="card-body">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                            <div>
                                <h3 style="font-size:12px;color:var(--text-dim);margin-bottom:12px;text-transform:uppercase;letter-spacing:0.04em;">Correlation Matrix</h3>
                                {corr_html if corr_html else '<div class="empty-state">Insufficient data</div>'}
                            </div>
                            <div>
                                <h3 style="font-size:12px;color:var(--text-dim);margin-bottom:12px;text-transform:uppercase;letter-spacing:0.04em;">PCA Factors</h3>
                                {pca_html if pca_html else '<div class="empty-state">Insufficient data</div>'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        const symbols = {json.dumps(symbols)};
        const analyses = {chart_data_json};
        const fgData = {fg_json};
        const vpData = {volume_profile_json};
        const palette = {json.dumps(SYM_COLORS)};
        const COLOR_BULL = '{COLORS['bull']}';
        const COLOR_BEAR = '{COLORS['bear']}';
        const COLOR_WARN = '{COLORS['warn']}';
        const COLOR_INFO = '{COLORS['info']}';
        const COLOR_DIM = '{COLORS['text_dim']}';

        document.getElementById('timestamp').textContent =
            new Date().toLocaleString('pt-BR', {{hour12:false, timeZone:'UTC'}}) + ' UTC';

        const charts = {{}};
        function initChart(id) {{
            const el = document.getElementById(id);
            if (!el) return null;
            const chart = echarts.init(el);
            charts[id] = chart;
            return chart;
        }}

        const commonGrid = {{ left: 50, right: 15, bottom: 25, top: 35 }};
        const commonXAxis = {{
            type: 'category',
            axisLabel: {{ fontSize: 10, color: COLOR_DIM }},
            axisLine: {{ lineStyle: {{ color: '#2f3848' }} }},
        }};
        const commonYAxis = {{
            type: 'value',
            axisLabel: {{ color: COLOR_DIM, fontSize: 10 }},
            splitLine: {{ lineStyle: {{ color: '#2f3848' }} }},
        }};

        const imbChart = initChart('chart-imbalance');
        if (imbChart) {{
            const imbSeries = symbols.map((sym, i) => {{
                const d = analyses[sym];
                if (!d) return null;
                return {{
                    name: sym, type: 'line', data: d.imbalance_series || [],
                    showSymbol: false, smooth: true,
                    lineStyle: {{ width: 1.5, color: palette[i % palette.length] }},
                    itemStyle: {{ color: palette[i % palette.length] }},
                }};
            }}).filter(s => s);
            const imbX = symbols.length > 0 && analyses[symbols[0]] ? analyses[symbols[0]].timestamps : [];
            imbChart.setOption({{
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
                legend: {{ data: symbols, top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 11 }} }},
                xAxis: {{ ...commonXAxis, data: imbX }},
                yAxis: {{ type: 'value', min: -1, max: 1, name: 'Imb', nameTextStyle: {{ color: COLOR_DIM }}, axisLabel: {{ color: COLOR_DIM, fontSize: 10 }}, splitLine: {{ lineStyle: {{ color: '#2f3848' }} }} }},
                series: imbSeries,
                grid: commonGrid,
            }});
        }}

        const cvdChart = initChart('chart-cvd');
        if (cvdChart) {{
            const cvdSeries = [];
            const cvdX = [];
            symbols.forEach((sym, i) => {{
                const d = analyses[sym];
                if (!d) return;
                if (cvdX.length === 0) cvdX.push(...d.timestamps);
                cvdSeries.push({{
                    name: sym + ' Buy', type: 'bar', stack: sym + 'buy',
                    data: d.buy_vol_series || [],
                    itemStyle: {{ color: palette[i % palette.length], opacity: 0.7 }},
                }});
                cvdSeries.push({{
                    name: sym + ' Sell', type: 'bar', stack: sym + 'sell',
                    data: (d.sell_vol_series || []).map(x => -x),
                    itemStyle: {{ color: COLOR_BEAR, opacity: 0.5 }},
                }});
            }});
            cvdChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 10 }}, data: cvdSeries.map(s => s.name) }},
                xAxis: {{ ...commonXAxis, data: cvdX }},
                yAxis: commonYAxis,
                series: cvdSeries,
                grid: commonGrid,
            }});
        }}

        const priceChart = initChart('chart-price');
        if (priceChart) {{
            const priceSeries = [];
            const priceX = symbols.length > 0 && analyses[symbols[0]] ? analyses[symbols[0]].timestamps : [];
            symbols.forEach((sym, i) => {{
                const d = analyses[sym];
                if (!d) return;
                const color = palette[i % palette.length];
                priceSeries.push({{
                    name: sym, type: 'line', data: d.close_series || [],
                    showSymbol: false, smooth: true,
                    lineStyle: {{ width: 2, color: color }},
                }});
                if (i === 0) {{
                    priceSeries.push({{
                        name: sym + ' BB Upper', type: 'line', data: d.bb_upper_series || [],
                        showSymbol: false, lineStyle: {{ width: 1, type: 'dashed', color: COLOR_DIM, opacity: 0.5 }},
                    }});
                    priceSeries.push({{
                        name: sym + ' BB Lower', type: 'line', data: d.bb_lower_series || [],
                        showSymbol: false, lineStyle: {{ width: 1, type: 'dashed', color: COLOR_DIM, opacity: 0.5 }},
                        areaStyle: {{ color: 'rgba(120,123,134,0.05)', origin: 'start' }},
                    }});
                    priceSeries.push({{
                        name: sym + ' VWAP', type: 'line', data: d.vwap_series || [],
                        showSymbol: false, lineStyle: {{ width: 1.5, type: 'dotted', color: COLOR_WARN }},
                    }});
                }}
            }});
            priceChart.setOption({{
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
                legend: {{ top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 10 }}, data: priceSeries.map(s => s.name) }},
                xAxis: {{ ...commonXAxis, data: priceX }},
                yAxis: {{ type: 'value', scale: true, axisLabel: {{ color: COLOR_DIM, fontSize: 10 }}, splitLine: {{ lineStyle: {{ color: '#2f3848' }} }} }},
                series: priceSeries,
                grid: {{ left: 60, right: 15, bottom: 25, top: 35 }},
            }});
        }}

        const rsiChart = initChart('chart-rsi');
        if (rsiChart) {{
            const rsiSeries = symbols.map((sym, i) => {{
                const d = analyses[sym];
                if (!d) return null;
                return {{
                    name: sym, type: 'line', data: d.rsi_series || [],
                    showSymbol: false, smooth: true,
                    lineStyle: {{ width: 1.5, color: palette[i % palette.length] }},
                }};
            }}).filter(s => s);
            const rsiX = symbols.length > 0 && analyses[symbols[0]] ? analyses[symbols[0]].timestamps : [];
            rsiChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 10 }} }},
                xAxis: {{ ...commonXAxis, data: rsiX }},
                yAxis: {{ type: 'value', min: 0, max: 100, axisLabel: {{ color: COLOR_DIM, fontSize: 10 }}, splitLine: {{ lineStyle: {{ color: '#2f3848' }} }} }},
                series: rsiSeries,
                markLine: {{ data: [
                    {{ yAxis: 70, lineStyle: {{ color: COLOR_BEAR, type: 'dashed' }}, label: {{ formatter: 'Overbought' }} }},
                    {{ yAxis: 30, lineStyle: {{ color: COLOR_BULL, type: 'dashed' }}, label: {{ formatter: 'Oversold' }} }},
                ]}},
                grid: {{ left: 40, right: 15, bottom: 25, top: 30 }},
            }});
        }}

        const macdChart = initChart('chart-macd');
        if (macdChart) {{
            const macdSeries = [];
            symbols.forEach((sym, i) => {{
                const d = analyses[sym];
                if (!d) return;
                const color = palette[i % palette.length];
                macdSeries.push({{ name: sym + ' MACD', type: 'line', data: d.macd_series || [], showSymbol: false, lineStyle: {{ width: 1.5, color: color }} }});
                macdSeries.push({{ name: sym + ' Signal', type: 'line', data: d.macd_sig_series || [], showSymbol: false, lineStyle: {{ width: 1, color: COLOR_WARN }} }});
            }});
            const macdX = symbols.length > 0 && analyses[symbols[0]] ? analyses[symbols[0]].timestamps : [];
            macdChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 10 }} }},
                xAxis: {{ ...commonXAxis, data: macdX }},
                yAxis: commonYAxis,
                series: macdSeries,
                grid: {{ left: 50, right: 15, bottom: 25, top: 30 }},
            }});
        }}

        const stChart = initChart('chart-st');
        if (stChart) {{
            const stSeries = symbols.map((sym, i) => {{
                const d = analyses[sym];
                if (!d) return null;
                const color = palette[i % palette.length];
                return [
                    {{ name: sym + ' Price', type: 'line', data: d.close_series || [], showSymbol: false, smooth: true, lineStyle: {{ width: 1.5, color: color }} }},
                    {{ name: sym + ' ST', type: 'line', data: d.supertrend_series || [], showSymbol: false, lineStyle: {{ width: 2, color: color }} }},
                ];
            }}).flat().filter(s => s);
            const stX = symbols.length > 0 && analyses[symbols[0]] ? analyses[symbols[0]].timestamps : [];
            stChart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ top: 0, textStyle: {{ color: COLOR_DIM, fontSize: 10 }} }},
                xAxis: {{ ...commonXAxis, data: stX }},
                yAxis: {{ type: 'value', scale: true, axisLabel: {{ color: COLOR_DIM, fontSize: 10 }}, splitLine: {{ lineStyle: {{ color: '#2f3848' }} }} }},
                series: stSeries,
                grid: {{ left: 60, right: 15, bottom: 25, top: 30 }},
            }});
        }}

        const vpChart = initChart('chart-vp');
        if (vpChart && symbols.length > 0) {{
            let vpSym = null;
            for (const sym of symbols) {{
                const a = vpData[sym];
                if (a && a.bins && a.bins.length > 0) {{ vpSym = sym; break; }}
            }}
            if (vpSym) {{
                const a = vpData[vpSym];
                const bins = a.bins;
                const vols = a.volumes;
                const pocIdx = a.poc_idx;
                const vahIdx = a.vah_idx;
                const valIdx = a.val_idx;
                const priceLabels = bins.map((b, i) => b.toFixed(2));
                vpChart.setOption({{
                    tooltip: {{ trigger: 'axis', formatter: function(params) {{ return params[0].name + '<br/>Vol: ' + params[0].value.toFixed(2); }} }},
                    yAxis: {{ type: 'value', axisLabel: {{ color: COLOR_DIM, fontSize: 10 }}, splitLine: {{ show: false }} }},
                    xAxis: {{ type: 'category', data: priceLabels, axisLabel: {{ show: false, fontSize: 9 }}, splitLine: {{ show: false }} }},
                    series: [{{
                        type: 'bar', data: vols,
                        itemStyle: {{ color: COLOR_INFO }},
                        barWidth: '80%',
                    }}],
                    markLine: {{
                        symbol: ['none', 'none'],
                        data: [
                            {{ xAxis: pocIdx, lineStyle: {{ color: COLOR_WARN, type: 'dashed' }}, label: {{ formatter: 'POC', position: 'insideEndTop' }} }},
                            {{ xAxis: vahIdx, lineStyle: {{ color: COLOR_BULL, type: 'dashed' }}, label: {{ formatter: 'VAH', position: 'insideEndTop' }} }},
                            {{ xAxis: valIdx, lineStyle: {{ color: COLOR_BEAR, type: 'dashed' }}, label: {{ formatter: 'VAL', position: 'insideEndTop' }} }},
                        ]
                    }},
                    grid: {{ left: 60, right: 10, bottom: 20, top: 10 }},
                }});
            }}
        }}

        if (fgData && fgData.history_values && fgData.history_values.length > 0) {{
            const fgChart = initChart('chart-fg');
            if (fgChart) {{
                fgChart.setOption({{
                    tooltip: {{ trigger: 'axis' }},
                    xAxis: {{ type: 'category', data: fgData.history_dates, axisLabel: {{ fontSize: 9, color: COLOR_DIM, rotate: 30 }} }},
                    yAxis: {{ type: 'value', min: 0, max: 100, show: false }},
                    series: [{{
                        type: 'line', data: fgData.history_values,
                        showSymbol: true, symbolSize: 4,
                        lineStyle: {{ width: 2, color: COLOR_INFO }},
                        itemStyle: {{ color: COLOR_INFO }},
                        areaStyle: {{ color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(66,165,245,0.3)' }},
                            {{ offset: 1, color: 'rgba(66,165,245,0)' }},
                        ]) }},
                    }}],
                    grid: {{ left: 10, right: 10, bottom: 20, top: 10 }},
                }});
            }}
        }}

        let ws = null;
        let wsReconnectAttempts = 0;
        const MAX_RECONNECT = 10;
        const WS_BATCH_MS = {WS_BATCH_MS};
        let wsBuffer = new Map();
        let wsBatchTimer = null;

        function connectWS() {{
            if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
            const streams = symbols.map(s => s.toLowerCase() + '@depth5@100ms/' + s.toLowerCase() + '@aggTrade').join('/');
            ws = new WebSocket('wss://stream.binance.com:9443/stream?streams=' + streams);
            ws.onopen = () => {{
                wsReconnectAttempts = 0;
                document.getElementById('ws-state').textContent = 'Live';
                document.getElementById('ws-status').style.background = COLOR_BULL;
            }};
            ws.onmessage = (event) => {{
                const msg = JSON.parse(event.data);
                if (msg.stream && msg.data) {{
                    const stream = msg.stream;
                    const data = msg.data;
                    if (!wsBuffer.has(stream)) wsBuffer.set(stream, []);
                    wsBuffer.get(stream).push(data);
                    if (!wsBatchTimer) {{
                        wsBatchTimer = setTimeout(processWSBatch, WS_BATCH_MS);
                    }}
                }}
            }};
            ws.onclose = () => {{
                document.getElementById('ws-state').textContent = 'Reconnecting...';
                document.getElementById('ws-status').style.background = COLOR_WARN;
                if (wsReconnectAttempts < MAX_RECONNECT) {{
                    wsReconnectAttempts++;
                    setTimeout(connectWS, 1000 * wsReconnectAttempts);
                }} else {{
                    document.getElementById('ws-state').textContent = 'Failed';
                    document.getElementById('ws-status').style.background = COLOR_BEAR;
                }}
            }};
            ws.onerror = (err) => {{ console.error('WS Error:', err); }};
        }}

        function processWSBatch() {{
            wsBatchTimer = null;
            wsBuffer.forEach((updates, stream) => {{
                if (updates.length === 0) return;
                const latest = updates[updates.length - 1];
                const streamParts = stream.split('@');
                const symbol = streamParts[0].toUpperCase();
                if (streamParts[1].startsWith('depth5')) updateOrderBook(symbol, latest);
            }});
            wsBuffer.clear();
        }}

        function updateOrderBook(symbol, data) {{
            const chart = charts['chart-imbalance'];
            if (!chart) return;
            const bids = data.bids || [];
            const asks = data.asks || [];
            let bidQty = 0, askQty = 0;
            for (let i = 0; i < Math.min(5, bids.length); i++) bidQty += parseFloat(bids[i][1]);
            for (let i = 0; i < Math.min(5, asks.length); i++) askQty += parseFloat(asks[i][1]);
            const imbalance = (bidQty - askQty) / (bidQty + askQty) || 0;
            const now = new Date().toLocaleTimeString('pt-BR', {{hour12:false}});
            const option = chart.getOption();
            if (option && option.series) {{
                const seriesIdx = symbols.indexOf(symbol);
                if (seriesIdx >= 0 && option.series[seriesIdx]) {{
                    const xData = option.xAxis[0].data || [];
                    const newX = xData.concat([now]);
                    const seriesData = option.series[seriesIdx].data || [];
                    const newData = seriesData.concat([imbalance]);
                    const MAX_POINTS = 150;
                    if (newX.length > MAX_POINTS) {{ newX.shift(); newData.shift(); }}
                    const update = {{ xAxis: {{ data: newX }} }};
                    update.series = option.series.map((s, i) => i === seriesIdx ? {{ data: newData }} : {{ data: s.data }});
                    chart.setOption(update, false, false);
                }}
            }}
        }}

        connectWS();

        window.addEventListener('resize', () => {{
            document.querySelectorAll('[id^=chart-]').forEach(el => {{
                const inst = echarts.getInstanceByDom(el);
                if (inst) inst.resize();
            }});
        }});
    </script>
</body>
</html>"""



def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze live data and generate dashboard")
    parser.add_argument("--data-dir", type=str, default="data/live")
    parser.add_argument("--output", type=str, default="data/live/dashboard.html")
    parser.add_argument("--recent-hours", type=float, default=1.0,
                        help="Only load files from last N hours (0 = all, default: 1h)")
    args = parser.parse_args()

    print(f"Loading live data (last {args.recent_hours}h)...")
    data = load_live_data(args.data_dir, recent_hours=args.recent_hours)

    print("Analyzing...")
    analysis = analyze_all(data)

    print("Generating HTML...")
    html = generate_html(analysis)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
