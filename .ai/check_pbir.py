"""Lightweight PBIR JSON/schema, field-reference and navigation checks."""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen
import jsonschema

ROOT = Path(__file__).resolve().parents[1] / 'PBIP'
REPORT = ROOT / 'InsuranceDemoSM.Report'
members = {}
for path in (ROOT / 'InsuranceDemoSM.SemanticModel/definition/tables').glob('*.tmdl'):
    source = path.read_text(encoding='utf-8-sig')
    table = re.search(r'^table (.+)$', source, re.M).group(1).strip("'")
    members[table] = {(kind, quoted or simple) for kind, quoted, simple in re.findall(r"^\t(column|measure) (?:'([^']+)'|([^\s=]+))", source, re.M)}

@lru_cache(None)
def fetch(uri):
    # Microsoft's embedded schema $id uses a dot, while the published URL uses a hyphen.
    uri = uri.replace('schema.embedded.json', 'schema-embedded.json')
    with urlopen(uri, timeout=30) as response:
        schema = json.load(response)
        schema['$id'] = uri
        return schema

def references(value):
    if isinstance(value, dict):
        for kind in ['Column', 'Measure']:
            if kind in value and 'Property' in value[kind]:
                field = value[kind]
                entity = field.get('Expression', {}).get('SourceRef', {}).get('Entity')
                if entity:
                    assert (kind.lower(), field['Property']) in members[entity], (entity, field['Property'])
        for child in value.values(): references(child)
    elif isinstance(value, list):
        for child in value: references(child)

pages = json.loads((REPORT / 'definition/pages/pages.json').read_text())['pageOrder']
assert len(pages) == len(set(pages)) == 5
visuals = 0
for path in REPORT.glob('definition/**/*.json'):
    content = json.loads(path.read_text(encoding='utf-8'))
    url = content['$schema']
    schema = fetch(url)
    resolver = jsonschema.RefResolver(base_uri=url, referrer=schema, handlers={'https':fetch})
    jsonschema.Draft7Validator(schema, resolver=resolver).validate(content)
    references(content)
    if path.name == 'visual.json':
        visuals += 1
        pos = content['position']
        assert 0 <= pos['x'] and pos['x'] + pos['width'] <= 1600.01
        assert 0 <= pos['y'] and pos['y'] + pos['height'] <= 900.01
        link = content.get('visual', {}).get('visualContainerObjects', {}).get('visualLink')
        if link:
            target = link[0]['properties']['navigationSection']['expr']['Literal']['Value'].strip("'")
            assert target in pages, target
assert visuals == 116, visuals
print(f'PASS: {len(pages)} pages, {visuals} visuals; Microsoft JSON schemas, TMDL fields, navigation and canvas bounds.')
