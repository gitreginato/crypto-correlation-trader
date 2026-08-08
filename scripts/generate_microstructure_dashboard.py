#!/usr/bin/env python3
"""Generate HTML dashboard for microstructure analysis.

Shows the "game behind the candles": who is buying, who is selling,
where volume concentrates, and how prices are directed.
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_html(results: dict) -> str:
    symbols = results.get("symbols", [])
    timeframe = results.get("timeframe", "15m")

    # Taker buy/sell
    taker = results.get("taker_buy_sell", {})
    avg_hour = taker.get("avg_by_hour", {})

    # Gaps
    gaps = results.get("gap_analysis", {}).get("symbols", {})

    # Wicks
    wicks = results.get("wick_analysis", {})
    wick_avg_hour = wicks.get("avg_by_hour", {})

    # Volume profile
    vol_profile = results.get("volume_profile", {}).get("symbols", {})

    # Round numbers
    round_num = results.get("round_number_clustering", {}).get("symbols", {})

    # Order flow
    ofi = results.get("order_flow_imbalance", {})
    ofi_avg_hour = ofi.get("avg_ofi_by_hour", {})

    # Price magnetism
    magnetism = results.get("price_magnetism", {}).get("symbols", {})

    # Candle anatomy
    anatomy = results.get("candle_anatomy", {})
    anatomy_avg_hour = anatomy.get("avg_by_hour", {})

    # Accumulation/Distribution
    acc_dist = results.get("accumulation_distribution", {}).get("symbols", {})

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microestrutura: O Jogo Atras das Velas</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0e17;
            color: #e0e6ed;
            padding: 20px;
        }}
        h1 {{ text-align: center; color: #ff9800; margin-bottom: 5px; font-size: 28px; }}
        .subtitle {{ text-align: center; color: #8892a0; margin-bottom: 30px; font-size: 14px; }}
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
        .card.full {{ grid-column: 1 / -1; }}
        .card h2 {{ color: #ff9800; font-size: 18px; margin-bottom: 15px; border-bottom: 1px solid #1e222d; padding-bottom: 10px; }}
        .card h3 {{ color: #8892a0; font-size: 14px; margin: 15px 0 10px; }}
        .chart {{ width: 100%; height: 400px; }}
        .chart.large {{ height: 500px; }}
        .chart.small {{ height: 300px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #1e222d; }}
        th {{ color: #ff9800; font-weight: 600; }}
        td.num {{ text-align: right; font-family: 'Courier New', monospace; }}
        .positive {{ color: #26a69a; }}
        .negative {{ color: #ef5350; }}
        .neutral {{ color: #8892a0; }}
        .insight {{
            background: #0d1117;
            border-left: 3px solid #ff9800;
            padding: 12px 16px;
            margin: 10px 0;
            font-size: 13px;
            line-height: 1.6;
        }}
        .insight.critical {{
            border-left-color: #ef5350;
            background: #1a0a0a;
        }}
        .insight.good {{
            border-left-color: #26a69a;
            background: #0a1a14;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        .stat-box {{
            background: #1a1e2d;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }}
        .stat-box .value {{ font-size: 22px; font-weight: 700; color: #ff9800; }}
        .stat-box .label {{ font-size: 11px; color: #8892a0; margin-top: 4px; }}
        .tabs {{ display: flex; gap: 5px; margin-bottom: 15px; flex-wrap: wrap; }}
        .tab {{
            padding: 6px 14px; background: #1e222d; border: none; color: #8892a0;
            cursor: pointer; border-radius: 6px; font-size: 13px;
        }}
        .tab.active {{ background: #ff9800; color: #0a0e17; }}
        .tab:hover {{ background: #2a2e3d; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <h1>Microestrutura: O Jogo Atras das Velas</h1>
    <div class="subtitle">
        Analise de order flow, volume profile, gaps, wicks e direcionamento de preco | {len(symbols)} simbolos | TF: {timeframe}
    </div>

    <div class="grid">

        <!-- Taker Buy/Sell by Hour -->
        <div class="card full">
            <h2>1. Quem Esta Comprando vs Vendendo por Hora do Dia (Taker Buy/Sell Ratio)</h2>
            <div class="insight">
                <strong>Ratio > 1</strong>: compradores agressivos dominam (market buys). <strong>Ratio < 1</strong>: vendedores dominam (market sells).
                Isso mostra quem esta no controle em cada hora. Horas com ratio consistente > 1 sao favoraveis para long.
            </div>
            <div id="chart-taker-hour" class="chart large"></div>
        </div>

        <!-- Net Aggression by Hour -->
        <div class="card full">
            <h2>2. Aggressao Liquida por Hora (Net Order Flow)</h2>
            <div class="insight">
                Percentual de volume de compra agressiva menos venda agressiva. Valores positivos = pressao de compra liquida.
                Mostra quando os "bots das empresas" estao comprando ou vendendo mais agressivamente.
            </div>
            <div id="chart-net-agg" class="chart"></div>
        </div>

        <!-- Taker Buy/Sell Table -->
        <div class="card">
            <h2>3. Resumo: Quem Domina por Simbolo</h2>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">Ratio Medio</th>
                        <th class="num">% Buy Dominant</th>
                        <th class="num">Net Aggression</th>
                        <th>Veredito</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td><strong>{sym}</strong></td>
                        <td class="num {'positive' if info['avg_ratio'] > 1 else 'negative'}">{info['avg_ratio']:.3f}</td>
                        <td class="num {'positive' if info['pct_buy_dominant'] > 0.5 else 'negative'}">{info['pct_buy_dominant']:.1%}</td>
                        <td class="num {'positive' if info['net_aggression'] > 0 else 'negative'}">{info['net_aggression']:.4f}</td>
                        <td class="{'positive' if info['net_aggression'] > 0.01 else 'negative' if info['net_aggression'] < -0.01 else 'neutral'}">
                            {'COMPRA' if info['net_aggression'] > 0.01 else 'VENDA' if info['net_aggression'] < -0.01 else 'NEUTRO'}
                        </td>
                    </tr>''' for sym, info in taker.get('symbols', dict()).items())}
                </tbody>
            </table>
        </div>

        <!-- Gap Analysis -->
        <div class="card">
            <h2>4. Analise de Gaps (Lacunas de Preco)</h2>
            <div class="insight">
                Gaps grandes (open != close anterior) indicam movimentos repentinos: news, manipulacao, ou bots agindo em horarios de baixa liquidez.
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">Gap Medio</th>
                        <th class="num">Gap Max</th>
                        <th class="num">Gap Min</th>
                        <th class="num">Gaps Grandes</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{sym}</td>
                        <td class="num">{info['avg_gap_pct']:.3f}%</td>
                        <td class="num positive">{info['max_gap_pct']:.2f}%</td>
                        <td class="num negative">{info['min_gap_pct']:.2f}%</td>
                        <td class="num {'negative' if info['num_large_gaps'] > 10 else ''}">{info['num_large_gaps']}</td>
                    </tr>''' for sym, info in gaps.items())}
                </tbody>
            </table>
        </div>

        <!-- Wick Analysis by Hour -->
        <div class="card full">
            <h2>5. Rejeicoes por Hora (Wick Analysis)</h2>
            <div class="insight">
                <strong>Upper wick alto</strong>: preco subiu mas foi rejeitado (vendedores forte). <strong>Lower wick alto</strong>: preco caiu mas foi rejeitado (compradores forte).
                Horas com mais lower wick = suporte forte. Horas com mais upper wick = resistencia forte.
            </div>
            <div id="chart-wick-hour" class="chart large"></div>
        </div>

        <!-- Volume Profile -->
        <div class="card full">
            <h2>6. Volume Profile: Onde o Volume Se Concentra por Nivel de Preco</h2>
            <div class="insight">
                <strong>POC (Point of Control)</strong>: nivel de preco com maior volume = zona de batalha principal.
                <strong>HVN (High Volume Nodes)</strong>: zonas de suporte/resistencia forte.
                <strong>LVN (Low Volume Nodes)</strong>: zonas de movimento rapido (pouca resistencia).
            </div>
            <div class="tabs" id="vp-tabs">
                {''.join(f'<button class="tab {"active" if i == 0 else ""}" onclick="showTab({chr(39)}vp-{i}{chr(39)})">{sym}</button>' for i, sym in list(enumerate(vol_profile.keys()))[:10])}
            </div>
            {''.join(f'''
            <div id="vp-{i}" class="tab-content {"active" if i == 0 else ""}">
                <div class="stat-grid">
                    <div class="stat-box"><div class="value">{info["poc"]:.2f}</div><div class="label">POC</div></div>
                    <div class="stat-box"><div class="value">{info["current_price"]:.2f}</div><div class="label">Preco Atual</div></div>
                    <div class="stat-box"><div class="value">{len(info["hvn_levels"])}</div><div class="label">HVN Nodes</div></div>
                    <div class="stat-box"><div class="value">{len(info["lvn_levels"])}</div><div class="label">LVN Nodes</div></div>
                </div>
                <div id="chart-vp-{i}" class="chart large"></div>
            </div>''' for i, (sym, info) in list(enumerate(vol_profile.items()))[:10])}
        </div>

        <!-- Round Number Clustering -->
        <div class="card">
            <h2>7. Clustering em Numeros Redondos (Alvos Psicologicos)</h2>
            <div class="insight">
                Se precos se agrupam perto de numeros redondos ($100, $1000, $50000), isso indica que bots/operadores estao direcionando precos para niveis psicologicos.
                <strong>Clustering factor > 1</strong> = mais clustering que o esperado ao acaso.
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">Preco Atual</th>
                        <th class="num">% Perto Round</th>
                        <th class="num">Clustering Factor</th>
                        <th>Interpretacao</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{sym}</td>
                        <td class="num">{info['current_price']:.4f}</td>
                        <td class="num">{info['pct_near_round']:.1%}</td>
                        <td class="num {'positive' if info['clustering_factor'] > 1.5 else ''}">{info['clustering_factor']:.2f}x</td>
                        <td class="{'positive' if info['clustering_factor'] > 1.5 else 'neutral'}">{'SIM - alvos psicologicos' if info['clustering_factor'] > 1.5 else 'Normal'}</td>
                    </tr>''' for sym, info in round_num.items())}
                </tbody>
            </table>
        </div>

        <!-- Order Flow Imbalance -->
        <div class="card">
            <h2>8. Order Flow: Compra Real vs Absorcao</h2>
            <div class="insight">
                <strong>True Buy</strong>: compra agressiva + preco subiu = compra real. <strong>Absorption Buy</strong>: compra agressiva mas preco nao subiu = alguem absorvendo as compras (vendedor grande).
                Absorcao alta = possivel distribuicao (smart money vendendo).
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">True Buy</th>
                        <th class="num">True Sell</th>
                        <th class="num">Absorp. Buy</th>
                        <th class="num">Absorp. Sell</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{sym}</td>
                        <td class="num positive">{info['pct_true_buy']:.1%}</td>
                        <td class="num negative">{info['pct_true_sell']:.1%}</td>
                        <td class="num {'negative' if info['pct_absorption_buy'] > 0.1 else ''}">{info['pct_absorption_buy']:.1%}</td>
                        <td class="num {'positive' if info['pct_absorption_sell'] > 0.1 else ''}">{info['pct_absorption_sell']:.1%}</td>
                    </tr>''' for sym, info in ofi.get('symbols', dict()).items())}
                </tbody>
            </table>
        </div>

        <!-- OFI by Hour -->
        <div class="card full">
            <h2>9. Order Flow Imbalance por Hora</h2>
            <div class="insight">
                Mostra a aggressao liquida (compra - venda) por hora. Horas com OFI positivo = pressao de compra. Horas com OFI negativo = pressao de venda.
                Isso revela em quais horarios os bots estao comprando vs vendendo.
            </div>
            <div id="chart-ofi-hour" class="chart"></div>
        </div>

        <!-- Price Magnetism -->
        <div class="card">
            <h2>10. Magnetismo de Preco (Reversao a VWAP)</h2>
            <div class="insight">
                Apos o preco se afastar do VWAP, ele tende a voltar? <strong>Taxa de reversao > 55%</strong> indica forte magnetismo (mean reversion).
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">Rev. 1 Bar</th>
                        <th class="num">Rev. 3 Bars</th>
                        <th class="num">Rev. 6 Bars</th>
                        <th>Forca</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{sym}</td>
                        <td class="num">{info['reversion_rate_1bar']:.1%}</td>
                        <td class="num">{info['reversion_rate_3bar']:.1%}</td>
                        <td class="num {'positive' if info['reversion_rate_6bar'] > 0.55 else ''}">{info['reversion_rate_6bar']:.1%}</td>
                        <td class="{'positive' if info['reversion_rate_6bar'] > 0.6 else 'neutral'}">{'FORTE' if info['reversion_rate_6bar'] > 0.6 else 'Moderado' if info['reversion_rate_6bar'] > 0.55 else 'Fraco'}</td>
                    </tr>''' for sym, info in magnetism.items())}
                </tbody>
            </table>
        </div>

        <!-- Candle Anatomy by Hour -->
        <div class="card full">
            <h2>11. Anatomia das Velas por Hora (Body vs Wick)</h2>
            <div class="insight">
                <strong>Body ratio alto</strong>: velas com corpo grande = conviccao (movimento direcional forte).
                <strong>% Bull alto</strong>: mais velas verdes que vermelhas = tendencia de compra.
            </div>
            <div id="chart-anatomy-hour" class="chart large"></div>
        </div>

        <!-- Accumulation/Distribution -->
        <div class="card">
            <h2>12. Fases: Acumulacao vs Distribuicao</h2>
            <div class="insight">
                <strong>Acumulacao</strong>: preco flat + volume alto = smart money comprando discretamente.
                <strong>Distribuicao</strong>: preco subindo + volume alto = smart money vendendo.
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Simbolo</th>
                        <th class="num">Acumul.</th>
                        <th class="num">Distrib.</th>
                        <th class="num">Markup</th>
                        <th class="num">Markdown</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{sym}</td>
                        <td class="num positive">{info['pct_accumulation']:.1%}</td>
                        <td class="num negative">{info['pct_distribution']:.1%}</td>
                        <td class="num positive">{info['pct_markup']:.1%}</td>
                        <td class="num negative">{info['pct_markdown']:.1%}</td>
                    </tr>''' for sym, info in acc_dist.items())}
                </tbody>
            </table>
        </div>

    </div>

    <script>
        const avgHour = {json.dumps(avg_hour)};
        const wickAvgHour = {json.dumps(wick_avg_hour)};
        const ofiAvgHour = {json.dumps(ofi_avg_hour)};
        const anatomyAvgHour = {json.dumps(anatomy_avg_hour)};
        const volProfile = {json.dumps(vol_profile)};

        // 1. Taker Buy/Sell by Hour
        if (avgHour && avgHour.hours) {{
            const chart = echarts.init(document.getElementById('chart-taker-hour'));
            chart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: ['Taker Buy/Sell Ratio', '1.0 (Equilibrio)'], top: 5 }},
                xAxis: {{ type: 'category', data: avgHour.hours.map(h => h + ':00') }},
                yAxis: [
                    {{ type: 'value', name: 'Ratio', min: 0.8, max: 1.2 }},
                ],
                series: [
                    {{
                        name: 'Taker Buy/Sell Ratio',
                        type: 'line',
                        data: avgHour.ratio,
                        smooth: true,
                        itemStyle: {{ color: '#ff9800' }},
                        areaStyle: {{ opacity: 0.3 }},
                        markLine: {{ data: [{{ yAxis: 1.0, lineStyle: {{ color: '#888', type: 'dashed' }} }}] }}
                    }}
                ],
                grid: {{ left: '8%', right: '5%', bottom: '10%', top: '15%' }}
            }});
        }}

        // 2. Net Aggression by Hour
        if (avgHour && avgHour.hours) {{
            const chart = echarts.init(document.getElementById('chart-net-agg'));
            chart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: avgHour.hours.map(h => h + ':00') }},
                yAxis: {{ type: 'value', name: 'Net %' }},
                series: [{{
                    name: 'Net Aggression %',
                    type: 'bar',
                    data: avgHour.net_pct,
                    itemStyle: {{
                        color: function(p) {{ return p.data > 0 ? '#26a69a' : '#ef5350'; }}
                    }}
                }}],
                grid: {{ left: '8%', right: '5%', bottom: '10%' }}
            }});
        }}

        // 5. Wick Analysis by Hour
        if (wickAvgHour && wickAvgHour.hours) {{
            const chart = echarts.init(document.getElementById('chart-wick-hour'));
            chart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: ['Upper Wick (Rejeicao Venda)', 'Lower Wick (Rejeicao Compra)', 'Body (Conviccao)'], top: 5 }},
                xAxis: {{ type: 'category', data: wickAvgHour.hours.map(h => h + ':00') }},
                yAxis: {{ type: 'value', name: 'Ratio' }},
                series: [
                    {{ name: 'Upper Wick', type: 'line', data: wickAvgHour.upper_wick, smooth: true, itemStyle: {{ color: '#ef5350' }} }},
                    {{ name: 'Lower Wick', type: 'line', data: wickAvgHour.lower_wick, smooth: true, itemStyle: {{ color: '#26a69a' }} }},
                    {{ name: 'Body', type: 'line', data: wickAvgHour.body, smooth: true, itemStyle: {{ color: '#ff9800' }} }}
                ],
                grid: {{ left: '8%', right: '5%', bottom: '10%', top: '15%' }}
            }});
        }}

        // 6. Volume Profile charts
        Object.keys(volProfile).slice(0, 10).forEach((sym, i) => {{
            const el = document.getElementById('chart-vp-' + i);
            if (!el) return;
            const info = volProfile[sym];
            const chart = echarts.init(el);
            chart.setOption({{
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '15%', right: '10%', bottom: '10%' }},
                xAxis: {{ type: 'value', name: 'Volume' }},
                yAxis: {{ type: 'value', name: 'Preco', inverse: true, min: info.price_min, max: info.price_max }},
                series: [{{
                    type: 'bar',
                    data: info.volume.map((v, i) => [v, info.price_levels[i]]),
                    itemStyle: {{
                        color: function(p) {{
                            const pocIdx = info.volume.indexOf(Math.max(...info.volume));
                            return p.dataIndex === pocIdx ? '#ff9800' : '#1e88e5';
                        }}
                    }}
                }}],
                markLine: {{
                    data: [
                        {{ yAxis: info.poc, lineStyle: {{ color: '#ff9800', type: 'solid', width: 2 }}, label: {{ formatter: 'POC' }} }},
                        {{ yAxis: info.current_price, lineStyle: {{ color: '#26a69a', type: 'dashed', width: 2 }}, label: {{ formatter: 'Atual' }} }}
                    ]
                }}
            }});
        }});

        // 9. OFI by Hour
        if (ofiAvgHour && ofiAvgHour.hours) {{
            const chart = echarts.init(document.getElementById('chart-ofi-hour'));
            chart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: ofiAvgHour.hours.map(h => h + ':00') }},
                yAxis: {{ type: 'value', name: 'OFI' }},
                series: [{{
                    type: 'bar',
                    data: ofiAvgHour.ofi,
                    itemStyle: {{ color: function(p) {{ return p.data > 0 ? '#26a69a' : '#ef5350'; }} }}
                }}],
                grid: {{ left: '8%', right: '5%', bottom: '10%' }}
            }});
        }}

        // 11. Candle Anatomy by Hour
        if (anatomyAvgHour && anatomyAvgHour.hours) {{
            const chart = echarts.init(document.getElementById('chart-anatomy-hour'));
            chart.setOption({{
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: ['Body Ratio (Conviccao)', '% Bull Candles'], top: 5 }},
                xAxis: {{ type: 'category', data: anatomyAvgHour.hours.map(h => h + ':00') }},
                yAxis: [
                    {{ type: 'value', name: 'Body Ratio' }},
                    {{ type: 'value', name: '% Bull', max: 1, axisLabel: {{ formatter: v => (v*100).toFixed(0) + '%' }} }}
                ],
                series: [
                    {{ name: 'Body Ratio', type: 'bar', data: anatomyAvgHour.body_ratio, itemStyle: {{ color: '#ff9800' }} }},
                    {{ name: '% Bull Candles', type: 'line', yAxisIndex: 1, data: anatomyAvgHour.bull_pct, smooth: true, itemStyle: {{ color: '#26a69a' }} }}
                ],
                grid: {{ left: '8%', right: '8%', bottom: '10%', top: '15%' }}
            }});
        }}

        // Tab switching
        function showTab(id) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
            // Resize charts in newly visible tab
            setTimeout(() => {{
                const tab = document.getElementById(id);
                tab.querySelectorAll('[id^=chart-]').forEach(el => {{
                    const inst = echarts.getInstanceByDom(el);
                    if (inst) inst.resize();
                }});
            }}, 100);
        }}

        window.addEventListener('resize', () => {{
            document.querySelectorAll('[id^=chart-]').forEach(el => {{
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
    parser = argparse.ArgumentParser(description="Generate microstructure HTML dashboard")
    parser.add_argument("--input", type=str, default="data/analysis/microstructure_analysis.json")
    parser.add_argument("--output", type=str, default="data/analysis/microstructure_dashboard.html")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found. Run scripts/analyze_microstructure.py first.")
        sys.exit(1)

    with open(input_path) as f:
        results = json.load(f)

    print("Generating microstructure dashboard...")
    html = generate_html(results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard saved: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"Open: file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
