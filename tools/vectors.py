#!/usr/bin/env python3
"""Conformance vectors for every port of the engine: engine/reference/vectors.json.

Computed by the reference engine (engine/reference/bf_engine.py) on the frozen register
(model/areas/name-ranges.json, model/areas/register.json, engine/data/register.json); a port (the
N-Ways issuer's engine) must reproduce them value for value.

  python3 tools/vectors.py
"""
import csv, gzip, json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import bf_engine as E  # noqa: E402

reg = json.load(open(os.path.join(REPO, 'engine', 'data', 'register.json'), encoding='utf-8'))
areas = reg['areas']
by_pc = {}
for a in areas:
    by_pc.setdefault(a['postcode'], []).append(a)


def area_at(lat, lon):
    """The code area of a point (tools/assign-areas.py): nearest place of the commune, ties to the lower key."""
    c = E.commune_at(lat, lon)
    if c is None:
        return None
    cl = math.cos(math.radians(lat)) ** 2
    return min(by_pc[c['postcode']], key=lambda a: ((a['point'][0] - lon) ** 2 * cl + (a['point'][1] - lat) ** 2, a['key']))


def decode(text):
    try:
        if text.upper().startswith('BF-'):
            p = E.parse_machine(text)
            if not p['valid']:
                return {'text': text, 'error': 'invalid'}
            return {'text': text, 'machine': E.machine(p['postcode'], p['kind'], p['place'], p['number'])}
        return {'text': text, 'machine': E.resolve_remembered(text)['code']}
    except ValueError as e:
        return {'text': text, 'error': str(e)}


def outside(lat, lon, issued=None):
    """A vector for a point in no commune outline (SPEC 5.1)."""
    v = {'lat': lat, 'lon': lon}
    if issued:
        v['issued'] = issued
    pc = E.spot_commune(lat, lon)
    if pc is None:
        v['error'] = 'refused'
        return v
    code = E.spot_encode(lat, lon)
    v.update({'commune': pc, 'code': code, 'clamped': E.spot_frame_beyond(lat, lon, E.frames()[pc]) > 0,
              'decoded': list(E.spot_decode(code))})
    return v


