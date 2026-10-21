#!/usr/bin/env python3
"""Data files behind the paper's figures (docs/figures/*.dat), computed from the published
register, registry and statistics. Standard library only.

    python3 tools/paper-figures.py

Every figure source in docs/figures/ reads one of these files; re-run this script after a new
registry export and rebuild the paper (sh docs/paper/build.sh).
"""
import collections
import csv
import gzip
import io
import json
import math
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'docs', 'figures')

# Equirectangular plane for the national map: x = (lon - LON0) cos(LATC) K, y = (lat - LAT0) K, in cm.
LON0, LAT0, LATC, K = -5.6, 9.35, 12.3, 1.5

REGION_NAMES = {'Djoro': 'Djôrô', 'Koulse': 'Kuilsé', 'Nakambe': 'Nakambé'}


def load(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as f:
        return json.load(f)


def write(name, text):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        f.write(text)


def simplify(pts, tol):
    """Douglas-Peucker on a list of (x, y)."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = math.hypot(p[0] - a[0], p[1] - a[1]) if L == 0 else abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / L
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [a, b]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def rings(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates'][0]]
    return [p[0] for p in geom['coordinates']]


def ring_km2(ring):
    kx = 111.320 * math.cos(math.radians(LATC))
    ky = 110.574
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        s += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(s) / 2


def plane(lon, lat):
    return ((lon - LON0) * math.cos(math.radians(LATC)) * K, (lat - LAT0) * K)


def communes_map():
    """National map: every commune shaded by compounds per square kilometre."""
    geo = load('model/units/communes.geojson')
    pcode_to_post = {}
    with open(os.path.join(REPO, 'model', 'units', 'communes.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            pcode_to_post[r['pcode']] = r['laposte_postcode']
    counts = load('registry/MANIFEST.json')['byUnit']
    edges = [5, 10, 20, 50, 200]
    lines = ['% Communes of Burkina Faso shaded by compounds per km2 (tools/paper-figures.py).']
    hist = collections.Counter()
    for ft in geo['features']:
        post = pcode_to_post.get(ft['properties']['pcode'])
        rs = rings(ft['geometry'])
        km2 = sum(ring_km2(r) for r in rs)
        dens = counts.get(post, 0) / km2 if km2 else 0
        cls = sum(1 for e in edges if dens >= e)
        hist[cls] += 1
        for r in rs:
            pts = simplify([plane(x, y) for x, y in r], 0.012)
            if len(pts) < 4:
                continue
            path = ' -- '.join(f'({x:.3f},{y:.3f})' for x, y in pts[:-1])
            lines.append(f'\\filldraw[dens{cls}] {path} -- cycle;')
    write('communes-map.dat', '\n'.join(lines) + '\n')
    cities = [('Ouagadougou', -1.5197, 12.3714), ('Bobo-Dioulasso', -4.2979, 11.1771),
              ('Koudougou', -2.3627, 12.2526), ('Ouahigouya', -2.4210, 13.5828),
              ('Kaya', -1.0844, 13.0917), ('Fada N\'Gourma', 0.3586, 12.0616),
              ('Dori', -0.0345, 14.0354), ('Banfora', -4.7617, 10.6333)]
    with open(os.path.join(OUT, 'communes-cities.dat'), 'w', encoding='utf-8') as f:
        f.write('x y name\n')
        for n, lon, lat in cities:
            x, y = plane(lon, lat)
            f.write(f'{x:.3f} {y:.3f} {{{n}}}\n')
    return hist


def area_sizes():
    """Histogram of compounds per area, split by the digit count of the area's name."""
    reg = load('engine/data/register.json')
    edges = [1, 10, 30, 100, 300, 1000, 3000, 10000, 40000]
    labels = ['1–9', '10–29', '30–99', '100–299', '300–999', '1k–3k', '3k–10k', '10k–40k']
    tab = {d: [0] * len(labels) for d in (3, 4, 5)}
    for a in reg['areas']:
        c = a['compounds']
        if c <= 0:
            continue
        i = max(j for j, e in enumerate(edges[:-1]) if c >= e)
        tab[a['digits']][i] += 1
    with open(os.path.join(OUT, 'area-sizes.dat'), 'w', encoding='utf-8') as f:
        f.write('bin label d3 d4 d5\n')
        for i, lab in enumerate(labels):
            f.write(f'{i} {{{lab}}} {tab[3][i]} {tab[4][i]} {tab[5][i]}\n')
    return tab


def koulouba():
    """Koulouba's compounds, in metres from its frame's south-west corner, in number order."""
    reg = load('engine/data/register.json')
    a = next(x for x in reg['areas'] if x['key'] == '10000-064')
    x0, y0, x1, y1 = a['frame']
    kx = 111320 * math.cos(math.radians((y0 + y1) / 2))
    rows = []
    with gzip.open(os.path.join(REPO, 'registry', '10000.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['zone'] == '10000-064':
                rows.append((int(r['number']), float(r['entrance_lng']), float(r['entrance_lat'])))
    rows.sort()
    with open(os.path.join(OUT, 'koulouba.dat'), 'w', encoding='utf-8') as f:
        f.write('x y n\n')
        for n, lon, lat in rows:
            f.write(f'{(lon - x0) * kx:.1f} {(lat - y0) * 110574:.1f} {n}\n')
    w, h = (x1 - x0) * kx, (y1 - y0) * 110574
    return len(rows), round(w), round(h)


def kombissiri():
    """The blocks of one shared four-digit name, Kombissiri (six areas of the commune of that name)."""
    reg = load('engine/data/register.json')
    names = {n['key']: n for n in reg['names']}
    areas = sorted((a for a in reg['areas'] if a['nameKey'] == 'KOMBISIRI'),
                   key=lambda a: a['blocks'][0][0])
    with open(os.path.join(OUT, 'kombissiri.dat'), 'w', encoding='utf-8') as f:
        f.write('lo hi compounds name\n')
        for a in areas:
            lo, hi = a['blocks'][0]
            f.write(f'{lo} {hi} {a["compounds"]} {{{a["officialName"]}}}\n')
    return names['KOMBISIRI'], [(a['postcode'], a['compounds'], a['blocks']) for a in areas]


def ouaga_frame():
    """Ouagadougou's outline in its spot frame, in kilometres east and north of the origin."""
    reg = load('engine/data/register.json')
    fr = next(c for c in reg['communes'] if c['postcode'] == '10000')
    kx = 111.320 * math.cos(math.radians(fr['latc']))
    geo = load('model/units/communes.geojson')
    ft = next(x for x in geo['features'] if x['properties']['pcode'] == fr['pcode'])
    with open(os.path.join(OUT, 'ouaga-frame.dat'), 'w', encoding='utf-8') as f:
        f.write('e n\n')
        for r in rings(ft['geometry']):
            pts = simplify([((x - fr['lon0']) * kx, (y - fr['lat0']) * 110.574) for x, y in r], 0.05)
            for x, y in pts:
                f.write(f'{x:.3f} {y:.3f}\n')
            f.write('\n')
    return fr


def sources():
    """Footprints per region by source."""
    st = load('model/stats/building-stats.json')['regions']
    rows = sorted(st.items(), key=lambda kv: kv[1]['structures'])
    with open(os.path.join(OUT, 'sources.dat'), 'w', encoding='utf-8') as f:
        f.write('i region osm other\n')
        for i, (r, v) in enumerate(rows):
            osm = v['fromOpenStreetMap'] / 1e3
            f.write(f'{i} {{{REGION_NAMES.get(r, r)}}} {osm:.1f} {v["structures"] / 1e3 - osm:.1f}\n')
    return len(rows)


if __name__ == '__main__':
    print('communes', dict(communes_map()))
    print('area sizes', area_sizes())
    print('koulouba', koulouba())
    print('kombissiri', kombissiri())
    print('ouaga frame', ouaga_frame())
    print('regions', sources())
