"""Author the five-page PBIR report using only existing semantic-model fields."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'PBIP' / 'InsuranceDemoSM.Report'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
NAVY, TEAL, BLUE, MUTED, RED = '#142D4E', '#008C95', '#2874C7', '#62758A', '#C44F55'
D, C, P, A, F, L, S = ['gold_' + name for name in ['dim_date','dim_customer','dim_product','dim_agent','fact_policy','lead_conversion','lead_propensity']]
PAGES = [('overview','Executive Overview','Overview'), ('products','Policy & Product Performance','Products'), ('customers','Customer & Geography','Customers'), ('distribution','Distribution & Agent Performance','Distribution'), ('ai_leads','AI Lead Conversion','AI Leads')]
SERIAL = 0

def save(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def lit(value):
    value = "'" + value.replace("'", "''") + "'" if isinstance(value,str) else str(value).lower() if isinstance(value,bool) else str(value)+'D'
    return {'expr':{'Literal':{'Value':value}}}

def color(value): return {'solid':{'color':lit(value)}}
def obj(**properties): return [{'properties':properties}]
def column(table, name):
    return {'field':{'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':name}},'queryRef':table+'.'+name,'nativeQueryRef':name}
def measure(name):
    result = {'field':{'Measure':{'Expression':{'SourceRef':{'Entity':'Measure'}},'Property':name}},'queryRef':'Measure.'+name,'nativeQueryRef':name}
    if 'Premium' in name or 'Sum Assured' in name: result['format'] = '"SGD " #,0'
    return result
def persist(page, visual): save(f'definition/pages/{page}/visuals/{visual["name"]}/visual.json',visual)

def visual(page,key,kind,title,box,roles=None,objects=None):
    global SERIAL
    SERIAL += 1
    x,y,w,h=box
    value={'$schema':SCHEMA+'visualContainer/2.0.0/schema.json','name':page+'_'+key,
        'position':{'x':x,'y':y,'width':w,'height':h,'z':SERIAL,'tabOrder':SERIAL},
        'visual':{'visualType':kind,'objects':objects or {},'visualContainerObjects':{
            'title':obj(show=lit(bool(title)),text=lit(title),fontColor=color(NAVY),fontSize=lit(12),fontFamily=lit('Segoe UI'),bold=lit(True),titleWrap=lit(False)),
            'background':obj(show=lit(True),color=color('#FFFFFF'),transparency=lit(0)),
            'border':obj(show=lit(True),color=color('#E1E8EF'),radius=lit(10)),
            'visualHeader':obj(show=lit(True))}}}
    if roles: value['visual']['query']={'queryState':{role:{'projections':fields} for role,fields in roles.items()}}
    persist(page,value)
    return value

def text(page,key,value,box,size=12,foreground=NAVY,background=None):
    v=visual(page,key,'textbox','',box,objects={'general':obj(paragraphs=[{'textRuns':[{'value':value,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':foreground}}]}])})
    v['visual']['visualContainerObjects']['background']=obj(show=lit(bool(background)),color=color(background or '#FFFFFF'),transparency=lit(0 if background else 100))
    v['visual']['visualContainerObjects']['border']=obj(show=lit(False))
    persist(page,v)
    return v

def sort(page,v,field,descending=True):
    v['visual']['query']['sortDefinition']={'sort':[{'field':field['field'],'direction':'Descending' if descending else 'Ascending'}],'isDefaultSort':False}
    persist(page,v)
    return v

def chart(page,key,kind,title,box,roles,accent=TEAL):
    return visual(page,key,kind,title,box,roles,{
        'legend':obj(show=lit('Series' in roles),position=lit('Top'),fontSize=lit(9),labelColor=color(MUTED)),
        'categoryAxis':obj(show=lit(True),showAxisTitle=lit(False),fontSize=lit(9),labelColor=color(MUTED)),
        'valueAxis':obj(show=lit(True),showAxisTitle=lit(False),fontSize=lit(9),labelColor=color(MUTED),gridlineColor=color('#EEF2F6')),
        'dataPoint':obj(defaultColor=color(accent)),'labels':obj(show=lit(False))})

def slicer(page,key,title,field,x,sync=True):
    v=visual(page,key,'slicer',title,(x,138,376,60),{'Values':[field]}, {'data':obj(mode=lit('Dropdown')),'header':obj(show=lit(False)),'items':obj(fontSize=lit(10),fontColor=color(NAVY)),'selection':obj(selectAllCheckboxEnabled=lit(True),singleSelect=lit(False))})
    if sync: v['visual']['syncGroup']={'groupName':field['queryRef'],'fieldChanges':True,'filterChanges':True}
    persist(page,v)
    return v

def cards(page,names):
    width=(1552-(len(names)-1)*12)/len(names)
    for i,name in enumerate(names):
        visual(page,'kpi_'+str(i),'card',name,(24+i*(width+12),214,width,98),{'Values':[measure(name)]},{'labels':obj(color=color(RED if name=='Lapse Rate' else TEAL if page=='ai_leads' else NAVY),fontSize=lit(26),labelDisplayUnits=lit(0),labelPrecision=lit(1 if any(x in name for x in ['Rate','Probability','Attainment']) else 0)),'categoryLabels':obj(show=lit(False))})

def table(page,key,title,box,fields,matrix=False):
    return visual(page,key,'pivotTable' if matrix else 'tableEx',title,box,{'Rows':fields[:2],'Values':fields[2:]} if matrix else {'Values':fields},{
        'columnHeaders':obj(fontColor=color(NAVY),backColor=color('#EDF4F8'),fontSize=lit(10),bold=lit(True),wordWrap=lit(True)),
        'rowHeaders':obj(fontSize=lit(10),stepped=lit(True)),
        'values':obj(fontSize=lit(10),fontColorPrimary=color(NAVY),backColorPrimary=color('#FFFFFF'),backColorSecondary=color('#F5F8FB'),wordWrap=lit(False)),
        'grid':obj(gridVertical=lit(False),gridHorizontal=lit(True),gridHorizontalColor=color('#EDF1F5'),rowPadding=lit(6)),
        'total':obj(totals=lit(False))})

save('definition/version.json',{'$schema':SCHEMA+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
save('definition/pages/pages.json',{'$schema':SCHEMA+'pagesMetadata/1.0.0/schema.json','pageOrder':[p[0] for p in PAGES],'activePageName':'overview'})
save('StaticResources/RegisteredResources/InsuranceExecutive.json',{'name':'Insurance Executive','dataColors':[TEAL,BLUE,'#709EBC','#D4A348','#547093','#89BDBC'],'background':'#FFFFFF','foreground':NAVY,'tableAccent':TEAL,'good':TEAL,'neutral':'#D4A348','bad':RED,'textClasses':{k:{'fontFace':'Segoe UI','fontSize':size,'color':NAVY} for k,size in [('title',12),('label',10),('callout',28),('header',12)]}})
save('definition/report.json',{'$schema':SCHEMA+'report/2.0.0/schema.json','themeCollection':{'customTheme':{'name':'InsuranceExecutive','reportVersionAtImport':'2.0','type':'RegisteredResources'}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'InsuranceExecutive','path':'InsuranceExecutive.json','type':'CustomTheme'}]}],'objects':{'outspacePane':obj(expanded=lit(False))}})
for page,title,_ in PAGES:
    save(f'definition/pages/{page}/page.json',{'$schema':SCHEMA+'page/1.0.0/schema.json','name':page,'displayName':title,'displayOption':'FitToPage','width':1600,'height':900,'objects':{'background':obj(color=color('#F3F6FA'),transparency=lit(0))}})
    text(page,'brand','Life Insurance Growth & Customer Analytics',(24,14,1400,34),21)
    text(page,'subtitle','Synthetic Azure + Fabric + Power BI Demonstration',(24,51,1400,24),10,MUTED)
    text(page,'title',title,(24,90,720,40),22)
    for i,(destination,_,label) in enumerate(PAGES):
        v=text(page,'nav_'+destination,label,(804+i*156,89,146,36),11,'#FFFFFF' if destination==page else NAVY,(TEAL if page=='ai_leads' else NAVY) if destination==page else '#E6EDF4')
        v['visual']['visualContainerObjects']['visualLink']=obj(show=lit(True),type=lit('PageNavigation'),navigationSection=lit(destination))
        persist(page,v)
    text(page,'footer','Fabric notebook ML scores  |  Select High propensity to focus the priority queue  |  SGD' if page=='ai_leads' else 'Synthetic demonstration data  |  Planning-area geography  |  All monetary values in SGD',(24,874,1450,22),9,MUTED)

pg='overview'
for key,title,field,x in [('date','Application month',column(D,'YearMonth'),24),('region','Customer region',column(C,'Region'),416),('product','Product family',column(P,'ProductFamily'),808),('channel','Distribution channel',column(A,'DistributionChannel'),1200)]: slicer(pg,key,title,field,x)
cards(pg,['Active Policies','Annual Premium','New Policies','Renewal Rate','Conversion Rate','Lapse Rate'])
sort(pg,chart(pg,'trend','lineClusteredColumnComboChart','Monthly premium (SGD) & new policies',(24,330,1000,254),{'Category':[column(D,'YearMonth')],'Y':[measure('Annual Premium')],'Y2':[measure('New Policies')]}),column(D,'YearMonth'),False)
chart(pg,'funnel','funnel','Lead funnel - current stage counts',(1040,330,536,254),{'Category':[column(L,'LeadStage')],'Y':[measure('Total Leads')]},BLUE)
sort(pg,chart(pg,'channels','barChart','Channel contribution - annual premium (SGD)',(24,602,600,254),{'Category':[column(A,'DistributionChannel')],'Y':[measure('Annual Premium')]}),measure('Annual Premium'))
sort(pg,chart(pg,'products','barChart','Product mix - annual premium (SGD)',(640,602,936,254),{'Category':[column(P,'ProductFamily')],'Y':[measure('Annual Premium')]},BLUE),measure('Annual Premium'))

pg='products'
for key,title,field,x in [('date','Application month',column(D,'YearMonth'),24),('product','Product family',column(P,'ProductFamily'),416),('channel','Distribution channel',column(A,'DistributionChannel'),808)]: slicer(pg,key,title,field,x)
v=slicer(pg,'time','Time calculation',column('Time Intelligence','Time Calculation'),1200,False)
v['visual']['objects']['selection']=obj(singleSelect=lit(True));persist(pg,v)
cards(pg,['Total Policies','Average Premium','Total Sum Assured','Renewal Rate','Claim Rate','Avg Days to Issue'])
table(pg,'matrix','Product performance - SGD and rates',(24,330,1010,292),[column(P,'ProductFamily'),column(P,'ProductName')]+list(map(measure,['Total Policies','Annual Premium','Average Premium','Renewal Rate','Lapse Rate','Claim Rate'])),True)
chart(pg,'status','donutChart','Policy status',(1050,330,526,292),{'Category':[column(F,'PolicyStatus')],'Y':[measure('Total Policies')]})
sort(pg,chart(pg,'trend','lineChart','Monthly premium by product family (SGD)',(24,640,800,216),{'Category':[column(D,'YearMonth')],'Series':[column(P,'ProductFamily')],'Y':[measure('Annual Premium')]}),column(D,'YearMonth'),False)
chart(pg,'scatter','scatterChart','Premium vs cover - bubble size = policies',(840,640,736,216),{'Category':[column(P,'ProductName')],'Series':[column(P,'ProductFamily')],'X':[measure('Average Premium')],'Y':[measure('Average Sum Assured')],'Size':[measure('Total Policies')]})

pg='customers'
for key,title,field,x in [('date','Application month',column(D,'YearMonth'),24),('region','Customer region',column(C,'Region'),416),('product','Product family',column(P,'ProductFamily'),808),('segment','Customer segment',column(C,'CustomerSegment'),1200)]: slicer(pg,key,title,field,x)
cards(pg,['Total Customers','Total Policies','Annual Premium','Lapse Rate'])
chart(pg,'map','map','Singapore - planning-area policy footprint',(24,330,624,334),{'Category':[column(C,'PlanningArea')],'Latitude':[column(C,'PlanningAreaLatitude')],'Longitude':[column(C,'PlanningAreaLongitude')],'Size':[measure('Total Policies')],'Tooltips':[measure('Total Customers'),measure('Annual Premium'),measure('Renewal Rate')]})
chart(pg,'segments','barChart','Customer segments',(664,330,448,254),{'Category':[column(C,'CustomerSegment')],'Y':[measure('Total Customers')]})
chart(pg,'age','hundredPercentStackedBarChart','Age band & product mix',(1128,330,448,254),{'Category':[column(C,'AgeBand')],'Series':[column(P,'ProductFamily')],'Y':[measure('Total Policies')]})
chart(pg,'income','clusteredColumnChart','Premium by income band (SGD)',(664,602,448,254),{'Category':[column(C,'IncomeBandSGD')],'Y':[measure('Annual Premium')]},BLUE)
chart(pg,'retention','barChart','Lapse rate by region',(1128,602,448,254),{'Category':[column(C,'Region')],'Y':[measure('Lapse Rate')]},RED)
table(pg,'existing','Existing customer = True - new = False',(24,682,624,174),[column(C,'ExistingCustomerFlag'),measure('Total Customers'),measure('Total Policies'),measure('Average Premium')])

pg='distribution'
for key,title,field,x in [('date','Application month',column(D,'YearMonth'),24),('region','Branch region',column(A,'Region'),416),('channel','Distribution channel',column(A,'DistributionChannel'),808),('grade','Agent grade',column(A,'AgentGrade'),1200)]: slicer(pg,key,title,field,x)
cards(pg,['Active Agents','Premium per Agent','Policies per Agent','Conversion Rate','Target Attainment','Avg First Response Hours'])
sort(pg,table(pg,'leaderboard','Agent leaderboard - annual premium (SGD)',(24,330,1010,292),[column(A,'AgentName'),column(A,'DistributionChannel')]+list(map(measure,['Annual Premium','Total Policies','Conversion Rate','Renewal Rate','Target Attainment']))),measure('Annual Premium'))
chart(pg,'scatter','scatterChart','Conversion vs premium - size = policies',(1050,330,526,292),{'Category':[column(A,'AgentName')],'Series':[column(A,'DistributionChannel')],'X':[measure('Conversion Rate')],'Y':[measure('Annual Premium')],'Size':[measure('Total Policies')]})
chart(pg,'stages','barChart','Lead stage by channel - current counts',(24,640,504,216),{'Category':[column(L,'DistributionChannel')],'Series':[column(L,'LeadStage')],'Y':[measure('Total Leads')]})
chart(pg,'target','barChart','Target attainment by channel',(544,640,504,216),{'Category':[column(A,'DistributionChannel')],'Y':[measure('Target Attainment')]},BLUE)
chart(pg,'branches','barChart','Branch region premium (SGD)',(1064,640,512,216),{'Category':[column(A,'Region')],'Y':[measure('Annual Premium')]})

pg='ai_leads'
slicer(pg,'band','Propensity band - select High to prioritize',column(S,'PropensityBand'),24,False)
slicer(pg,'region','Lead region',column(S,'Region'),416,False)
slicer(pg,'product','Product family',column(P,'ProductFamily'),808)
slicer(pg,'channel','Distribution channel',column(A,'DistributionChannel'),1200)
cards(pg,['Open Leads','High Propensity Leads','Avg Conversion Probability','Expected Conversions','Potential Premium - High Propensity'])
count={'field':{'Aggregation':{'Expression':column(S,'LeadID')['field'],'Function':2}},'queryRef':'CountDistinct(gold_lead_propensity.LeadID)','nativeQueryRef':'Scored leads','displayName':'Scored leads'}
chart(pg,'bands','clusteredColumnChart','Propensity bands - scored open leads',(24,330,360,238),{'Category':[column(S,'PropensityBand')],'Y':[count]})
chart(pg,'probability','scatterChart','Probability distribution - one dot per lead',(400,330,400,238),{'Category':[column(S,'LeadID')],'X':[measure('Avg Conversion Probability')],'Y':[column(S,'DaysSinceLeadCreated')],'Tooltips':[column(S,'PropensityBand')]},BLUE)
chart(pg,'channel_high','barChart','High propensity by channel',(816,330,360,238),{'Category':[column(S,'DistributionChannel')],'Y':[measure('High Propensity Leads')]})
chart(pg,'product_high','barChart','High propensity by product',(1192,330,384,238),{'Category':[column(S,'ProductInterest')],'Y':[measure('High Propensity Leads')]})
premium=column(S,'EstimatedAnnualPremiumSGD');premium.update(displayName='Est. premium (SGD)',format='"SGD " #,0')
sort(pg,table(pg,'priority','Sales priority queue - highest probability first',(24,586,1552,270),[column(S,'LeadID'),column(S,'ProductInterest'),column(S,'DistributionChannel'),column(S,'Region'),premium,measure('Avg Conversion Probability'),column(S,'PropensityBand'),column(S,'DaysSinceLeadCreated'),column(S,'AgentKey')]),measure('Avg Conversion Probability'))
print(f'Authored {len(PAGES)} report pages and {SERIAL} visual containers.')