def spots_outside():
    """Issued entrances in no outline, and random points around the country in no outline.
    Candidates from the registry: rows whose spot code names another commune than the code, or
    lies on a frame edge (the nearest edge cell); each kept only if it lies in no outline."""
    rnd = random.Random(5101)
    reg = os.path.join(REPO, 'registry')
    other, edge = [], []
    for fn in sorted(os.listdir(reg)):
        if not fn.endswith('.csv.gz') or fn == 'areas.csv.gz':
            continue
        with gzip.open(os.path.join(reg, fn), 'rt', newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                m = E.SPOT_RE.match(row['spot_code'])
                if not m:
                    continue
                f_ = E.frames()[m.group(1)]
                e, n = int(m.group(2)), int(m.group(3))
                pt = (row['machine'], float(row['entrance_lat']), float(row['entrance_lng']))
                if e in (0, 10 ** f_['dx'] - 1) or n in (0, 10 ** f_['dy'] - 1):
                    edge.append(pt)
                elif m.group(1) != row['machine'][3:8]:
                    other.append(pt)
    out = []
    for pool, k in ((other, 400), (edge, 200)):
        kept = 0
        for machine, lat, lon in rnd.sample(pool, len(pool)):
            if kept == k:
                break
            if E.commune_at(lat, lon) is None:
                out.append(outside(lat, lon, machine))
                kept += 1
    coded = refused = 0
    while coded < 150 or refused < 60:
        lat, lon = rnd.uniform(9.2, 15.3), rnd.uniform(-5.7, 2.6)
        if E.commune_at(lat, lon) is not None:
            continue
        v = outside(lat, lon)
        if 'error' in v and refused < 60:
            refused += 1
            out.append(v)
        elif 'error' not in v and coded < 150:
            coded += 1
            out.append(v)
    return out


def main():
    rnd = random.Random(248)
    num = [a for a in areas if a['blocks']]
    words = sorted({a['name'] for a in areas} | {a['officialName'] for a in areas})
    tricky = ['Douré', 'Doure', 'Ouatinoma', 'Watinoma', 'Wattinooma', 'Tanguin', 'Tanghin', 'Tangin', 'Goghin', 'Gogin',
              'St Camille', 'Saint-Camille', 'Ste Thérèse', 'Q Tangonkin', 'Quartier Dapoya', 'Village de Bissiga', 'La Patte',
              "L'Arbre", 'Djibo', 'Tchériba', 'Phalga', 'Zongo']
    keys = [[w, E.name_key(w)] for w in tricky + rnd.sample(words, 700)]
    forms, found = [], []
    for a in rnd.sample(num, 500):
        lo, hi = a['blocks'][0]
        n = rnd.randint(lo, hi)
        m = E.machine(a['postcode'], 'V', a['index'], n, a['nameId'])
        forms.append({'zone': a['key'], 'number': n, 'check': int(m[-1]), 'home': '%s %d' % (a['name'], n),
                      'written': '%s %s' % (a['name'], E.group_number(n)), 'machine': m})
        for text in ('%s %d' % (a['name'], n), '%s %s' % (a['name'], E.group_number(n)), m, '%s %s-%s' % (a['name'], E.group_number(n), m[-1])):
            found.append(decode(text))
    off = [a for a in num if E.name_key(a['officialName']) != E.name_key(a['name']) and E.name_key(a['officialName']) in reg['aliases']]
    for a in rnd.sample(off, min(150, len(off))):
        found.append(decode('%s %d' % (a['officialName'], a['blocks'][0][0] + 1)))
    for a in rnd.sample(num, 80):
        n = a['blocks'][0][0] + 3
        good = E.machine(a['postcode'], 'V', a['index'], n, a['nameId'])
        found.append(decode(good[:-1] + str((int(good[-1]) + 1) % 10)))
        found.append(decode('%s %d-%d' % (a['name'], n, (int(good[-1]) + 1) % 10)))
        found.append(decode('%s %d' % (a['name'], a['blocks'][-1][1] + 1)))
    found += [decode(t) for t in ('Nulle Part 1234', 'Secteur 15 Ouaga · 48 217', 'Bissiga 41 17 9', 'BF-10000-S15-48217-6')]
    spots = []
    while len(spots) < 500:
        lat, lon = rnd.uniform(9.4, 15.1), rnd.uniform(-5.5, 2.4)
        a = area_at(lat, lon)
        if a is None:
            continue
        code = E.spot_encode(lat, lon)
        spots.append({'lat': lat, 'lon': lon, 'area': a['key'], 'code': code, 'decoded': list(E.spot_decode(code))})
    for box in ((-1.65, 12.25, -1.40, 12.47), (-4.40, 11.10, -4.20, 11.25)):   # Ouagadougou, Bobo-Dioulasso
        for _ in range(100):
            lat, lon = rnd.uniform(box[1], box[3]), rnd.uniform(box[0], box[2])
            a = area_at(lat, lon)
            if a is None:
                continue
            code = E.spot_encode(lat, lon)
            spots.append({'lat': lat, 'lon': lon, 'area': a['key'], 'code': code, 'decoded': list(E.spot_decode(code))})
    big = max(num, key=lambda a: a['blocks'][0][1] - a['blocks'][0][0])
    x0, y0, x1, y1 = big['frame']
    comps = [{'id': 'c%02d' % k, 'lat': y0 + rnd.uniform(0, y1 - y0), 'lon': x0 + rnd.uniform(0, x1 - x0)} for k in range(41)]
    nums, _ = E.issue_numbers({c['id']: (c['lon'], c['lat']) for c in comps}, tuple(big['frame']), block=tuple(big['blocks'][0]))
    issued = dict(nums)
    points = {c['id']: (c['lon'], c['lat']) for c in comps}
    inserts = []
    for i in range(60):
        lat, lon = y0 + rnd.uniform(0, y1 - y0), x0 + rnd.uniform(0, x1 - x0)
        n = E.provisional_number((lon, lat), issued, points, tuple(big['frame']), big['digits'], block=tuple(big['blocks'][0]))
        inserts.append({'lat': lat, 'lon': lon, 'number': n})
        k = 'i%02d' % i
        issued[k], points[k] = n, (lon, lat)
    hil = [[x, y, E.hilbert_index(16, x, y)] for x, y in ((0, 0), (1, 0), (65535, 65535), (12345, 54321), (40000, 2))]
    out = {'note': 'Computed by engine/reference/bf_engine.py on the frozen register; every port must match.',
           'nameKeys': keys, 'forms': forms, 'found': found, 'spots': spots,
           'numbering': {'zone': big['key'], 'compounds': comps, 'numbers': nums, 'inserts': inserts},
           'hilbert': hil, 'groups': [[n, E.group_number(n)] for n in (217, 1000, 4117, 48217, 10000, 99999)],
           'spotsOutside': spots_outside()}
    json.dump(out, open(os.path.join(REPO, 'engine', 'reference', 'vectors.json'), 'w'), ensure_ascii=False, indent=0)
    print(len(keys), 'name keys,', len(forms), 'forms,', len(found), 'decodings,', len(spots), 'spots,', len(out['spotsOutside']),
          'points in no outline,', len(inserts), 'inserts')


if __name__ == '__main__':
    main()
