#!/usr/bin/env python3
"""Convert drawio XML to standalone SVG files. No external dependencies."""
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path


def parse_style(style_str):
    """Parse drawio style string into dict."""
    if not style_str:
        return {}
    parts = style_str.split(';')
    result = {}
    for p in parts:
        p = p.strip()
        if '=' in p:
            k, v = p.split('=', 1)
            result[k] = v
        elif p:
            result[p] = '1'
    return result


def get_color(style, key, default):
    v = style.get(key, default)
    if v == 'none':
        return 'none'
    return v


def drawio_to_svg(mxgraph_xml, width=2000, height=1400):
    """Convert mxGraphModel XML to SVG string."""
    root = ET.fromstring(mxgraph_xml)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="background:#0B0E14;">',
        '<style>',
        '  text { font-family: Inter, -apple-system, Segoe UI, sans-serif; }',
        '  .lane-label { font-size: 14px; font-weight: bold; fill: #fff; }',
        '  .node-label { font-size: 11px; fill: #fff; text-anchor: middle; }',
        '  .done { fill: #2e7d32; stroke: #4caf50; }',
        '  .todo { fill: #3a3a3a; stroke: #777; stroke-dasharray: 5,3; }',
        '  .partial { fill: #a67c00; stroke: #d4a017; }',
        '  .me { fill: #b71c1c; stroke: #e53935; }',
        '  .exchange { fill: #0277bd; stroke: #039be5; }',
        '  .retail { fill: #a55a00; stroke: #d4a017; }',
        '  .quant { fill: #6a1b9a; stroke: #8e24aa; }',
        '  .onchain { fill: #00695c; stroke: #00897b; }',
        '  .oracle { fill: #0d47a1; stroke: #1565c0; }',
        '  .lane-done { fill: #0f1f1a; stroke: #2e7d32; }',
        '  .lane-todo { fill: #1a0808; stroke: #777; stroke-dasharray: 5,3; }',
        '  .lane-partial { fill: #1f1800; stroke: #a67c00; }',
        '  .lane-exchange { fill: #0a1f2e; stroke: #0277bd; }',
        '  .lane-retail { fill: #2a1500; stroke: #a55a00; }',
        '  .lane-quant { fill: #1f0a2e; stroke: #6a1b9a; }',
        '  .lane-onchain { fill: #002a2a; stroke: #00695c; }',
        '  .edge { stroke: #4caf50; stroke-width: 2; fill: none; }',
        '  .edge-dashed { stroke: #777; stroke-width: 1; fill: none; stroke-dasharray: 5,3; }',
        '  .edge-future { stroke: #b71c1c; stroke-width: 3; fill: none; stroke-dasharray: 8,4; }',
        '</style>',
        '<defs>',
        '  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" '
        '  orient="auto" markerUnits="strokeWidth">',
        '    <path d="M0,0 L0,6 L9,3 z" fill="#4caf50"/>',
        '  </marker>',
        '  <marker id="arrow-dashed" markerWidth="10" markerHeight="10" refX="9" refY="3" '
        '  orient="auto" markerUnits="strokeWidth">',
        '    <path d="M0,0 L0,6 L9,3 z" fill="#777"/>',
        '  </marker>',
        '  <marker id="arrow-future" markerWidth="10" markerHeight="10" refX="9" refY="3" '
        '  orient="auto" markerUnits="strokeWidth">',
        '    <path d="M0,0 L0,6 L9,3 z" fill="#b71c1c"/>',
        '  </marker>',
        '</defs>',
    ]

    cells = {}
    edges = []

    # First pass: collect all cells with relative geometry
    raw_cells = {}
    for cell in root.findall('.//mxCell'):
        cid = cell.get('id')
        if not cid or cid == '0' or cid == '1':
            continue

        style = parse_style(cell.get('style', ''))
        geo = cell.find('.//mxGeometry')
        if geo is None:
            continue

        x = float(geo.get('x', 0))
        y = float(geo.get('y', 0))
        w = float(geo.get('width', 100))
        h = float(geo.get('height', 40))

        raw_cells[cid] = {
            'id': cid,
            'value': cell.get('value', ''),
            'style': style,
            'rel_x': x,
            'rel_y': y,
            'w': w,
            'h': h,
            'parent': cell.get('parent', '1'),
            'is_edge': cell.get('edge') == '1',
            'is_swimlane': 'swimlane' in style,
            'is_text': style.get('text') == '1',
        }

        if raw_cells[cid]['is_edge']:
            raw_cells[cid]['src'] = cell.get('source', '')
            raw_cells[cid]['tgt'] = cell.get('target', '')

    # Second pass: resolve absolute positions (parents before children)
    resolved = set()
    for _ in range(10):  # max 10 iterations for nested swimlanes
        progress = False
        for cid, c in raw_cells.items():
            if cid in resolved:
                continue
            parent = c['parent']
            if parent == '1' or parent == '0' or parent not in raw_cells:
                c['abs_x'] = c['rel_x']
                c['abs_y'] = c['rel_y']
                resolved.add(cid)
                progress = True
            elif parent in resolved:
                p = raw_cells[parent]
                c['abs_x'] = c['rel_x'] + p['abs_x']
                c['abs_y'] = c['rel_y'] + p['abs_y']
                resolved.add(cid)
                progress = True
        if not progress:
            break

    cells = raw_cells
    edges = [c for c in cells.values() if c['is_edge']]

    # Draw swimlanes first (background)
    for cid, c in cells.items():
        if not c['is_swimlane']:
            continue
        x, y, w, h = c['abs_x'], c['abs_y'], c['w'], c['h']
        label = c['value'].replace('&#10;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

        lane_class = 'lane-done'
        if 'todo' in str(c['style']).lower() or 'dashed' in c['style']:
            lane_class = 'lane-todo'
        elif 'partial' in str(c['style']).lower() or '4D3A00' in str(c['style']):
            lane_class = 'lane-partial'
        elif '0D4D6B' in str(c['style']):
            lane_class = 'lane-exchange'
        elif '7A3D00' in str(c['style']):
            lane_class = 'lane-retail'
        elif '4D1A6B' in str(c['style']):
            lane_class = 'lane-quant'
        elif '004D4D' in str(c['style']):
            lane_class = 'lane-onchain'

        svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" class="{lane_class}" stroke-width="1.5"/>')
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="4" class="{lane_class}" stroke-width="1.5"/>')
        svg_parts.append(f'<text x="{x + w/2}" y="{y + 20}" class="lane-label" text-anchor="middle">{label}</text>')

    # Draw edges
    for e in edges:
        src = cells.get(e['src'])
        tgt = cells.get(e['tgt'])
        if not src or not tgt:
            continue

        sx, sy = src['abs_x'] + src['w']/2, src['abs_y'] + src['h']/2
        tx, ty = tgt['abs_x'] + tgt['w']/2, tgt['abs_y'] + tgt['h']/2

        style_str = e['style']
        is_dashed = style_str.get('dashed') == '1'
        is_future = '#B71C1C' in str(style_str.get('strokeColor', '')) or '#E53935' in str(style_str.get('strokeColor', ''))

        if is_future:
            cls = 'edge-future'
            marker = 'arrow-future'
        elif is_dashed:
            cls = 'edge-dashed'
            marker = 'arrow-dashed'
        else:
            cls = 'edge'
            marker = 'arrow'

        # Simple orthogonal path
        mid_x = (sx + tx) / 2
        path = f'M {sx},{sy} L {mid_x},{sy} L {mid_x},{ty} L {tx},{ty}'
        svg_parts.append(f'<path d="{path}" class="{cls}" marker-end="url(#{marker})"/>')

    # Draw nodes (non-swimlane, non-edge, non-text)
    for cid, c in cells.items():
        if c['is_swimlane'] or c['is_edge'] or c['is_text']:
            continue
        if c['parent'] != '1' and cells.get(c['parent'], {}).get('is_swimlane', False):
            pass  # child of swimlane, draw it

        x, y, w, h = c['abs_x'], c['abs_y'], c['w'], c['h']
        style = c['style']
        value = c['value'].replace('&#10;', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

        # Determine shape
        shape = 'rect'
        if style.get('rhombus') == '1':
            shape = 'diamond'
        elif style.get('triangle') == '1':
            shape = 'triangle'

        # Determine class
        fill = get_color(style, 'fillColor', '#2e7d32')
        stroke = get_color(style, 'strokeColor', '#4caf50')
        is_dashed = style.get('dashed') == '1'

        # Map fill color to class
        cls = 'done'
        if '#3A3A3A' in fill.upper() or '#3a3a3a' in fill:
            cls = 'todo'
        elif '#A67C00' in fill.upper() or '#a67c00' in fill:
            cls = 'partial'
        elif '#B71C1C' in fill.upper() or '#b71c1c' in fill:
            cls = 'me'
        elif '#0277BD' in fill.upper() or '#0277bd' in fill:
            cls = 'exchange'
        elif '#A55A00' in fill.upper() or '#a55a00' in fill:
            cls = 'retail'
        elif '#6A1B9A' in fill.upper() or '#6a1b9a' in fill:
            cls = 'quant'
        elif '#00695C' in fill.upper() or '#00695c' in fill:
            cls = 'onchain'
        elif '#0D47A1' in fill.upper() or '#0d47a1' in fill:
            cls = 'oracle'

        dash_attr = ' stroke-dasharray="5,3"' if is_dashed else ''
        font_weight = ' font-weight="bold"' if style.get('fontStyle') == '1' else ''

        if shape == 'diamond':
            cx, cy = x + w/2, y + h/2
            points = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
            svg_parts.append(f'<polygon points="{points}" class="{cls}" stroke-width="2"{dash_attr}/>')
        elif shape == 'triangle':
            points = f"{x+w/2},{y} {x+w},{y+h} {x},{y+h}"
            svg_parts.append(f'<polygon points="{points}" class="{cls}" stroke-width="2"{dash_attr}/>')
        else:
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="{cls}" stroke-width="2"{dash_attr}/>')

        # Draw label
        lines = value.split('\n')
        line_height = 13
        total_text_h = len(lines) * line_height
        start_y = y + h/2 - total_text_h/2 + 10
        for i, line in enumerate(lines):
            ly = start_y + i * line_height
            svg_parts.append(
                f'<text x="{x + w/2}" y="{ly}" class="node-label"{font_weight}>{line}</text>'
            )

    # Draw text cells (titles, legends)
    for cid, c in cells.items():
        if not c['is_text']:
            continue
        x, y, w, h = c['abs_x'], c['abs_y'], c['w'], c['h']
        value = c['value'].replace('&#10;', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&nbsp;', ' ')
        style = c['style']
        font_size = style.get('fontSize', '12')
        fill = get_color(style, 'fontColor', '#D1D4DC')
        align = style.get('align', 'center')
        anchor = 'middle' if align == 'center' else 'start' if align == 'left' else 'end'
        tx = x + w/2 if align == 'center' else x + 10 if align == 'left' else x + w - 10
        font_weight = 'bold' if style.get('fontStyle') == '1' else 'normal'

        lines = value.split('\n')
        line_height = int(font_size) + 2
        for i, line in enumerate(lines):
            ly = y + 20 + i * line_height
            svg_parts.append(
                f'<text x="{tx}" y="{ly}" font-size="{font_size}" fill="{fill}" '
                f'text-anchor="{anchor}" font-weight="{font_weight}">{line}</text>'
            )

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def main():
    drawio_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('organograma.drawio')
    output_dir = drawio_path.parent

    tree = ET.parse(drawio_path)
    root = tree.getroot()

    for diagram in root.findall('diagram'):
        name = diagram.get('name', 'diagram')
        safe_name = name.replace(' ', '-').lower()
        model = diagram.find('mxGraphModel')
        if model is None:
            continue

        w = int(model.get('pageWidth', 2000))
        h = int(model.get('pageHeight', 1400))

        model_xml = ET.tostring(model, encoding='unicode')
        svg = drawio_to_svg(model_xml, w, h)

        out_path = output_dir / f'{safe_name}.svg'
        out_path.write_text(svg, encoding='utf-8')
        print(f'Generated: {out_path} ({len(svg)} bytes)')

        # Also generate HTML wrapper
        html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
  body {{ margin: 0; background: #0B0E14; display: flex; justify-content: center; align-items: flex-start; min-height: 100vh; }}
  svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
{svg}
</body>
</html>'''
        html_path = output_dir / f'{safe_name}.html'
        html_path.write_text(html, encoding='utf-8')
        print(f'Generated: {html_path} ({len(html)} bytes)')


if __name__ == '__main__':
    main()
