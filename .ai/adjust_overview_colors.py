"""Apply contrast colors to the neon theme and Executive Overview only."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'PBIP/InsuranceDemoSM.Report'
source = Path('C:/Temp/Daiichi_Life_Premium_Neon_Theme.json')
theme = json.loads(source.read_text(encoding='utf-8-sig'))
theme.update(dataColors=['#38D9F5','#69B7FF','#B9A3FF','#55DCC3','#F5C76B','#F28BB8','#92B5DD','#FB7185'],
             good='#55DCC3', neutral='#F5C76B', bad='#FB7185', maximum='#38D9F5',
             center='#69B7FF', minimum='#44699B', null='#92A8C4',
             firstLevelElements='#F8FAFC', secondLevelElements='#D6E5F5',
             thirdLevelElements='#344766', fourthLevelElements='#A8BDD6',
             foreground='#F8FAFC', background='#08142C', secondaryBackground='#101E3B', tableAccent='#38D9F5')
for name, props in theme.get('textClasses', {}).items():
    props['color'] = '#D6E5F5' if name == 'label' else '#F8FAFC'
fill = lambda value: {'solid': {'color': value}}
styles = theme.setdefault('visualStyles', {}).setdefault('*', {}).setdefault('*', {})
styles.update(categoryAxis=[{'labelColor':fill('#D6E5F5')}],
              valueAxis=[{'labelColor':fill('#D6E5F5'),'gridlineColor':fill('#344766')}],
              legend=[{'labelColor':fill('#D6E5F5')}],
              title=[{'fontColor':fill('#F8FAFC')}],
              subTitle=[{'fontColor':fill('#A8BDD6')}])
report = json.loads((root/'definition/report.json').read_text(encoding='utf-8'))
resource = report['themeCollection']['customTheme']['name']
item = next(item for pack in report['resourcePackages'] for item in pack['items'] if item['name'] == resource)
target = root/'StaticResources/RegisteredResources'/item['path']
target.write_text(json.dumps(theme,indent=2)+'\n',encoding='utf-8')

def literal(value): return {'expr':{'Literal':{'Value':"'"+value+"'"}}}
def color(value): return {'solid':{'color':literal(value)}}
def set_color(objects, section, key, value):
    entries = objects.setdefault(section, [{'properties':{}}])
    for entry in entries: entry.setdefault('properties',{})[key] = color(value)

changed = 0
for path in (root/'definition/pages/overview/visuals').glob('*/visual.json'):
    doc = json.loads(path.read_text(encoding='utf-8'))
    if 'visual' not in doc: continue
    before = json.dumps(doc)
    visual = doc['visual']; objects = visual.setdefault('objects', {})
    containers = visual.setdefault('visualContainerObjects', {})
    for key, value in [('title','#F8FAFC'),('subTitle','#A8BDD6')]:
        if key in containers: set_color(containers,key,'fontColor',value)
    if visual['visualType'] == 'actionButton':
        set_color(objects,'text','fontColor','#38D9F5' if doc['name']=='overview_nav_overview' else '#F8FAFC')
    if doc['name'] in ['overview_trend','overview_funnel','overview_channels','overview_products']:
        for key in ['categoryAxis','valueAxis','legend']:
            set_color(objects,key,'labelColor','#D6E5F5')
        set_color(objects,'valueAxis','gridlineColor','#344766')
        set_color(objects,'labels','color','#F8FAFC')
        set_color(objects,'dataPoint','defaultColor','#69B7FF' if doc['name'] in ['overview_products','overview_funnel'] else '#38D9F5')
        if doc['name']=='overview_trend':
            set_color(objects,'valueAxis','secLabelColor','#D6E5F5')
            objects['dataPoint'].append({'selector':{'metadata':'Measure.New Policies'},'properties':{'fill':color('#F5C76B')}})
    if json.dumps(doc) != before:
        path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8'); changed += 1
print(f'Updated theme and colors in {changed} Overview visuals; background image, layout and queries preserved.')
print(target)
