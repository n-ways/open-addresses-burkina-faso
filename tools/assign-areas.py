#!/usr/bin/env python3
"""Every Burkinabè footprint's code area.

  python3 tools/assign-areas.py <work folder>

Reads <work>/buildings-pts.csv (tools/extract-buildings.py: bid, lon, lat, unit = the commune's HDX
p-code, dens) and model/areas/register.json: the nearest named place of its commune (local metres, ties
to the lower index). A footprint in no commune polygon (on the border) takes the nearest place in the
country. Standard library only, streamed.

Writes <work>/area-of.csv (bid, aid = "<postcode>-<index>", dens), <work>/area-counts-raw.json and
<work>/area-boxes.json (each area's box of footprint centres: its numbering frame).
"""
import collections, csv, json, math, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
work = os.path.abspath(sys.argv[1])
W = lambda f: os.path.join(work, f)
reg = json.load(open(os.path.join(REPO, 'model', 'areas', 'register.json'), encoding='utf-8'))
by_pcode = {}
allp = []
for pc, c in reg.items():
    ps = [(v['lon'], v['lat'], f"{pc}-{v['index']}") for v in c['villages']]
    by_pcode[c['pcode']] = ps
    allp += ps
G = collections.defaultdict(list)
for p in allp:
    G[(int(p[0] // 0.1), int(p[1] // 0.1))].append(p)
CG = {}
for pcode, ps in by_pcode.items():
    g = collections.defaultdict(list)
    for p in ps:
        g[(int(p[0] // 0.05), int(p[1] // 0.05))].append(p)
    CG[pcode] = g


def nearest(grid, cell, lon, lat, maxr):
    cl = math.cos(math.radians(lat)) ** 2
    best = None
    for r in range(0, maxr):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                for p in grid.get((int(lon // cell) + dx, int(lat // cell) + dy), ()):
                    d = ((p[0] - lon) ** 2 * cl + (p[1] - lat) ** 2, p[2])
                    if best is None or d < best:
                        best = d
        if best is not None and math.sqrt(best[0]) < (r - 1) * cell:
            return best[1]
    return best[1] if best else None


counts, stats, box = collections.Counter(), collections.Counter(), {}
with open(W('buildings-pts.csv'), encoding='utf-8', newline='') as f, open(W('area-of.csv'), 'w', newline='') as o:
    w = csv.writer(o)
    w.writerow(['bid', 'aid', 'dens'])
    for r in csv.DictReader(f):
        lat, lon = float(r['lat']), float(r['lon'])
        aid = nearest(CG[r['unit']], 0.05, lon, lat, 400) if r['unit'] in CG else None
        if aid is None:
            aid = nearest(G, 0.1, lon, lat, 200)
            stats['noUnit'] += 1
        counts[aid] += 1
        b = box.get(aid)
        box[aid] = [lon, lat, lon, lat] if b is None else [min(b[0], lon), min(b[1], lat), max(b[2], lon), max(b[3], lat)]
        w.writerow([r['bid'], aid, r['dens']])
json.dump(dict(sorted(counts.items())), open(W('area-counts-raw.json'), 'w'))
json.dump(dict(sorted(box.items())), open(W('area-boxes.json'), 'w'))
print(sum(counts.values()), 'footprints,', len(counts), 'areas with footprints,', stats['noUnit'], 'in no commune;',
      'largest', counts.most_common(5))
