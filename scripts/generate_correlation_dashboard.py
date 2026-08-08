#!/usr/bin/env python3
"""Generate interactive HTML dashboard from correlation analysis JSON.

Creates a single self-contained HTML file with:
- Correlation heatmaps (returns, volatility, volume, drawdown)
- Lagged correlation network
- Time-of-day volatility patterns
- Cross-asset momentum analysis
- Movement-following analysis (BTC -> altcoins)
- Category-based correlations
- Regime-dependent correlations
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_html(results: dict) -> str:
    """Generate the full HTML dashboard."""
    symbols = results.get("symbols", [])
    metadata = results.get("symbol_metadata", {})

    # Helper: get category for symbol
    def cat(sym):
        return metadata.get(sym, {}).get("category", "unknown")

    # Helper: get name for symbol
    def name(sym):
        return metadata.get(sym, {}).get("name", sym.replace("USDT", ""))

    # --- Correlation Heatmap (Returns) ---
    ret_corr = results.get("return_correlations", {})
    pearson = ret_corr.get("matrix_pearson", {})
    corr_symbols = ret_corr.get("symbols", symbols)

    # Build heatmap data for JS
    heatmap_data = []
    for i, a in enumerate(corr_symbols):
        for j, b in enumerate(corr_symbols):
            val = pearson.get(a, {}).get(b, 0)
            heatmap_data.append([i, j, float(val)])

    # --- Top correlated pairs ---
    top_pairs = ret_corr.get("top_correlated", [])

    # --- Lagged correlations ---
    lagged = results.get("lagged_correlations", {})
    leaders = lagged.get("leaders", {})

    # --- Time patterns ---
    time_pat = results.get("time_patterns", {})
    avg_hour = time_pat.get("avg_by_hour", {})

    # --- Cross-asset momentum ---
    cross_mom = results.get("cross_asset_momentum", {})
    predictors = cross_mom.get("predictors", {})

    # --- Movement following ---
    movement = results.get("movement_following", {})
    thresholds = movement.get("thresholds", {})

    # --- Category correlations ---
    cat_corr = results.get("category_correlations", {})
    within_cat = cat_corr.get("within_category", {})

    # --- Volatility correlations ---
    vol_corr = results.get("volatility_correlations", {})

    # --- Drawdown correlations ---
    dd_corr = results.get("drawdown_correlations", {})

    # Helper: momentum table row (extracted to avoid nested f-string quote conflicts)
    def _momentum_row(p):
        up_cls = "positive" if p["up_mean_return"] > 0 else "negative"
        down_cls = "positive" if p["down_mean_return"] > 0 else "negative"
        up_wr_cls = "positive" if p["up_win_rate"] > 0.5 else "negative"
        down_wr_cls = "positive" if p["down_win_rate"] > 0.5 else "negative"
        return f"""
                        <tr>
                            <td>{p['target']}</td>
                            <td class="num {up_cls}">{p['up_mean_return']:.4f}</td>
                            <td class="num {up_wr_cls}">{p['up_win_rate']:.1%}</td>
                            <td class="num {down_cls}">{p['down_mean_return']:.4f}</td>
                            <td class="num {down_wr_cls}">{p['down_win_rate']:.1%}</td>
                            <td class="num">{p['correlation']:.4f}</td>
                        </tr>"""

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Correlation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0e17;
            color: #e0e6ed;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #00d4ff;
            margin-bottom: 5px;
            font-size: 28px;
        }}
        .subtitle {{
            text-align: center;
            color: #8892a0;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }}
        .card {{
            background: #131722;
            border: 1px solid #1e222d;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .card.full {{
            grid-column: 1 / -1;
        }}
        .card h2 {{
            color: #00d4ff;
            font-size: 18px;
            margin-bottom: 15px;
            border-bottom: 1px solid #1e222d;
            padding-bottom: 10px;
        }}
        .card h3 {{
            color: #8892a0;
            font-size: 14px;
            margin: 15px 0 10px;
        }}
        .chart {{
            width: 100%;
            height: 400px;
        }}
        .chart.large {{
            height: 500px;
        }}
        .chart.small {{
            height: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #1e222d;
        }}
        th {{
            color: #00d4ff;
            font-weight: 600;
        }}
        td.num {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}
        .positive {{ color: #26a69a; }}
        .negative {{ color: #ef5350; }}
        .neutral {{ color: #8892a0; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-large_cap {{ background: #1b3a5c; color: #4fc3f7; }}
        .badge-mid_cap {{ background: #3a2c1b; color: #ffa726; }}
        .badge-meme {{ background: #4c1b3a; color: #ec407a; }}
        .badge-defi {{ background: #1b4c3a; color: #66bb6a; }}
        .badge-layer2 {{ background: #3a1b4c; color: #ab47bc; }}
        .badge-oracle {{ background: #4c3a1b; color: #ffca28; }}
        .badge-exchange_token {{ background: #1b3a4c; color: #29b6f6; }}
        .badge-unknown {{ background: #2a2a2a; color: #888; }}
        .summary {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            justify-content: center;
        }}
        .stat {{
            background: #131722;
            border: 1px solid #1e222d;
            border-radius: 8px;
            padding: 15px 25px;
            text-align: center;
        }}
        .stat .value {{
            font-size: 28px;
            font-weight: 700;
            color: #00d4ff;
        }}
        .stat .label {{
            font-size: 12px;
            color: #8892a0;
            margin-top: 5px;
        }}
        .insight {{
            background: #0d1117;
            border-left: 3px solid #00d4ff;
            padding: 12px 16px;
            margin: 10px 0;
            font-size: 13px;
            line-height: 1.6;
        }}
        .tabs {{
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .tab {{
            padding: 8px 16px;
            background: #1e222d;
            border: none;
            color: #8892a0;
            cursor: pointer;
            border-radius: 6px;
            font-size: 13px;
        }}
        .tab.active {{
            background: #00d4ff;
            color: #0a0e17;
        }}
        .tab:hover {{
            background: #2a2e3d;
        }}
        .tab.active:hover {{
            background: #00b8d9;
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <h1>Crypto Correlation Dashboard</h1>
    <div class="subtitle">
        Analise comprehensiva de correlacoes: {len(symbols)} simbolos | Timeframe: {results.get('timeframe', '?')} |
        Periodo: {results.get('timeframe', '?')}
    </div>

    <!-- Summary Stats -->
    <div class="summary">
        <div class="stat">
            <div class="value">{len(symbols)}</div>
            <div class="label">Simbolos</div>
        </div>
        <div class="stat">
            <div class="value">{len(top_pairs)}</div>
            <div class="label">Pares Analisados</div>
        </div>
        <div class="stat">
            <div class="value">{len(leaders)}</div>
            <div class="label">Leaders Encontrados</div>
        </div>
        <div class="stat">
            <div class="value">{len(within_cat)}</div>
            <div class="label">Categorias</div>
        </div>
    </div>

    <div class="grid">

        <!-- Correlation Heatmap -->
        <div class="card full">
            <h2>1. Matriz de Correlacao de Returns (Pearson)</h2>
            <div id="heatmap-returns" class="chart large"></div>
        </div>

        <!-- Top Correlated Pairs Table -->
        <div class="card">
            <h2>2. Pares Mais Correlacionados</h2>
            <table>
                <thead>
                    <tr>
                        <th>Par</th>
                        <th>Categoria</th>
                        <th class="num">Pearson</th>
                        <th class="num">Spearman</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{p['a']} / {p['b']}</td>
                        <td><span class="badge badge-{cat(p['a'])}">{cat(p['a'])}</span></td>
                        <td class="num {'positive' if p['pearson'] > 0 else 'negative'}">{p['pearson']:.4f}</td>
                        <td class="num {'positive' if p['spearman'] > 0 else 'negative'}">{p['spearman']:.4f}</td>
                    </tr>''' for p in top_pairs[:15])}
                </tbody>
            </table>
        </div>

        <!-- Least Correlated Pairs -->
        <div class="card">
            <h2>3. Pares Menos Correlacionados (Diversificacao)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Par</th>
                        <th class="num">Pearson</th>
                        <th class="num">Spearman</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{p['a']} / {p['b']}</td>
                        <td class="num {'positive' if p['pearson'] > 0 else 'negative'}">{p['pearson']:.4f}</td>
                        <td class="num {'positive' if p['spearman'] > 0 else 'negative'}">{p['spearman']:.4f}</td>
                    </tr>''' for p in ret_corr.get('least_correlated', [])[:15])}
                </tbody>
            </table>
        </div>

        <!-- Lagged Correlations -->
        <div class="card full">
            <h2>4. Relacoes Lead-Lag (Quem lidera quem?)</h2>
            <div class="insight">
                Esta analise mostra se o movimento de uma moeda prediz o movimento de outra N barras depois.
                Correlacoes altas em lag > 0 indicam que o "leader" precede o "follower".
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Leader</th>
                        <th>Follower</th>
                        <th class="num">Best Lag</th>
                        <th class="num">Correlacao</th>
                        <th>Interpretacao</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td><strong>{leader}</strong></td>
                        <td>{f['follower']}</td>
                        <td class="num">{f['best_lag']} bars</td>
                        <td class="num {'positive' if f['correlation'] > 0 else 'negative'}">{f['correlation']:.4f}</td>
                        <td class="neutral">{'Leader precede follower' if abs(f['correlation']) > 0.3 else 'Fraca'}</td>
                    </tr>''' for leader, followers in leaders.items() for f in followers[:5])}
                </tbody>
            </table>
        </div>

        <!-- Time of Day Patterns -->
        <div class="card full">
            <h2>5. Padroes por Hora do Dia (Volatilidade Media)</h2>
            <div class="insight">
                Mostra a volatilidade media (high-low)/close por hora do dia, agregada entre todos os simbolos.
                Horas com maior volatilidade sao melhores para day trading.
            </div>
            <div id="chart-hour-vol" class="chart"></div>
        </div>

        <!-- Volume by Hour -->
        <div class="card full">
            <h2>6. Volume por Hora do Dia</h2>
            <div id="chart-hour-vol" class="chart"></div>
        </div>

        <!-- Cross-Asset Momentum -->
        <div class="card full">
            <h2>7. Momentum Cross-Asset (BTC/ETH prediz altcoins?)</h2>
            <div class="insight">
                Se BTC subiu X% nos ultimos N dias, qual a probabilidade de cada altcoin subir nos proximos N dias?
            </div>
            <div class="tabs" id="mom-tabs">
                {''.join(f'<button class="tab {"active" if i == 0 else ""}" onclick="showTab({chr(39)}mom-{i}{chr(39)})">{key}</button>' for i, key in enumerate(predictors.keys()))}
            </div>
            {''.join(f'''
            <div id="mom-{i}" class="tab-content {"active" if i == 0 else ""}">
                <table>
                    <thead>
                        <tr>
                            <th>Alvo</th>
                            <th class="num">BTC Up: Retorno Medio</th>
                            <th class="num">BTC Up: Win Rate</th>
                            <th class="num">BTC Down: Retorno Medio</th>
                            <th class="num">BTC Down: Win Rate</th>
                            <th class="num">Correlacao</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(_momentum_row(p) for p in preds[:20])}
                    </tbody>
                </table>
            </div>''' for i, (key, preds) in enumerate(predictors.items()))}
        </div>

        <!-- Movement Following -->
        <div class="card full">
            <h2>8. Movimentos Grandes de BTC -> Altcoins (Bar Seguinte)</h2>
            <div class="insight">
                Quando BTC sobe > X% em um bar, o que altcoins fazem no bar seguinte?
                Win rate > 60% indica que altcoins seguem BTC com alta probabilidade.
            </div>
            <div id="chart-movement" class="chart large"></div>
        </div>

        <!-- Category Correlations -->
        <div class="card">
            <h2>9. Correlacao Media por Categoria</h2>
            <div id="chart-category" class="chart"></div>
        </div>

        <!-- Regime Correlations -->
        <div class="card">
            <h2>10. Correlacoes em Bull vs Bear Market</h2>
            <div class="insight">
                Correlacoes aumentam em bear markets. Isso e importante para gestao de risco.
            </div>
            <div id="chart-regime" class="chart"></div>
        </div>

        <!-- Volatility Correlation Heatmap -->
        <div class="card full">
            <h2>11. Matriz de Correlacao de Volatilidade (20-day rolling std)</h2>
            <div id="heatmap-vol" class="chart large"></div>
        </div>

        <!-- Drawdown Correlation Heatmap -->
        <div class="card full">
            <h2>12. Matriz de Correlacao de Drawdowns</h2>
            <div class="insight">
            Drawdowns correlacionados significam que os ativos caem juntos. Importante para diversificacao de portfolio.
            </div>
            <div id="heatmap-dd" class="chart large"></div>
        </div>

    </div>

    <script>
        // Data from Python
        const corrSymbols = {json.dumps(corr_symbols)};
        const heatmapData = {json.dumps(heatmap_data)};
        const avgHour = {json.dumps(avg_hour)};

        // 1. Returns Correlation Heatmap
        const heatmapReturns = echarts.init(document.getElementById('heatmap-returns'));
        heatmapReturns.setOption({{
            tooltip: {{
                position: 'top',
                formatter: function(p) {{
                    return corrSymbols[p.data[0]] + ' vs ' + corrSymbols[p.data[1]] + '<br>Correlation: ' + p.data[2].toFixed(4);
                }}
            }},
            grid: {{ height: '70%', top: '10%' }},
            xAxis: {{ type: 'category', data: corrSymbols, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
            yAxis: {{ type: 'category', data: corrSymbols, axisLabel: {{ fontSize: 11 }} }},
            visualMap: {{
                min: -1, max: 1, calculable: true,
                orient: 'horizontal', left: 'center', bottom: '2%',
                inRange: {{ color: ['#ef5350', '#fff', '#26a69a'] }}
            }},
            series: [{{ type: 'heatmap', data: heatmapData, label: {{ show: false }} }}]
        }});

        // 5. Hour Volatility Chart
        if (avgHour && avgHour.hours) {{
            const chartHourVol = echarts.init(document.getElementById('chart-hour-vol'));
            chartHourVol.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: avgHour.hours.map(h => h + ':00') }},
                yAxis: {{ type: 'value', name: 'Volatilidade' }},
                series: [{{
                    name: 'Volatilidade Media',
                    type: 'bar',
                    data: avgHour.volatility,
                    itemStyle: {{ color: '#00d4ff' }}
                }}],
                grid: {{ left: '8%', right: '5%', bottom: '10%' }}
            }});
        }}

        // 8. Movement Following Chart
        const thresholds = {json.dumps(thresholds)};
        const movementChart = echarts.init(document.getElementById('chart-movement'));
        const threshKeys = Object.keys(thresholds);
        const upWinRates = threshKeys.map(k => {{
            const followers = thresholds[k]['btc_up_big']['followers'];
            const avg = Object.values(followers).reduce((s, f) => s + f.win_rate, 0) / Object.keys(followers).length;
            return avg;
        }});
        const downWinRates = threshKeys.map(k => {{
            const followers = thresholds[k]['btc_down_big']['followers'];
            const avg = Object.values(followers).reduce((s, f) => s + f.win_rate, 0) / Object.keys(followers).length;
            return avg;
        }});
        movementChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['BTC Up -> Altcoin Up (win rate)', 'BTC Down -> Altcoin Down (win rate)'], top: 0 }},
            xAxis: {{ type: 'category', data: threshKeys }},
            yAxis: {{ type: 'value', max: 1, axisLabel: {{ formatter: v => (v*100).toFixed(0) + '%' }} }},
            series: [
                {{ name: 'BTC Up -> Altcoin Up (win rate)', type: 'bar', data: upWinRates, itemStyle: {{ color: '#26a69a' }} }},
                {{ name: 'BTC Down -> Altcoin Down (win rate)', type: 'bar', data: downWinRates.map(v => 1-v), itemStyle: {{ color: '#ef5350' }} }}
            ],
            grid: {{ left: '8%', right: '5%', bottom: '10%', top: '15%' }}
        }});

        // 9. Category Correlations
        const withinCat = {json.dumps(within_cat)};
        const catChart = echarts.init(document.getElementById('chart-category'));
        catChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ type: 'category', data: Object.keys(withinCat), axisLabel: {{ rotate: 30 }} }},
            yAxis: {{ type: 'value', min: 0, max: 1 }},
            series: [{{
                type: 'bar',
                data: Object.values(withinCat).map(v => v.avg_correlation),
                itemStyle: {{ color: '#00d4ff' }}
            }}],
            grid: {{ left: '10%', right: '5%', bottom: '20%' }}
        }});

        // 11. Volatility Correlation Heatmap
        const volCorr = {json.dumps(vol_corr.get('matrix', dict()))};
        const volSymbols = {json.dumps(vol_corr.get('symbols', symbols))};
        const volHeatmapData = [];
        volSymbols.forEach((a, i) => {{
            volSymbols.forEach((b, j) => {{
                volHeatmapData.push([i, j, volCorr[a] ? (volCorr[a][b] || 0) : 0]);
            }});
        }});
        const heatmapVol = echarts.init(document.getElementById('heatmap-vol'));
        heatmapVol.setOption({{
            tooltip: {{
                position: 'top',
                formatter: p => volSymbols[p.data[0]] + ' vs ' + volSymbols[p.data[1]] + '<br>Vol Corr: ' + p.data[2].toFixed(4)
            }},
            grid: {{ height: '70%', top: '10%' }},
            xAxis: {{ type: 'category', data: volSymbols, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
            yAxis: {{ type: 'category', data: volSymbols, axisLabel: {{ fontSize: 11 }} }},
            visualMap: {{
                min: 0, max: 1, calculable: true,
                orient: 'horizontal', left: 'center', bottom: '2%',
                inRange: {{ color: ['#131722', '#00d4ff'] }}
            }},
            series: [{{ type: 'heatmap', data: volHeatmapData }}]
        }});

        // 12. Drawdown Correlation Heatmap
        const ddCorr = {json.dumps(dd_corr.get('matrix', dict()))};
        const ddSymbols = {json.dumps(dd_corr.get('symbols', symbols))};
        const ddHeatmapData = [];
        ddSymbols.forEach((a, i) => {{
            ddSymbols.forEach((b, j) => {{
                ddHeatmapData.push([i, j, ddCorr[a] ? (ddCorr[a][b] || 0) : 0]);
            }});
        }});
        const heatmapDD = echarts.init(document.getElementById('heatmap-dd'));
        heatmapDD.setOption({{
            tooltip: {{
                position: 'top',
                formatter: p => ddSymbols[p.data[0]] + ' vs ' + ddSymbols[p.data[1]] + '<br>DD Corr: ' + p.data[2].toFixed(4)
            }},
            grid: {{ height: '70%', top: '10%' }},
            xAxis: {{ type: 'category', data: ddSymbols, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
            yAxis: {{ type: 'category', data: ddSymbols, axisLabel: {{ fontSize: 11 }} }},
            visualMap: {{
                min: 0, max: 1, calculable: true,
                orient: 'horizontal', left: 'center', bottom: '2%',
                inRange: {{ color: ['#131722', '#ef5350'] }}
            }},
            series: [{{ type: 'heatmap', data: ddHeatmapData }}]
        }});

        // Tab switching
        function showTab(id) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }}

        // Resize charts on window resize
        window.addEventListener('resize', () => {{
            document.querySelectorAll('[id^=chart-], [id^=heatmap-]').forEach(el => {{
                const inst = echarts.getInstanceByDom(el);
                if (inst) inst.resize();
            }});
        }});
    </script>
</body>
</html>"""
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate HTML dashboard from correlation analysis")
    parser.add_argument("--input", type=str, default="data/analysis/correlation_analysis.json", help="Input JSON file")
    parser.add_argument("--output", type=str, default="data/analysis/correlation_dashboard.html", help="Output HTML file")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        print("Run scripts/analyze_correlations.py first.")
        sys.exit(1)

    print(f"Loading analysis from: {input_path}")
    with open(input_path) as f:
        results = json.load(f)

    print("Generating HTML dashboard...")
    html = generate_html(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"\nDashboard saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"\nOpen in browser: file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
