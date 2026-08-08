#!/usr/bin/env python3
"""
Scientific Report Generator for Crypto Market Analysis

Generates comprehensive markdown reports from market data analysis including:
- Statistical properties and stationarity tests
- Technical indicator summaries
- Microstructure metrics
- Regime detection results
- Risk metrics (VaR, CVaR, Drawdowns)
- Cross-sectional correlations
- Trading signals and interpretations

Designed for quantitative research, backtesting documentation, and strategy development.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.analyze_live import analyze_all, load_live_data


def format_pct(x: float) -> str:
    return f"{x*100:.2f}%"


def format_num(x: float, decimals: int = 4) -> str:
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.2f}K"
    return f"{x:.{decimals}f}"


def format_sci(x: float) -> str:
    if x == 0:
        return "0.00"
    return f"{x:.2e}"


def regime_name(regime: int) -> str:
    return {0: "Bear (Low Vol)", 1: "Neutral", 2: "Bull (High Vol)"}.get(regime, f"State {regime}")


def signal_interpretation(rsi: float, macd: float, macd_sig: float, bb_pos: float, st_trend: str) -> Dict[str, str]:
    signals = {}
    if rsi > 70:
        signals['RSI'] = "🔴 Sobrecomprado - Potencial venda"
    elif rsi < 30:
        signals['RSI'] = "🟢 Sobrevendido - Potencial compra"
    else:
        signals['RSI'] = "⚪ Neutro"

    signals['MACD'] = "🟢 Bullish (MACD > Signal)" if macd > macd_sig else "🔴 Bearish (MACD < Signal)"

    if bb_pos > 0.8:
        signals['BB'] = "🔴 Perto da banda superior - Sobrecomprado"
    elif bb_pos < 0.2:
        signals['BB'] = "🟢 Perto da banda inferior - Sobrevendido"
    else:
        signals['BB'] = "⚪ Dentro das bandas"

    signals['SuperTrend'] = "🟢 Tendência de alta" if st_trend == "UP" else "🔴 Tendência de baixa"
    return signals


def generate_scientific_report(analysis: Dict[str, Any]) -> str:
    """Generate comprehensive scientific analysis report in markdown."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    symbols = analysis['symbols']
    analyses = analysis['analyses']
    cs = analysis.get('cross_sectional', {})
    fg = analysis.get('fear_greed', {})
    liq = analysis.get('liquidations', {})

    report = f"""# Relatório Científico de Análise de Mercado Crypto
**Gerado em:** {timestamp}
**Símbolos analisados:** {', '.join(symbols)}
**Período:** Últimas 2 horas (dados em tempo real via Binance WebSocket + REST)

---

## Sumário Executivo

"""

    # Executive summary
    bullish_count = sum(1 for s in symbols if analyses[s]['supertrend_trend'] == 'UP')
    bearish_count = len(symbols) - bullish_count
    avg_rsi = np.mean([analyses[s]['rsi'] for s in symbols])
    avg_funding = np.mean([analyses[s]['funding_rate'] for s in symbols])

    report += f"""| Métrica | Valor |
|---------|-------|
| **Tendência Geral** | {bullish_count} Bullish / {bearish_count} Bearish (SuperTrend) |
| **RSI Médio** | {avg_rsi:.1f} |
| **Funding Rate Médio** | {avg_funding*100:.4f}% |
| **Fear & Greed** | {fg.get('current', 'N/A')} - {fg.get('classification', 'N/A')} |
| **Liquidações 24h** | ${liq.get('total_usd', 0)/1e9:.2f}B (L: ${liq.get('long_usd', 0)/1e9:.2f}B / S: ${liq.get('short_usd', 0)/1e9:.2f}B) |

---

## Análise por Símbolo

"""

    # Detailed analysis per symbol
    for sym in symbols:
        a = analyses[sym]
        bb_pos = (a['current_price'] - a['bb_lower']) / (a['bb_upper'] - a['bb_lower']) if a['bb_upper'] != a['bb_lower'] else 0.5
        signals = signal_interpretation(a['rsi'], a['macd'], a['macd_signal'], bb_pos, a['supertrend_trend'])

        # Stationarity
        adf = a['stationarity']['price_adf']
        adf_ret = a['stationarity']['returns_adf']

        # Regime
        regime = a['regimes'].get('current_regime', -1)
        regimes = a['regimes'].get('regimes', [])
        regime_mean = regimes[regime]['mean'] if 0 <= regime < len(regimes) else 0

        report += f"""### {sym}

#### Preço e Indicadores Técnicos
| Indicador | Valor | Interpretação |
|-----------|-------|---------------|
| **Preço Atual** | ${a['current_price']:,.2f} | |
| **Variação 2h** | {a['price_change_pct']:+.2f}% | {'🟢' if a['price_change_pct'] > 0 else '🔴'} |
| **RSI(14)** | {a['rsi']:.1f} | {signals['RSI']} |
| **MACD** | {a['macd']:.4f} | {signals['MACD']} |
| **MACD Signal** | {a['macd_signal']:.4f} | |
| **MACD Histogram** | {a['macd_histogram']:.4f} | {'🟢' if a['macd_histogram'] > 0 else '🔴'} |
| **BB Position** | {bb_pos:.1%} | {signals['BB']} |
| **BB Upper** | ${a['bb_upper']:,.2f} | |
| **BB Lower** | ${a['bb_lower']:,.2f} | |
| **VWAP** | ${a['vwap']:,.2f} | {'Acima' if a['current_price'] > a['vwap'] else 'Abaixo'} do VWAP |
| **SuperTrend** | {a['supertrend_trend']} | {signals['SuperTrend']} |
| **ATR(14)** | ${a['atr']:,.2f} | Volatilidade atual |

#### Níveis de Fibonacci (50 barras)
| Nível | Preço | Distância |
|-------|-------|-----------|
"""
        for level, price in a['fib_levels'].items():
            dist = ((a['current_price'] - price) / a['current_price'] * 100) if a['current_price'] > 0 else 0
            near = " ⚠️ PRÓXIMO" if abs(dist) < 2 else ""
            report += f"| {level} | ${price:,.2f} | {dist:+.1f}%{near} |\n"

        report += f"""
#### Estatísticas e Estacionariedade
| Teste | Estatística | p-valor | Conclusão |
|-------|-------------|---------|-----------|
| **ADF (Preço)** | {adf.get('statistic', 0):.4f} | {adf.get('p_value', 1):.4f} | {'Estacionário ✅' if adf.get('stationary') else 'Não estacionário ❌'} |
| **KPSS (Preço)** | {a['stationarity']['price_kpss'].get('statistic', 0):.4f} | {a['stationarity']['price_kpss'].get('p_value', 1):.4f} | {'Estacionário ✅' if a['stationarity']['price_kpss'].get('stationary') else 'Não estacionário ❌'} |
| **ADF (Retornos)** | {adf_ret.get('statistic', 0):.4f} | {adf_ret.get('p_value', 1):.4f} | {'Estacionário ✅' if adf_ret.get('stationary') else 'Não estacionário ❌'} |
| **Hurst Exponent** | {a['hurst'].get('hurst', 0.5):.3f} | — | {a['hurst'].get('interpretation', '')} |
| **Half-Life** | {f"{a['half_life'].get('half_life', float('inf')):.1f} períodos" if not np.isinf(a['half_life'].get('half_life', float('inf'))) else 'N/A (no mean reversion)'} | — | {a['half_life'].get('interpretation', '')} |

#### Risco e Drawdown
| Métrica | Valor |
|---------|-------|
| **VaR 95% (Histórico)** | {a['risk'].get('var_historical', 0)*100:.2f}% |
| **CVaR 95% (Expected Shortfall)** | {a['risk'].get('cvar_historical', 0)*100:.2f}% |
| **Max Drawdown** | {a['drawdowns'].get('max_drawdown', 0)*100:.2f}% |
| **Current Drawdown** | {a['drawdowns'].get('current_drawdown', 0)*100:.2f}% |
| **Avg DD Duration** | {a['drawdowns'].get('avg_drawdown_duration', 0):.1f} períodos |

#### Regime de Mercado (HMM 3 estados)
| Estado Atual | {regime} - {regime_name(regime)} |
| Probabilidades | {[f'{p:.1%}' for p in a['regimes'].get('current_probs', [])]} |
| Retorno Médio do Regime | {regime_mean*100:+.3f}% |

| Estado | Retorno Médio | Volatilidade | % Tempo |
|--------|---------------|--------------|---------|
"""
        for r in a['regimes'].get('regimes', []):
            report += f"| {r['state']} | {r['mean']*100:+.3f}% | {r['std']*100:.2f}% | {r['pct']*100:.1f}% |\n"

        report += f"""
#### Microestrutura e Order Flow
| Métrica | Valor | Interpretação |
|---------|-------|---------------|
| **CVD** | {a['cvd']:+.2f} | {'Pressão compradora 🟢' if a['cvd'] > 0 else 'Pressão vendedora 🔴'} |
| **Kyle's Lambda** | {a['kyle_lambda']:.2e} | Impacto de preço por unidade de volume |
| **Amihud Illiquidity** | {a['amihud']:.2e} | {'Líquido' if a['amihud'] < 1e-6 else 'Pouco líquido'} |
| **Order Book Imbalance** | {a['order_book'].get('imbalance', 0):+.4f} | {'Bids dominam 🟢' if a['order_book'].get('imbalance', 0) > 0 else 'Asks dominam 🔴'} |
| **Spread (bps)** | {a['order_book'].get('spread_bps', 0):.1f} | |
| **Bid Depth (5 níveis)** | {a['order_book'].get('bid_depth', 0):,.0f} | |
| **Ask Depth (5 níveis)** | {a['order_book'].get('ask_depth', 0):,.0f} | |

#### Volume Profile (VPVR)
| Métrica | Valor |
|---------|-------|
| **POC (Point of Control)** | ${a['volume_profile'].get('poc_price', 0):,.2f} |
| **VAH (Value Area High)** | ${a['volume_profile'].get('vah_price', 0):,.2f} |
| **VAL (Value Area Low)** | ${a['volume_profile'].get('val_price', 0):,.2f} |
| **Volume Total** | {a['volume_profile'].get('total_volume', 0):,.0f} |
| **Volume na Value Area** | {a['volume_profile'].get('volume_in_va', 0):,.0f} ({a['volume_profile'].get('volume_in_va', 0)/a['volume_profile'].get('total_volume', 1)*100:.1f}%) |

#### Posicionamento e Funding
| Métrica | Valor |
|---------|-------|
| **Funding Rate** | {a['funding_rate']*100:.4f}% ({a['funding_class']}) |
| **Long/Short Ratio** | {a['long_short_ratio']:.3f} |
| **Long % (Contas)** | {a['long_pct']*100:.1f}% |
| **Open Interest** | {a['open_interest']:,.0f} |
| **OI Change 24h** | {a['oi_change_24h']*100:+.2f}% |

#### Breakpoints Estruturais
- **Detectados:** {len(a.get('breakpoints', []))} pontos de mudança de variância
- **Locais:** {', '.join([str(b) for b in a.get('breakpoints', [])[:10]]) if a.get('breakpoints') else 'Nenhum'}

---
"""

    # Cross-sectional analysis
    if cs:
        report += """
---

## Análise Cross-Sectional (Multi-Ativo)

### Matriz de Correlação (Retornos)
"""
        corr = cs.get('correlation_matrix', {})
        if corr:
            report += "| | " + " | ".join(symbols) + " |\n"
            report += "|" + "---|" * (len(symbols) + 1) + "\n"
            for s1 in symbols:
                row = [f"**{s1}**"]
                for s2 in symbols:
                    v = corr.get(s1, {}).get(s2, 0)
                    row.append(f"{v:.2f}")
                report += "| " + " | ".join(row) + " |\n"

        report += f"""
### Estatísticas de Correlação
- **Correlação Média:** {cs.get('avg_correlation', 0):.2f}
- **Correlação Máxima:** {cs.get('max_correlation', 0):.2f}
- **Correlação Mínima:** {cs.get('min_correlation', 0):.2f}

### Análise de Lead-Lag (Cross-Correlação)
"""
        for pair, ll in cs.get('lead_lag', {}).items():
            if 'error' not in ll:
                report += f"- **{pair}:** Lag ótimo = {ll.get('optimal_lag', 0)} períodos (corr = {ll.get('max_correlation', 0):.3f}) | {ll.get('interpretation', '')}\n"

        report += "\n### Causalidade de Granger\n"
        for pair, gc in cs.get('granger', {}).items():
            if 'error' not in gc:
                report += f"- **{pair}:** {gc.get('s2_causes_s1', False)} → S2 causa S1 (p={gc.get('min_pval_s2_to_s1', 1):.3f}) | S1 causa S2 = {gc.get('s1_causes_s2', False)} (p={gc.get('min_pval_s1_to_s2', 1):.3f})\n"

        # PCA
        pca = cs.get('pca', {})
        if pca.get('explained_variance'):
            report += "\n### Análise de Componentes Principais (PCA)\n"
            for i, var in enumerate(pca['explained_variance']):
                report += f"- **PC{i+1}:** {var*100:.1f}% da variância\n"

    # Fear & Greed
    if fg:
        report += f"""
---

## Fear & Greed Index
- **Valor Atual:** {fg.get('current', 'N/A')} - {fg.get('classification', 'N/A')}
- **Histórico (30 dias):** {fg.get('history_values', [])[:5]}... (últimos 5)
"""

    # Liquidations
    if liq:
        report += f"""
---

## Liquidações 24h (Xoomar)
- **Total:** ${liq.get('total_usd', 0)/1e9:.2f}B
- **Longs:** ${liq.get('long_usd', 0)/1e9:.2f}B ({liq.get('long_usd', 0)/liq.get('total_usd', 1)*100:.1f}%)
- **Shorts:** ${liq.get('short_usd', 0)/1e9:.2f}B ({liq.get('short_usd', 0)/liq.get('total_usd', 1)*100:.1f}%)
- **Maior Single:** ${liq.get('max_single_usd', 0)/1e6:.2f}M
"""

    # Summary signals
    report += """
---

## Sinais Consolidados

| Símbolo | RSI | MACD | BB | SuperTrend | CVD | Regime | **Sinal Geral** |
|---------|-----|------|-----|------------|-----|--------|----------------|
"""

    for sym in symbols:
        a = analyses[sym]
        bb_pos = (a['current_price'] - a['bb_lower']) / (a['bb_upper'] - a['bb_lower']) if a['bb_upper'] != a['bb_lower'] else 0.5
        regime = a['regimes'].get('current_regime', -1)

        bullish_signals = sum([
            a['rsi'] < 30,
            a['macd'] > a['macd_signal'],
            bb_pos < 0.2,
            a['supertrend_trend'] == 'UP',
            a['cvd'] > 0,
        ])

        if bullish_signals >= 4:
            overall = "🟢 **COMPRA FORTE**"
        elif bullish_signals >= 3:
            overall = "🟢 Compra"
        elif bullish_signals <= 1:
            overall = "🔴 **VENDA FORTE**"
        elif bullish_signals <= 2:
            overall = "🔴 Venda"
        else:
            overall = "⚪ Neutro"

        report += f"| {sym} | {a['rsi']:.1f} | {'🟢' if a['macd'] > a['macd_signal'] else '🔴'} | {'🟢' if bb_pos < 0.2 else ('🔴' if bb_pos > 0.8 else '⚪')} | {'🟢' if a['supertrend_trend']=='UP' else '🔴'} | {'🟢' if a['cvd']>0 else '🔴'} | {regime} | {overall} |\n"

    report += f"""

---

## Metodologia e Referências

### Testes Estatísticos
- **ADF (Augmented Dickey-Fuller):** Teste de raiz unitária. H0: série não estacionária.
- **KPSS:** Teste de estacionariedade trend-stationary. H0: série estacionária.
- **Hurst Exponent:** Mede persistência/anti-persistência. H=0.5 = random walk; H>0.5 = persistente (trending); H<0.5 = anti-persistente (mean-reverting).
- **Half-Life (OU Process):** Tempo para reverter 50% do choque à média.

### Microestrutura
- **Kyle's Lambda:** Impacto de preço por unidade de volume (λ = ΔP/ΔV). Maior = menos líquido.
- **Amihud Illiquidity:** |Retorno| / Volume. Mede impacto de preço por dólar negociado.
- **CVD (Cumulative Volume Delta):** Volume agressivo comprador - vendedor.
- **VPVR (Volume Profile Visible Range):** Distribuição de volume por nível de preço. POC = Point of Control.

### Detecção de Regime
- **HMM (Hidden Markov Model):** 3 estados ocultos (Bear, Neutral, Bull) com transições probabilísticas.
- **Breakpoints (Ruptures):** Detecção de mudança estrutural na variância usando algoritmo PELT.

### Referências
1. Dickey, D.A. & Fuller, W.A. (1979). Distribution of the estimators for autoregressive time series with a unit root.
2. Kwiatkowski et al. (1992). Testing the null hypothesis of stationarity.
3. Kyle, A.S. (1985). Continuous auctions and insider trading.
4. Amihud, Y. (2002). Illiquidity and stock returns.
5. Mandelbrot & Wallis (1969). Robustness of the rescaled range.
6. Hamilton (1989). A new approach to the economic analysis of nonstationary time series.

---
*Relatório gerado automaticamente pelo Order Flow Terminal v2.0*
*Dados: Binance Spot/Futures via WebSocket + REST API*
*Atualização: {timestamp}
"""

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate scientific analysis report from live data")
    parser.add_argument("--data-dir", type=str, default="data/live")
    parser.add_argument("--output", type=str, default="data/live/SCIENTIFIC_REPORT.md")
    parser.add_argument("--recent-hours", type=float, default=2.0)
    args = parser.parse_args()

    print(f"Loading live data (last {args.recent_hours}h)...")
    data = load_live_data(args.data_dir, recent_hours=args.recent_hours)

    print("Running scientific analysis...")
    analysis = analyze_all(data)

    print("Generating scientific report...")
    report = generate_scientific_report(analysis)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report saved: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
