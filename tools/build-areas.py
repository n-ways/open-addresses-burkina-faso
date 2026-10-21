#!/usr/bin/env python3
"""The code areas of Burkina Faso at first issue: model/areas/register.json.

  python3 tools/build-areas.py <work folder> <GeoNames BF.txt>

Every named place people use, in the commune that holds it:
  OpenStreetMap  place = village, hamlet, isolated_dwelling, locality, quarter, suburb, neighbourhood,
                 town, city (<work>/place.geojsonseq; ways and relations by their first point), ODbL;
  GeoNames       feature codes PPL, PPLX (sections of a town), PPLL, PPLQ, PPLA, PPLA2, PPLA3, PPLC,
                 CC BY 4.0: it names the quarters of Ouagadougou and the villages swallowed by the towns
                 that OpenStreetMap does not (Dapoya, Larlé, Cissin, Kilwin...).
A GeoNames place within 1 km of an OpenStreetMap place with the same name key (bf_engine.name_key) is the
same place and is dropped; so is a second place of one name key within 300 m. Generic labels
("Campement d'éleveurs", "Site de...", bf_engine.is_generic) are not names and are left out: their homes
take the nearest real name. Towns are no longer cut into secteurs (no secteur map is public): a town's
homes take the nearest named quarter or village like everywhere else, so every number stays at 5
digits or fewer; the secteur becomes an alias once a commune shares its map.

Areas are indexed 001.. per commune in the alphabetical order of their plain name, then frozen.
"""
import csv, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import bf_engine as E  # noqa: E402

work, gn_path = os.path.abspath(sys.argv[1]), sys.argv[2]
OSM_KINDS = ('village', 'hamlet', 'isolated_dwelling', 'locality', 'quarter', 'suburb', 'neighbourhood', 'town', 'city')
GN_CODES = ('PPL', 'PPLX', 'PPLL', 'PPLQ', 'PPLA', 'PPLA2', 'PPLA3', 'PPLC')

pts = []
for line in open(os.path.join(work, 'place.geojsonseq'), encoding='utf-8'):
    line = line.strip('\x1e\n ')
    if not line:
        continue
    o = json.loads(line)
    p, g = o['properties'], o['geometry']
    name = (p.get('name:fr') or p.get('name') or '').strip()
    if p.get('place') not in OSM_KINDS or not name or E.is_generic(name):
        continue
    c = g['coordinates']
    while isinstance(c[0], list):
        c = c[0]
    pts.append({'name': name, 'kind': p['place'], 'lon': round(c[0], 6), 'lat': round(c[1], 6),
                'source': f"osm:{p.get('@type', 'node')}/{p.get('@id')}"})
grid = {}
for q in pts:
    grid.setdefault((E.name_key(q['name']), round(q['lon'], 1), round(q['lat'], 1)), []).append(q)


def near(q, others, metres):
    for o in others:
        d = math.hypot((o['lon'] - q['lon']) * 111320 * math.cos(math.radians(q['lat'])), (o['lat'] - q['lat']) * 110574)
        if d <= metres:
            return True
    return False


def around(key, lon, lat):
    out = []
    for dx in (-0.1, 0, 0.1):
        for dy in (-0.1, 0, 0.1):
            out += grid.get((key, round(lon + dx, 1), round(lat + dy, 1)), [])
    return out


added = dropped = 0
for r in csv.reader(open(gn_path, encoding='utf-8'), delimiter='\t'):
    if r[7] not in GN_CODES or E.is_generic(r[1]):
        continue
    q = {'name': r[1], 'kind': {'PPLX': 'quarter'}.get(r[7], 'village'), 'lon': round(float(r[5]), 6), 'lat': round(float(r[4]), 6),
         'source': f'geonames:{r[0]}'}
    k = E.name_key(q['name'])
    if not k or near(q, around(k, q['lon'], q['lat']), 1000):
        dropped += 1
        continue
    pts.append(q)
    grid.setdefault((k, round(q['lon'], 1), round(q['lat'], 1)), []).append(q)
    added += 1

reg = {}
for c in E.communes():
    if not c['postcode']:
        raise SystemExit(f'{c["name"]} has no machine code')
    x0, y0, x1, y1 = c['box']
    inside = [q for q in pts if x0 <= q['lon'] <= x1 and y0 <= q['lat'] <= y1 and E._inside(q['lon'], q['lat'], c['polys'])]
    inside.sort(key=lambda q: (E.plain(q['name']), q['source'].startswith('geonames'), q['lat'], q['lon']))
    kept = []
    for q in inside:   # a second place of one name within 300 m is the same place
        if near(q, [k for k in kept if E.name_key(k['name']) == E.name_key(q['name'])], 300):
            continue
        kept.append(q)
    if not kept:
        kept = [{'name': c['name'], 'kind': 'town', 'lon': round((x0 + x1) / 2, 6), 'lat': round((y0 + y1) / 2, 6), 'source': 'commune'}]
    if len(kept) > 999:
        raise SystemExit(f'{c["name"]}: {len(kept)} places, more than 999')
    reg[c['postcode']] = {'commune': c['name'], 'pcode': c['pcode'],
                          'villages': [{'index': f'{i + 1:03d}', 'officialName': q['name'], 'kind': q['kind'], 'lon': q['lon'],
                                        'lat': q['lat'], 'source': q['source']} for i, q in enumerate(kept)]}
json.dump(dict(sorted(reg.items())), open(os.path.join(REPO, 'model', 'areas', 'register.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
n = sum(len(v['villages']) for v in reg.values())
print(n, 'areas in', len(reg), 'communes;', added, 'from GeoNames,', dropped, 'GeoNames duplicates;',
      'largest commune', max((len(v['villages']), v['commune']) for v in reg.values()))
