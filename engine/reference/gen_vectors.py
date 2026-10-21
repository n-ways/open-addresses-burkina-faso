#!/usr/bin/env python3
"""Rebuild test_vectors.json from real points (run only when the SPEC changes on purpose)."""
import json, bf_engine as e

_load = e._load_json

V = {'note': 'Real points: OpenStreetMap / Google-Microsoft footprints (N-Ways map data, Oct 2026) and OSM and GeoNames place '
             'names; the codes are taken from the tables frozen at first issue (20 October 2026).',
     'damm': [], 'machine': [], 'remembered': [], 'names': [], 'nameKeys': [], 'rejected': [], 'spoken_fr': [], 'spot': [], 'spotOutside': [], 'registry': []}
for s in ['572', '1000015' + '48217', '00042406502' + '021' + '4117']:
    V['damm'].append({'digits': s, 'check': e.damm(s)})
# Every example is taken from the frozen tables (model/areas/name-ranges.json, register.json), so
# the vectors always describe issued codes. Secteur codes are not issued (no secteur map is public).
NR = e.names()['names']
REG = _load('../../model/areas/register.json')
REGV = {(pc, v['index']): v for pc, c in REG.items() for v in c['villages']}


def first(key, k=0, plus=16):
    b = NR[key]['blocks'][k]
    return b[0], b[1], b[3] + plus


shared = sorted((k for k, v in NR.items() if len(v['blocks']) >= 2), key=lambda k: (-len(NR[k]['blocks']), k))[:3]
for k in shared[:2]:
    for idx in (0, 1):
        pc, ix, n = first(k, idx)
        V['machine'].append({'parts': [pc, 'V', ix, str(n)], 'code': e.machine(pc, 'V', ix, str(n))})
for k in shared:
    pc, ix, n = first(k)
    V['remembered'].append({'area': NR[k]['plateName'], 'kind': 'V', 'number': str(n), 'text': e.remembered(NR[k]['plateName'], str(n), 'V')})
# Same name, different places: the number alone says which one (national name ranges, SPEC 2.4)
for k in shared:
    for idx in (0, 1):
        pc, ix, n = first(k, idx)
        text = f"{NR[k]['plateName']} {e.group_number(n)}"
        r = e.resolve_remembered(text)
        V['names'].append({'text': text, 'code': r['code'], 'postcode': r['postcode'], 'kind': r['kind'], 'place': r['place'],
                           'decodesTo': REGV[(pc, ix)]['officialName'] + ', ' + REG[pc]['commune']})
# Plate names: (a) a long official name decodes to its plate name; (b) two areas whose plate names are
# the same only after shortening decode to different places.
V['plates'] = []
long_ones = [(pc, v) for pc, c in sorted(REG.items()) for v in c['villages']
             if v.get('plateName') and v['plateName'] != v['officialName'] and not v.get('needsCouncilChoice')][:6]
for pc, v in long_ones:
    V['plates'].append({'postcode': pc, 'index': v['index'], 'officialName': v['officialName'], 'plateName': v['plateName'],
                        'plateRule': v['plateRule'], 'fits': e.plate_ok(v['plateName'])})
V['plateDecode'] = []
for pc, v in long_ones[:3]:
    k = e.name_key(v['plateName'])
    blk = next(b for b in NR[k]['blocks'] if (b[0], b[1]) == (pc, v['index']))
    n = blk[3] + 1
    for text, why in ((f"{v['officialName']} {e.group_number(n)}", 'the official name typed: decodes to its plate name'),
                      (f"{v['plateName']} {e.group_number(n)}", 'the plate name')):
        if e.name_key(text.rsplit(' ', 1)[0]) not in NR and e.name_key(v['officialName']) not in e.names()['aliases'] and why.startswith('the official'):
            continue
        r = e.resolve_remembered(text)
        V['plateDecode'].append({'text': text, 'code': r['code'], 'plateName': r['area'], 'decodesTo': v['officialName'] + ', ' + REG[pc]['commune'], 'why': why})
V['plateRejected'] = [{'plate': n, 'why': 'over the plate limit: issued under it provisionally, the commune chooses a shorter one'}
                      for n in sorted({v['plateName'] for c in REG.values() for v in c['villages']
                                       if v.get('plateName') and not e.plate_ok(v['plateName'])})[:3]]
