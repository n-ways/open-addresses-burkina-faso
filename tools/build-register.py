#!/usr/bin/env python3
"""The frozen register of Burkina Faso's code areas, at first issue (engine/SPEC.md 2.4, 6.4).

  python3 tools/build-register.py <work> [--freeze]

1. model/stats/area-compounds.csv takes the compounds actually grouped (tools/area-compounds.py), and
   tools/name-ranges.py sizes and places every name's blocks on them (SPEC 2.4) and writes the plate
   names into model/areas/register.json.
2. Every area's numbering frame is the box of its footprints' centres (<work>/area-boxes.json,
   tools/assign-areas.py), widened by 0.0005 degrees (about 55 m) on every side; an area with no
   footprint today gets its place point widened the same way. Frozen with the blocks.
3. Writes engine/data/register.json (what the engines load: communes with their machine code and spot
   frame, every area with its key, rank, plate and official names, name id, digits, blocks and frame;
   the names with their range and spare; the aliases), engine/data/units.json (the commune outlines)
   and model/stats/register.json (the counts in the papers).
"""
import collections, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
work = os.path.abspath(sys.argv[1])
freeze = '--freeze' in sys.argv
with open(os.path.join(REPO, 'model', 'stats', 'area-compounds.csv'), 'w') as f:
    subprocess.run([sys.executable, os.path.join(HERE, 'area-compounds.py'), work], stdout=f, check=True)
r = subprocess.run([sys.executable, os.path.join(HERE, 'name-ranges.py')], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr[-3000:])
counts = json.load(open(os.path.join(work, 'area-counts.json')))
boxes = json.load(open(os.path.join(work, 'area-boxes.json')))
reg = json.load(open(os.path.join(REPO, 'model', 'areas', 'register.json'), encoding='utf-8'))
nr = json.load(open(os.path.join(REPO, 'model', 'areas', 'name-ranges.json'), encoding='utf-8'))
frames = json.load(open(os.path.join(REPO, 'model', 'units', 'frames.json'), encoding='utf-8'))
PAD = 0.0005

by_area = {}
for key, e in nr['names'].items():
    for pc, ix, _c, lo, hi in e['blocks']:
        by_area.setdefault((pc, ix), (key, e, []))[2].append([lo, hi])
    for pc, ix in e['areasWithoutCompounds']:
        by_area.setdefault((pc, ix), (key, e, []))
areas, missing = [], []
for pc in sorted(reg):
    for v in reg[pc]['villages']:
        k = f"{pc}-{v['index']}"
        hit = by_area.get((pc, v['index']))
        if hit is None:
            if counts.get(k):
                missing.append(k)
            continue
        key, e, blocks = hit
        b = boxes.get(k) or [v['lon'], v['lat'], v['lon'], v['lat']]
        a = {'key': k, 'postcode': pc, 'index': v['index'], 'name': v.get('plateName', v['officialName']),
             'officialName': v['officialName'], 'nameId': e['id'], 'nameKey': key, 'digits': e['digits'], 'blocks': blocks,
             'frame': [round(b[0] - PAD, 6), round(b[1] - PAD, 6), round(b[2] + PAD, 6), round(b[3] + PAD, 6)],
             'point': [v['lon'], v['lat']], 'compounds': counts.get(k, 0)}
        if v.get('needsCouncilChoice'):
            a['provisional'] = True
            a['plateCandidates'] = v.get('plateCandidates', [])
        areas.append(a)
if missing:
    sys.exit(f'{len(missing)} areas with compounds have no name block, e.g. {missing[:5]}')
for i, a in enumerate(areas):
    a['id'] = i + 1
communes = [{'postcode': pc, 'name': c['commune'], 'pcode': c['pcode'], **{f: frames[pc][f] for f in ('lon0', 'lat0', 'latc', 'dx', 'dy')}}
            for pc, c in sorted(reg.items())]
out = {'about': 'N-Ways Addressing for Burkina Faso: the frozen register of code areas (engine/SPEC.md 2.4). Built by tools/build-register.py.',
       'frozen': freeze, 'builtAt': datetime.date.today().isoformat(), 'communes': communes, 'areas': areas,
       'names': [{'key': k, 'id': e['id'], 'plateName': e['plateName'], 'digits': e['digits'], 'range': e['range'], 'spareFrom': e['spareFrom']}
                 for k, e in sorted(nr['names'].items(), key=lambda kv: kv[1]['id'])],
       'aliases': nr['aliasKeys']}
os.makedirs(os.path.join(REPO, 'engine', 'data'), exist_ok=True)
json.dump(out, open(os.path.join(REPO, 'engine', 'data', 'register.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
pcode_pc = {c['pcode']: pc for pc, c in reg.items()}
units = {}
for f in json.load(open(os.path.join(REPO, 'model', 'units', 'communes.geojson'), encoding='utf-8'))['features']:
    g = f['geometry']
    polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    units[pcode_pc[f['properties']['pcode']]] = [[[[round(x, 6), round(y, 6)] for x, y in ring] for ring in poly] for poly in polys]
json.dump(units, open(os.path.join(REPO, 'engine', 'data', 'units.json'), 'w'), separators=(',', ':'))

dig = collections.Counter()
for a in areas:
    dig[a['digits']] += a['compounds']
keyc = collections.Counter(a['nameKey'] for a in areas)
stats = {'areas': len(areas), 'areasWithCompounds': sum(1 for a in areas if a['compounds']),
         'compounds': sum(a['compounds'] for a in areas),
         'ouagadougou': {'areas': sum(1 for a in areas if a['postcode'] == '10000'), 'compounds': sum(a['compounds'] for a in areas if a['postcode'] == '10000')},
         'boboDioulasso': {'areas': sum(1 for a in areas if a['postcode'] == '90000'), 'compounds': sum(a['compounds'] for a in areas if a['postcode'] == '90000')},
         'nameKeys': len(keyc), 'sharedNames': sum(1 for v in keyc.values() if v > 1),
         'areasInSharedNames': sum(v for v in keyc.values() if v > 1),
         'areasByDigits': dict(sorted(collections.Counter(a['digits'] for a in areas if a['compounds']).items())),
         'compoundsByDigits': dict(sorted(dig.items())),
         'provisionalNames': sum(1 for a in areas if a.get('provisional')),
         'compoundsWithProvisionalNames': sum(a['compounds'] for a in areas if a.get('provisional')),
         'largestArea': max(({'key': a['key'], 'name': a['name'], 'compounds': a['compounds']} for a in areas), key=lambda x: x['compounds'])}
json.dump(stats, open(os.path.join(REPO, 'model', 'stats', 'register.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False))
