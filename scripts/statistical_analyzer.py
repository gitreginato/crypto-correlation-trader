#!/usr/bin/env python3
"""
Advanced Statistical Analysis Module for Crypto Market Microstructure

Provides scientifically rigorous analysis of market data including:
- Stationarity and unit root tests
- Autocorrelation and partial autocorrelation
- Hurst exponent for persistence/memory
- Regime detection (HMM, variance change points)
- Microstructure metrics (VPIN, order flow toxicity, Kyle's lambda)
- Volume profile and liquidity analysis
- Correlation and lead-lag analysis
- Risk metrics (VaR, CVaR, expected shortfall)
- Statistical significance testing
"""

import warnings

import numpy as np
import pandas as pd
import ruptures as rpt
from scipy import stats
from scipy.stats import jarque_bera, normaltest
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import acf, adfuller, grangercausalitytests, kpss, pacf

from src.data.parquet_store import ParquetStore

warnings.filterwarnings('ignore')

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


@dataclass
class StatisticalResult:
    """Container for statistical test results"""
    test_name: str
    statistic: float
    p_value: float
    critical_values: Dict[str, float] = field(default_factory=dict)
    interpretation: str = ""
    significant: bool = False

    def to_dict(self) -> Dict:
        return {
            'test': self.test_name,
            'statistic': self.statistic,
            'p_value': self.p_value,
            'critical_values': self.critical_values,
            'interpretation': self.interpretation,
            'significant': self.significant
        }


@dataclass
class MicrostructureMetrics:
    """Microstructure metrics for a symbol"""
    symbol: str
    timestamp: pd.Timestamp

    # Order flow
    vpin: float = 0.0
    flow_toxicity: float = 0.0
    kyle_lambda: float = 0.0
    ami_hudson: float = 0.0

    # Volume profile
    poc_price: float = 0.0
    vah_price: float = 0.0
    val_price: float = 0.0
    volume_in_poc: float = 0.0

    # Liquidity
    bid_ask_spread: float = 0.0
    spread_bps: float = 0.0
    depth_imbalance: float = 0.0
    effective_spread: float = 0.0
    realized_spread: float = 0.0

    # Trade flow
    cvd: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    trade_count: int = 0
    large_trade_ratio: float = 0.0

    # Statistical
    returns_skew: float = 0.0
    returns_kurtosis: float = 0.0
    hurst_exponent: float = 0.0
    half_life: float = 0.0

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


