"""Apply consistent formatting to the authored PBIR visual definitions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'PBIP' / 'InsuranceDemoSM.Report'

NEON = ['#38D9F5', '#F05CFF', '#F5C76B', '#55DCC3', '#69B7FF', '#FB7185',
        '#B9A3FF', '#34D399', '#FF9F6E', '#7DD3FC', '#C084FC', '#F472B6']

# Stable business colors make the same option recognizable on every page.
VALUE_COLORS = {
    'Agency': '#38D9F5', 'Bancassurance': '#F05CFF', 'Broker / IFA': '#F5C76B',
    'Digital': '#55DCC3', 'Direct': '#B9A3FF',
    'Central': '#38D9F5', 'East': '#55DCC3', 'North': '#69B7FF',
    'North-East': '#F05CFF', 'West': '#F5C76B',
    'Critical Illness': '#FB7185', 'Endowment / Savings': '#F5C76B',
    'Investment Linked': '#F05CFF', 'Retirement / Annuity': '#B9A3FF',
    'Term Life': '#38D9F5', 'Whole Life': '#55DCC3',
    'Application': '#38D9F5', 'Appointment': '#F05CFF', 'Contacted': '#F5C76B',
    'Lost': '#FB7185', 'New': '#69B7FF', 'Qualified': '#B9A3FF',
    'Quote': '#55DCC3', 'Won': '#34D399',
    'Active': '#55DCC3', 'Cancelled': '#92A8C4', 'Claimed': '#F05CFF',
    'Lapsed': '#FB7185', 'Matured': '#F5C76B',
    'High': '#55DCC3', 'Medium': '#F5C76B', 'Low': '#FB7185',
    'Affluent': '#F5C76B', 'Emerging': '#38D9F5', 'High Value': '#F05CFF', 'Mass': '#69B7FF',
    '18-29': '#38D9F5', '30-39': '#55DCC3', '40-49': '#F5C76B',
    '50-59': '#F05CFF', '60+': '#B9A3FF',
    'Below 40k': '#69B7FF', '40k-79k': '#38D9F5', '80k-119k': '#55DCC3',
    '120k-199k': '#F5C76B', '200k+': '#F05CFF',
    'Balanced Wealth Link': NEON[0], 'Critical Care Protect': NEON[5],
    'Early Stage Guard': NEON[2], 'Education Milestone': NEON[3],
    'Family Shield Term': NEON[4], 'Future Builder Savings': NEON[1],
    'Golden Years Annuity': NEON[6], 'Growth Navigator': NEON[7],
    'Legacy Plus': NEON[8], 'Lifetime Heritage': NEON[9],
    'RetireIncome Select': NEON[10], 'Secure Horizon Term': NEON[11],
}

PROPERTY_VALUES = {
    'DistributionChannel': ['Agency', 'Bancassurance', 'Broker / IFA', 'Digital', 'Direct'],
    'Region': ['Central', 'East', 'North', 'North-East', 'West'],
    'ProductFamily': ['Critical Illness', 'Endowment / Savings', 'Investment Linked',
                      'Retirement / Annuity', 'Term Life', 'Whole Life'],
    'LeadStage': ['Application', 'Appointment', 'Contacted', 'Lost', 'New', 'Qualified', 'Quote', 'Won'],
    'PolicyStatus': ['Active', 'Cancelled', 'Claimed', 'Lapsed', 'Matured'],
    'PropensityBand': ['High', 'Medium', 'Low'],
    'CustomerSegment': ['Affluent', 'Emerging', 'High Value', 'Mass'],
    'AgeBand': ['18-29', '30-39', '40-49', '50-59', '60+'],
    'IncomeBandSGD': ['Below 40k', '40k-79k', '80k-119k', '120k-199k', '200k+'],
    'ProductInterest': ['Balanced Wealth Link', 'Critical Care Protect', 'Early Stage Guard',
                        'Education Milestone', 'Family Shield Term', 'Future Builder Savings',
                        'Golden Years Annuity', 'Growth Navigator', 'Legacy Plus',
                        'Lifetime Heritage', 'RetireIncome Select', 'Secure Horizon Term'],
}

CHART_TYPES = {
    'barChart', 'clusteredBarChart', 'stackedBarChart', 'hundredPercentStackedBarChart',
    'columnChart', 'clusteredColumnChart', 'stackedColumnChart',
    'hundredPercentStackedColumnChart', 'lineChart', 'lineClusteredColumnComboChart',
    'lineStackedColumnComboChart', 'scatterChart', 'pieChart', 'donutChart',
    'funnel', 'treemap', 'map', 'filledMap'
}

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

def category_column(query_state):
    projections = query_state.get('Category', {}).get('projections', [])
    if not projections:
        return None
    return projections[0].get('field', {}).get('Column')

def category_color_entry(entity, property_name, value, value_color):
    return {
        'properties': {'fill': color(value_color)},
        'selector': {'data': [{'scopeId': {'Comparison': {
            'ComparisonKind': 0,
            'Left': {'Column': {'Expression': {'SourceRef': {'Entity': entity}},
                                'Property': property_name}},
            'Right': {'Literal': {'Value': "'" + value.replace("'", "''") + "'"}}
        }}}]}
    }

def apply_neon_series_colors(visual, name):
    if visual.get('visualType') not in CHART_TYPES:
        return
    query_state = visual.get('query', {}).get('queryState', {})

    # The probability scatter should use propensity as its color series, not only as a tooltip.
    if name == 'ai_leads_probability' and 'Tooltips' in query_state:
        query_state['Series'] = query_state.pop('Tooltips')

    objects = visual.setdefault('objects', {})
    current = objects.get('dataPoint', [])
    if query_state.get('Series', {}).get('projections'):
        # An unscoped defaultColor overrides the theme palette and makes every legend item cyan.
        selected = [item for item in current if item.get('selector')]
        if selected:
            objects['dataPoint'] = selected
        else:
            objects.pop('dataPoint', None)
        return

    category = category_column(query_state)
    if not category or category.get('Property') not in PROPERTY_VALUES:
        return

    entity = category.get('Expression', {}).get('SourceRef', {}).get('Entity')
    property_name = category.get('Property')
    if not entity:
        return

    # Preserve measure-level settings, replace the global cyan with explicit category colors.
    selected = [item for item in current if item.get('selector', {}).get('metadata')]
    entries = [{'properties': {'showAllDataPoints': literal(True)}}] + selected
    for value in PROPERTY_VALUES[property_name]:
        entries.append(category_color_entry(entity, property_name, value, VALUE_COLORS[value]))
    objects['dataPoint'] = entries

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
    apply_neon_series_colors(visual, name)
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
