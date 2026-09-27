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
    if name == 'products_status':
        visual['objects']['legend'] = props({'show': literal(True), 'position': literal('Right'), 'fontSize': literal(10)})
    if name in ['products_matrix', 'distribution_leaderboard', 'ai_leads_priority']:
        visual['objects']['values'] = [v for v in visual['objects']['values'] if 'selector' not in v]
        if name == 'products_matrix':
            conditional(visual, 'Lapse Rate', .1, '#FBE6E7', '#FFFFFF')
            conditional(visual, 'Renewal Rate', .8, '#DEF2EC', '#FFFFFF')
        elif name == 'distribution_leaderboard':
            conditional(visual, 'Target Attainment', 1, '#DEF2EC', '#FFF3DA')
        else:
            conditional(visual, 'Avg Conversion Probability', .65, '#DEF2EC', '#FFFFFF')
            rule = visual['objects']['values'][-1]['properties']['backColor']['solid']['color']['expr']['Conditional']
            rule['Cases'].append({
                'Condition': {'Comparison': {'ComparisonKind': 2,
                    'Left': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Measure'}}, 'Property': 'Avg Conversion Probability'}},
                    'Right': {'Literal': {'Value': '0.35D'}}}},
                'Value': {'Literal': {'Value': "'#FFF3DA'"}}
            })
    if json.dumps(report) != before:
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        changed += 1
print(f'Polished {changed} visual files.')