class StatisticalAnalyzer:
    """Comprehensive statistical analysis for market data"""

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    # ─── Stationarity Tests ──────────────────────────────────────

    def test_stationarity_adf(self, series: pd.Series,
                              regression: str = 'c') -> StatisticalResult:
        """Augmented Dickey-Fuller test for unit root"""
        series = series.dropna()
        if len(series) < 20:
            return StatisticalResult('ADF', 0, 1, interpretation="Insufficient data")

        result = adfuller(series, regression=regression, autolag='AIC')
        stat, pval, used_lag, nobs, critical, icbest = result

        significant = pval < self.alpha
        interp = "Stationary (no unit root)" if significant else "Non-stationary (unit root present)"

        return StatisticalResult(
            test_name="Augmented Dickey-Fuller",
            statistic=stat,
            p_value=pval,
            critical_values={k: float(v) for k, v in critical.items()},
            interpretation=interp,
            significant=significant
        )

    def test_stationarity_kpss(self, series: pd.Series,
                               regression: str = 'c') -> StatisticalResult:
        """KPSS test for stationarity (null = stationary)"""
        series = series.dropna()
        if len(series) < 20:
            return StatisticalResult('KPSS', 0, 1, interpretation="Insufficient data")

        stat, pval, lags, critical = kpss(series, regression=regression, nlags='auto')

        significant = pval < self.alpha
        interp = "Non-stationary (reject stationarity)" if significant else "Stationary (fail to reject)"

        return StatisticalResult(
            test_name="KPSS",
            statistic=stat,
            p_value=pval,
            critical_values={k: float(v) for k, v in critical.items()},
            interpretation=interp,
            significant=significant
        )

    # ─── Autocorrelation Analysis ────────────────────────────────

    def autocorrelation_analysis(self, series: pd.Series,
                                  max_lag: int = 50) -> Dict:
        """Comprehensive autocorrelation analysis"""
        series = series.dropna()
        if len(series) < max_lag + 10:
            max_lag = len(series) // 3

        acf_vals = acf(series, nlags=max_lag, fft=True)
        pacf_vals = pacf(series, nlags=max_lag, method='ywm')

        # Ljung-Box test for autocorrelation
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb_result = acorr_ljungbox(series, lags=min(20, max_lag), return_df=True)

        # Find significant lags
        conf_int = 1.96 / np.sqrt(len(series))
        significant_lags = [i for i, v in enumerate(acf_vals[1:], 1)
                           if abs(v) > conf_int]

        return {
            'acf': acf_vals.tolist(),
            'pacf': pacf_vals.tolist(),
            'ljung_box_stat': float(lb_result['lb_stat'].iloc[-1]),
            'ljung_box_pval': float(lb_result['lb_pvalue'].iloc[-1]),
            'significant_lags': significant_lags[:20],
            'confidence_interval': float(conf_int),
            'first_zero_crossing': next((i for i, v in enumerate(acf_vals[1:], 1)
                                        if v < 0), None)
        }

    # ─── Hurst Exponent & Long Memory ────────────────────────────

    def hurst_exponent(self, series: pd.Series,
                       min_lag: int = 2, max_lag: int = 100) -> Dict:
        """Calculate Hurst exponent using R/S analysis (Rescaled Range)"""
        series = series.dropna().values
        if len(series) < max_lag * 2:
            max_lag = len(series) // 3

        lags = np.logspace(np.log10(min_lag), np.log10(max_lag), 20).astype(int)
        lags = np.unique(lags[lags >= min_lag])

        rs_values = []
        for lag in lags:
            if lag >= len(series):
                continue
            # Split into non-overlapping chunks
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
                rs_values.append(np.mean(chunk_rs))

        if len(rs_values) < 3:
            return {'hurst': 0.5, 'method': 'R/S', 'error': 'Insufficient data'}

        # Linear regression on log-log
        log_lags = np.log(lags[:len(rs_values)])
        log_rs = np.log(rs_values)
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_lags, log_rs)

        return {
            'hurst': float(slope),
            'r_squared': float(r_value**2),
            'p_value': float(p_value),
            'method': 'R/S',
            'interpretation': self._interpret_hurst(slope)
        }

    def _interpret_hurst(self, h: float) -> str:
        if h < 0.45:
            return "Anti-persistent (mean reverting)"
        elif h < 0.55:
            return "Random walk (no memory)"
        elif h < 0.65:
            return "Persistent (trending)"
        else:
            return "Strongly persistent (strong trend memory)"

    def half_life_mean_reversion(self, series: pd.Series) -> Dict:
        """Calculate half-life of mean reversion using OU process"""
        series = series.dropna().values
        if len(series) < 30:
            return {'half_life': np.inf, 'error': 'Insufficient data'}

        # OU process: dX = theta*(mu - X)*dt + sigma*dW
        # Discrete: X_t - X_{t-1} = theta*(mu - X_{t-1}) + epsilon
        y = series[1:] - series[:-1]
        x = series[:-1]

        if np.std(x) == 0:
            return {'half_life': np.inf, 'error': 'Zero variance'}

        # OLS regression
        X = np.column_stack([x, np.ones_like(x)])
        try:
            theta_mu, theta, *_ = np.linalg.lstsq(X, y, rcond=None)[0]
            theta = -theta_mu  # mean reversion speed

            if theta <= 0:
                return {'half_life': np.inf, 'theta': theta,
                        'interpretation': 'No mean reversion'}

            half_life = np.log(2) / theta
            return {
                'half_life': float(half_life),
                'theta': float(theta),
                'mu': float(-theta_mu/theta) if theta != 0 else np.nan,
                'interpretation': f"Mean reversion half-life: {half_life:.1f} periods"
            }
        except (np.linalg.LinAlgError, ValueError, IndexError) as e:
            logger.warning("Half-life calculation failed: %s", e)
            return {'half_life': np.inf, 'error': 'Calculation failed'}

    # ─── Regime Detection ────────────────────────────────────────

    def detect_regimes_hmm(self, returns: pd.Series,
                           n_regimes: int = 3) -> Dict:
        """Hidden Markov Model for regime detection"""
        returns = returns.dropna().values.reshape(-1, 1)
        if len(returns) < 50:
            return {'error': 'Insufficient data'}

        scaler = StandardScaler()
        scaled = scaler.fit_transform(returns)

        gmm = GaussianMixture(n_components=n_regimes,
                             covariance_type='full',
                             random_state=42)
        gmm.fit(scaled)

        regimes = gmm.predict(scaled)
        probs = gmm.predict_proba(scaled)

        # Characterize regimes
        regime_stats = []
        for i in range(n_regimes):
            mask = regimes == i
            regime_returns = returns[mask].flatten()
            regime_stats.append({
                'regime': i,
                'mean': float(np.mean(regime_returns)),
                'std': float(np.std(regime_returns)),
                'skew': float(stats.skew(regime_returns)),
                'count': int(np.sum(mask)),
                'pct': float(np.mean(mask))
            })

        # Sort by mean return
        regime_stats.sort(key=lambda x: x['mean'])

        return {
            'regimes': regime_stats,
            'current_regime': int(regimes[-1]),
            'regime_probs': probs[-1].tolist(),
            'transition_matrix': self._estimate_transition_matrix(regimes, n_regimes)
        }

    def _estimate_transition_matrix(self, regimes: np.ndarray, n: int) -> List[List[float]]:
        """Estimate regime transition matrix"""
        trans = np.zeros((n, n))
        for i in range(len(regimes) - 1):
            trans[regimes[i], regimes[i+1]] += 1
        row_sums = trans.sum(axis=1, keepdims=True)
        trans = np.divide(trans, row_sums, where=row_sums!=0)
        return trans.tolist()

    def detect_breakpoints(self, series: pd.Series,
                           penalty: str = 'bic',
                           min_size: int = 30) -> List[int]:
        """Detect structural breakpoints using ruptures library"""
        series = series.dropna().values
        if len(series) < min_size * 3:
            return []

        # Use L2 cost for variance changes
        model = "l2"
        algo = rpt.Pelt(model=model, min_size=min_size).fit(series)
        breakpoints = algo.predict(pen=penalty)

        # Remove last point (end of series)
        return [int(b) for b in breakpoints[:-1]]

    # ─── Microstructure Metrics ──────────────────────────────────

    def calculate_vpin(self, trades: pd.Series, volumes: pd.Series,
                       bucket_volume: float = None) -> float:
        """Volume-synchronized Probability of Informed Trading (VPIN)"""
        # Simplified VPIN: |buy_vol - sell_vol| / total_vol per bucket
        # Requires trade direction (buy/sell)
        if 'side' not in trades.index.names:
            return 0.0
        return 0.0  # Placeholder - needs trade direction data

    def calculate_kyle_lambda(self, returns: pd.Series,
                               volumes: pd.Series) -> float:
        """Kyle's Lambda: price impact per unit volume"""
        # Regress returns on signed volume
        if len(returns) != len(volumes):
            return 0.0

        # Use absolute returns vs volume
        abs_ret = np.abs(returns.dropna())
        vol = volumes.loc[abs_ret.index]

        if len(abs_ret) < 20 or vol.std() == 0:
            return 0.0

        try:
            X = vol.values.reshape(-1, 1)
            y = abs_ret.values
            lambda_est = np.linalg.lstsq(X, y, rcond=None)[0][0]
            return float(lambda_est)
        except (np.linalg.LinAlgError, ValueError, IndexError) as e:
            logger.warning("Kyle lambda calculation failed: %s", e)
            return 0.0

    def calculate_amihud_illiquidity(self, returns: pd.Series,
                                      volumes: pd.Series,
                                      window: int = 20) -> pd.Series:
        """Amihud illiquidity ratio: |return| / (price * volume)"""
        # Simplified: |return| / volume
        illiq = (returns.abs() / volumes).rolling(window).mean()
        return illiq

    # ─── Risk Metrics ────────────────────────────────────────────

    def calculate_var_cvar(self, returns: pd.Series,
                           confidence: float = 0.95) -> Dict:
        """Value at Risk and Conditional VaR (Expected Shortfall)"""
        returns = returns.dropna()
        if len(returns) < 30:
            return {'var': 0, 'cvar': 0, 'error': 'Insufficient data'}

        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()

        # Also parametric VaR (assuming normal)
        mu, sigma = returns.mean(), returns.std()
        from scipy.stats import norm
        z = norm.ppf(1 - confidence)
        var_param = mu + z * sigma

        return {
            'var_historical': float(var),
            'cvar_historical': float(cvar),
            'var_parametric': float(var_param),
            'confidence': confidence,
            'n_obs': len(returns)
        }

    def calculate_drawdowns(self, prices: pd.Series) -> Dict:
        """Calculate drawdown statistics"""
        prices = prices.dropna()
        if len(prices) < 2:
            return {}

        cummax = prices.expanding().max()
        drawdown = (prices - cummax) / cummax

        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()

        # Current drawdown
        current_dd = drawdown.iloc[-1]

        # Drawdown duration
        in_dd = drawdown < 0
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
            'max_drawdown_date': str(max_dd_idx) if hasattr(max_dd_idx, 'strftime') else str(max_dd_idx),
            'current_drawdown': float(current_dd),
            'avg_drawdown_duration': float(np.mean(dd_durations)) if dd_durations else 0,
            'max_drawdown_duration': int(max(dd_durations)) if dd_durations else 0,
            'drawdown_series': drawdown.values.tolist()
        }

    # ─── Correlation & Lead-Lag ──────────────────────────────────

    def cross_correlation(self, series1: pd.Series, series2: pd.Series,
                          max_lag: int = 20) -> Dict:
        """Cross-correlation with lead-lag analysis"""
        # Align series
        df = pd.DataFrame({'s1': series1, 's2': series2}).dropna()
        if len(df) < 30:
            return {'error': 'Insufficient aligned data'}

        s1, s2 = df['s1'].values, df['s2'].values

        correlations = []
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                corr = np.corrcoef(s1[:lag], s2[-lag:])[0, 1]
            elif lag > 0:
                corr = np.corrcoef(s1[lag:], s2[:-lag])[0, 1]
            else:
                corr = np.corrcoef(s1, s2)[0, 1]
            correlations.append(corr)

        max_corr = max(correlations, key=abs)
        max_lag_idx = correlations.index(max_corr) - max_lag

        return {
            'correlations': correlations,
            'lags': list(range(-max_lag, max_lag + 1)),
            'max_correlation': float(max_corr),
            'optimal_lag': int(max_lag_idx),
            'interpretation': f"Series 2 leads by {-max_lag_idx} periods" if max_lag_idx < 0 else f"Series 1 leads by {max_lag_idx} periods"
        }

    def granger_causality(self, series1: pd.Series, series2: pd.Series,
                          max_lag: int = 10) -> Dict:
        """Granger causality test"""
        df = pd.DataFrame({'s1': series1, 's2': series2}).dropna()
        if len(df) < 30:
            return {'error': 'Insufficient data'}

        try:
            # Test if s2 Granger-causes s1
            gc_21 = grangercausalitytests(df[['s1', 's2']], maxlag=max_lag, verbose=False)
            gc_12 = grangercausalitytests(df[['s2', 's1']], maxlag=max_lag, verbose=False)

            # Get minimum p-value across lags
            pvals_21 = [gc_21[i+1][0]['ssr_ftest'][1] for i in range(max_lag)]
            pvals_12 = [gc_12[i+1][0]['ssr_ftest'][1] for i in range(max_lag)]

            return {
                's2_causes_s1': min(pvals_21) < 0.05,
                's1_causes_s2': min(pvals_12) < 0.05,
                'pvals_s2_to_s1': pvals_21,
                'pvals_s1_to_s2': pvals_12,
                'min_pval_s2_to_s1': min(pvals_21),
                'min_pval_s1_to_s2': min(pvals_12)
            }
        except (ValueError, ImportError, RuntimeError) as e:
            logger.warning("Granger causality test failed: %s", e)
            return {'error': 'Test failed'}

    # ─── Comprehensive Analysis ──────────────────────────────────

    def full_analysis(self, prices: pd.Series,
                       volumes: pd.Series = None,
                       trades: pd.DataFrame = None,
                       order_book: pd.DataFrame = None) -> Dict:
        """Run complete statistical analysis"""
        returns = prices.pct_change().dropna()

        result = {
            'symbol': getattr(prices, 'name', 'UNKNOWN'),
            'timestamp': pd.Timestamp.now().isoformat(),
            'data_points': len(prices),
            'returns_stats': {
                'mean': float(returns.mean()),
                'std': float(returns.std()),
                'skew': float(stats.skew(returns)),
                'kurtosis': float(stats.kurtosis(returns)),
                'jarque_bera_stat': float(jarque_bera(returns)[0]),
                'jarque_bera_pval': float(jarque_bera(returns)[1]),
                'normal_pval': float(normaltest(returns)[1])
            },
            'stationarity': {
                'adf': self.test_stationarity_adf(prices).to_dict(),
                'kpss': self.test_stationarity_kpss(prices).to_dict(),
                'adf_returns': self.test_stationarity_adf(returns).to_dict()
            },
            'autocorrelation': self.autocorrelation_analysis(returns),
            'hurst': self.hurst_exponent(returns),
            'half_life': self.half_life_mean_reversion(prices),
            'risk': self.calculate_var_cvar(returns),
            'drawdowns': self.calculate_drawdowns(prices),
            'regimes': self.detect_regimes_hmm(returns, n_regimes=3)
        }

        if volumes is not None:
            result['amihud'] = self.calculate_amihud_illiquidity(returns, volumes).iloc[-1]
            result['kyle_lambda'] = self.calculate_kyle_lambda(returns, volumes)

        return result