V['nameKeys'] = [{'names': g, 'key': e.name_key(g[0])} for g in
                 [['Douré', 'Doure', 'DOURE'], ['Ouatinoma', 'Watinoma', 'Wattinooma', 'Ouattinoma'], ['Goghin', 'Gogin'],
                  ['Sanga', 'Sangha'], ['Q-Tanghin', 'Tanguin', 'Tangin'], ['Djibo', 'Jibo'],
                  ['Saint-Camille', 'St-Camille', 'St Camille']]]
k0 = shared[0]
pc0, ix0, n0 = first(k0)
good = e.machine(pc0, 'V', ix0, str(n0))
V['rejected'] = [{'text': t, 'why': w} for t, w in
                 [('Secteur 15 Ouaga · 48 217', 'secteur codes are not issued'),
                  (f"{NR[k0]['plateName']} 217" if NR[k0]['digits'] != 3 else f"{NR[k0]['plateName']} 2171", 'wrong digit count for the name'),
                  (f"{NR[k0]['plateName']} {e.group_number(n0)}-{(int(good[-1]) + 1) % 10}", 'check digit binds name + number + area'),
                  (f"{NR[k0]['plateName']} {e.group_number(NR[k0]['spareFrom'])}", 'in the spare of the range: not issued')]]
V['spoken_fr'] = [{'number': n, 'fr': e.say_fr(n)} for n in ['48217', '4117', '217', '9171', '8070']]
for name, lat, lon in [('Ouagadougou, OSM public building (2,185 m2 footprint) near the city centre', 12.3721856, -1.5236057),
                       ('Ouagadougou, OSM building with a cinema tag', 12.3680912, -1.5204357),
                       ('Bobo-Dioulasso, footprint centroid (10% national sample)', 11.177437, -4.298791),
                       ('Nabadogo village node (OSM), commune of Sabou', 12.133638, -2.070857),
                       ('Bissiga hamlet node (OSM), commune of Sabou', 12.147873, -2.071336)]:
    c = e.commune_at(lat, lon)
    code = e.spot_encode(lat, lon)
    V['spot'].append({'name': name, 'lat': lat, 'lon': lon, 'commune': c['name'], 'postcode': c['postcode'],
                      'spot': code, 'decoded': list(e.spot_decode(code))})
# Points in no commune outline (SPEC 5.1): issued entrances in a gap between two outlines, over a
# border line inside the frame, beyond the frame (nearest edge cell), and points refused.
for name, issued, lat, lon in [('Ouagadougou compound in the gap between the Ouagadougou and Komsilga outlines', 'BF-10000-V076-11657-0', 12.2781536, -1.5450458),
                               ('Compound 8.6 km over the published outline of its commune', 'BF-61350-V048-181-6', 15.0013242, 0.2241349),
                               ('Compound in no frame within 10 km, 14 cells (140 m) south of its commune frame: nearest edge cell', 'BF-32250-V024-2302-1', 10.9987819, -0.9736617),
                               ('Point in a neighbouring country, no commune within 10 km', None, 16.0, -1.0),
                               ('Point in a neighbouring country, far from the border', None, 5.6, -0.2)]:
    v = {'name': name, 'lat': lat, 'lon': lon}
    if issued:
        v['issued'] = issued
    pc = e.spot_commune(lat, lon)
    if pc is None:
        v['error'] = 'refused'
    else:
        code = e.spot_encode(lat, lon)
        v.update({'postcode': pc, 'clamped': e.spot_frame_beyond(lat, lon, e.frames()[pc]) > 0, 'spot': code,
                  'decoded': list(e.spot_decode(code))})
    V['spotOutside'].append(v)
for f, digits in [('sample-ouaga-centre.csv', 5), ('sample-ouaga-periphery.csv', 5)]:
    comps, pts, nums, d, box = e.registry(f, digits)
    first = sorted(nums.items(), key=lambda kv: kv[1])[:5]
    newp = (box[0] + (box[2] - box[0]) * 0.37, box[1] + (box[3] - box[1]) * 0.61)
    prov = e.provisional_number(newp, nums, pts, box, digits)
    V['registry'].append({'sample': f, 'digits': digits, 'structures': sum(len(c['members']) for c in comps),
                          'compounds': len(comps),
                          'byRule': {r: sum(1 for c in comps if c['rule'] == r) for r in sorted({c['rule'] for c in comps})},
                          'first': [{'compound': k, 'number': n} for k, n in first],
                          'newHome': {'lon': round(newp[0], 7), 'lat': round(newp[1], 7), 'provisional': prov}})
e._write_json(V, 'test_vectors.json', ensure_ascii=False, indent=1)
print(json.dumps(V, ensure_ascii=False)[:2500])
