"""Apply consistent formatting to the authored PBIR visual definitions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'PBIP' / 'InsuranceDemoSM.Report'

def literal(value):
    if isinstance(value, str):
        value = "'" + value.replace("'", "''") + "'"
    elif isinstance(value, bool):
        value = str(value).lower()
    else:
        value = str(value) + 'D'
    return {'expr': {'Literal': {'Value': value}}}

def color(value):
    return {'solid': {'color': literal(value)}}

def props(value):
    return [{'properties': value}]

def conditional(visual, measure, threshold, high, low):
    expression = {'Measure': {'Expression': {'SourceRef': {'Entity': 'Measure'}}, 'Property': measure}}
    expression = {'expr': {'Conditional': {
        'Cases': [{'Condition': {'Comparison': {
            'ComparisonKind': 2, 'Left': expression, 'Right': {'Literal': {'Value': str(threshold) + 'D'}}
        }}, 'Value': {'Literal': {'Value': "'" + high + "'"}}}],
        'DefaultValue': {'Literal': {'Value': "'" + low + "'"}}
    }}}
    visual['objects']['values'].append({
        'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}], 'metadata': 'Measure.' + measure},
        'properties': {'backColor': {'solid': {'color': expression}}}
    })

changed = 0
for path in ROOT.glob('definition/pages/*/visuals/*/visual.json'):
    report = json.loads(path.read_text(encoding='utf-8'))
    if 'visual' not in report:
        continue
    before = json.dumps(report)
    visual = report['visual']
    page = path.parents[2].name
    name = report['name']
    if visual['visualType'] not in ['textbox', 'actionButton', 'card', 'slicer']:
        visual['visualContainerObjects']['title'][0]['properties'].update(fontSize=literal(11), titleWrap=literal(True))
    if '_nav_' in name and visual['visualType'] == 'textbox':
        target = name.split('_nav_')[1]
        label = visual['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value']
        selected = page == target
        visual['visualType'] = 'actionButton'
        visual['objects'] = {
            'text': props({'show': literal(True), 'text': literal(label), 'fontSize': literal(11),
                           'fontFamily': literal('Segoe UI'), 'fontColor': color('#FFFFFF' if selected else '#142D4E'),
                           'horizontalAlignment': literal('center'), 'verticalAlignment': literal('middle')}),
            'icon': props({'show': literal(False)}),
            'outline': props({'show': literal(False)}),
            'fill': props({'show': literal(True), 'fillColor': color(('#008C95' if page == 'ai_leads' else '#142D4E') if selected else '#E6EDF4')})
        }
    if visual['visualType'] == 'card':
        title = visual['visualContainerObjects']['title'][0]['properties']
        title.update(fontSize=literal(10), titleWrap=literal(True))
        measure = visual['query']['queryState']['Values']['projections'][0]['nativeQueryRef']
        if measure in ['Annual Premium', 'Total Sum Assured', 'Potential Premium - High Propensity']:
            visual['objects']['labels'][0]['properties'].update(labelDisplayUnits=literal(1000000), labelPrecision=literal(2))
    if visual['visualType'] in ['tableEx', 'pivotTable']:
        table_objects = visual['objects']
        table_objects.setdefault('columnHeaders', props({}))[0]['properties'].update(
            fontColor=color('#F8FAFC'),
            backColor=color('#123B63'),
            fontSize=literal(10),
            bold=literal(True),
            wordWrap=literal(True),
        )
        base_values = next((item for item in table_objects.setdefault('values', props({})) if 'selector' not in item), None)
        if base_values is None:
            base_values = {'properties': {}}
            table_objects['values'].insert(0, base_values)
        base_values['properties'].update(
            fontColorPrimary=color('#EAF4FF'),
            fontColorSecondary=color('#D6E5F5'),
            backColorPrimary=color('#0B1D3A'),
            backColorSecondary=color('#10294C'),
            fontSize=literal(10),
            wordWrap=literal(False),
        )
        table_objects.setdefault('grid', props({}))[0]['properties'].update(
            gridVertical=literal(False),
            gridHorizontal=literal(True),
            gridHorizontalColor=color('#27466F'),
            rowPadding=literal(6),
        )
        if visual['visualType'] == 'pivotTable':
            table_objects.setdefault('rowHeaders', props({}))[0]['properties'].update(
                fontColor=color('#EAF4FF'),
                backColor=color('#0B1D3A'),
                fontSize=literal(10),
                stepped=literal(True),
            )
            table_objects.setdefault('total', props({}))[0]['properties'].update(
                fontColor=color('#F8FAFC'),
                backColor=color('#08142C'),
                bold=literal(True),
            )
    if name == 'products_status':
        visual['objects']['legend'] = props({'show': literal(True), 'position': literal('Right'), 'fontSize': literal(10)})
    if name in ['products_matrix', 'distribution_leaderboard', 'ai_leads_priority']:
        visual['objects']['values'] = [v for v in visual['objects']['values'] if 'selector' not in v]
        if name == 'products_matrix':
            conditional(visual, 'Lapse Rate', .1, '#5A2037', '#0B1D3A')
            conditional(visual, 'Renewal Rate', .8, '#0F4A43', '#0B1D3A')
        elif name == 'distribution_leaderboard':
            conditional(visual, 'Target Attainment', 1, '#0F4A43', '#4A3917')
        else:
            conditional(visual, 'Avg Conversion Probability', .65, '#0F4A43', '#0B1D3A')
            rule = visual['objects']['values'][-1]['properties']['backColor']['solid']['color']['expr']['Conditional']
            rule['Cases'].append({
                'Condition': {'Comparison': {'ComparisonKind': 2,
                    'Left': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Measure'}}, 'Property': 'Avg Conversion Probability'}},
                    'Right': {'Literal': {'Value': '0.35D'}}}},
                'Value': {'Literal': {'Value': "'#4A3917'"}}
            })
    if json.dumps(report) != before:
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        changed += 1
print(f'Polished {changed} visual files.')