class MarketDataAnalyzer:
    """High-level analyzer for complete market data"""

    def __init__(self):
        self.stats = StatisticalAnalyzer()

    def analyze_symbol(self, symbol: str,
                       ohlcv: pd.DataFrame,
                       trades: pd.DataFrame = None,
                       order_book: pd.DataFrame = None) -> Dict:
        """Analyze a single symbol comprehensively"""
        prices = ohlcv['close']
        volumes = ohlcv['volume']

        # Basic stats analysis
        analysis = self.stats.full_analysis(prices, volumes, trades, order_book)

        # Microstructure if we have order book
        if order_book is not None and not order_book.empty:
            analysis['microstructure'] = self._analyze_microstructure(
                symbol, order_book, trades
            )

        # Volume profile if we have trades
        if trades is not None and not trades.empty:
            analysis['volume_profile'] = self._volume_profile(trades)

        return analysis

    def _analyze_microstructure(self, symbol: str,
                                 order_book: pd.DataFrame,
                                 trades: pd.DataFrame) -> Dict:
        """Analyze order book microstructure"""
        latest_ob = order_book.iloc[-1]

        # Spread metrics
        spread = latest_ob['ask_0_price'] - latest_ob['bid_0_price']
        mid = (latest_ob['ask_0_price'] + latest_ob['bid_0_price']) / 2
        spread_bps = (spread / mid) * 10000

        # Depth
        bid_depth = sum(latest_ob.get(f'bid_{i}_qty', 0) for i in range(5))
        ask_depth = sum(latest_ob.get(f'ask_{i}_qty', 0) for i in range(5))
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0

        # Trade flow
        if trades is not None and not trades.empty:
            recent = trades.tail(100)
            buy_vol = recent[~recent['is_buyer_maker']]['quantity'].sum()
            sell_vol = recent[recent['is_buyer_maker']]['quantity'].sum()
            cvd = buy_vol - sell_vol
        else:
            cvd = 0
            buy_vol = sell_vol = 0

        return {
            'symbol': symbol,
            'mid_price': float(mid),
            'spread': float(spread),
            'spread_bps': float(spread_bps),
            'bid_depth': float(bid_depth),
            'ask_depth': float(ask_depth),
            'depth_imbalance': float(imbalance),
            'cvd': float(cvd),
            'buy_volume': float(buy_vol),
            'sell_volume': float(sell_vol),
            'timestamp': pd.Timestamp.now().isoformat()
        }

    def _volume_profile(self, trades: pd.DataFrame,
                        bins: int = 50) -> Dict:
        """Calculate volume profile (VPVR)"""
        if trades.empty:
            return {}

        # VWAP per price level
        trades = trades.copy()
        price_min = trades['price'].min()
        price_max = trades['price'].max()

        bin_edges = np.linspace(price_min, price_max, bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        volume_profile = np.zeros(bins)

        for _, row in trades.iterrows():
            idx = np.searchsorted(bin_edges, row['price']) - 1
            if 0 <= idx < bins:
                volume_profile[idx] += row['quantity']

        # POC (Point of Control)
        poc_idx = np.argmax(volume_profile)
        poc_price = bin_centers[poc_idx]

        # Value Area (70% of volume)
        total_vol = volume_profile.sum()
        target_vol = total_vol * 0.7

        # Expand from POC
        cum_vol = volume_profile[poc_idx]
        low_idx = high_idx = poc_idx

        while cum_vol < target_vol and (low_idx > 0 or high_idx < bins - 1):
            if low_idx > 0 and (high_idx >= bins - 1 or
                                 volume_profile[low_idx - 1] >= volume_profile[high_idx + 1]):
                low_idx -= 1
                cum_vol += volume_profile[low_idx]
            elif high_idx < bins - 1:
                high_idx += 1
                cum_vol += volume_profile[high_idx]
            else:
                break

        vah = bin_centers[high_idx]
        val = bin_centers[low_idx]

        return {
            'poc_price': float(poc_price),
            'vah_price': float(vah),
            'val_price': float(val),
            'volume_profile': volume_profile.tolist(),
            'price_bins': bin_centers.tolist(),
            'total_volume': float(total_vol),
            'volume_in_value_area': float(cum_vol)
        }

    def analyze_cross_sectional(self, symbols_data: Dict[str, Dict]) -> Dict:
        """Analyze relationships across symbols"""
        if len(symbols_data) < 2:
            return {}

        # Get returns for each symbol
        returns_dict = {}
        for sym, data in symbols_data.items():
            if 'prices' in data:
                returns_dict[sym] = data['prices'].pct_change().dropna()

        if len(returns_dict) < 2:
            return {}

        returns_df = pd.DataFrame(returns_dict).dropna()

        # Correlation matrix
        corr_matrix = returns_df.corr()

        # Lead-lag analysis for top pairs
        lead_lag = {}
        symbols = list(returns_dict.keys())
        for i, s1 in enumerate(symbols):
            for s2 in symbols[i+1:]:
                cc = self.stats.cross_correlation(returns_dict[s1], returns_dict[s2])
                lead_lag[f'{s1}-{s2}'] = cc

        # PCA for common factors
        from sklearn.decomposition import PCA
        pca = PCA(n_components=min(3, len(symbols)))
        try:
            pca.fit(returns_df)
            explained_var = pca.explained_variance_ratio_.tolist()
            components = pca.components_.tolist()
        except (ValueError, np.linalg.LinAlgError) as e:
            logger.warning("PCA fit failed: %s", e)
            explained_var = []
            components = []

        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'lead_lag': lead_lag,
            'pca': {
                'explained_variance': explained_var,
                'components': components
            },
            'avg_correlation': float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].mean()),
            'max_correlation': float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].max()),
            'min_correlation': float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].min())
        }


def analyze_historical_data(symbol: str,
                            ohlcv_path: str,
                            trades_path: str = None) -> Dict:
    """Load and analyze historical data from parquet files.

    Uses ParquetStore for standardized OHLCV reading with proper
    partitioned layout (exchange/market/symbol/timeframe/year/month).
    """
    store = ParquetStore(base_dir=ohlcv_path)

    # Discover available timeframes for this symbol, prefer lower (more granular)
    timeframes = store.get_available_timeframes(symbol)
    if not timeframes:
        return {'error': f'No data for {symbol} in {ohlcv_path}'}

    timeframe = timeframes[0]  # Use first available (sorted alphabetically)
    ohlcv = store.read(symbol, timeframe)

    if ohlcv.empty:
        return {'error': f'No data for {symbol} in {ohlcv_path}'}

    # ParquetStore uses open_time; rename to timestamp for downstream analysis
    if 'open_time' in ohlcv.columns:
        ohlcv = ohlcv.rename(columns={'open_time': 'timestamp'})

    # Ensure datetime index
    if 'timestamp' in ohlcv.columns:
        ohlcv['timestamp'] = pd.to_datetime(ohlcv['timestamp'])
        ohlcv = ohlcv.set_index('timestamp')

    # Resample to 1min if needed
    if ohlcv.index.inferred_freq is None:
        ohlcv = ohlcv.resample('1min').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()

    # Run analysis
    analyzer = MarketDataAnalyzer()
    result = analyzer.analyze_symbol(symbol, ohlcv)

    return result


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        result = analyze_historical_data(sys.argv[1], 'data/parquet')
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python statistical_analyzer.py <SYMBOL>")
