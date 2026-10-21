#!/usr/bin/env python3
"""The measured properties reported in the paper's evaluation chapter, computed from the published
registry and register with the reference engine. Standard library only; about ten minutes.

    python3 tools/paper-evaluation.py            # writes model/stats/evaluation.json

Measures
  uniqueness   machine codes and remembered forms are each unique across the registry
  lengths      characters of the written form (plate name, space, grouped number) and digits
  check digit  share of single-digit substitutions, adjacent transpositions, jump transpositions
               and twin errors that the Damm digit detects, over every digit of a sample of codes
  decoding     remembered forms (as written, lower case without accents, without the space in the
               number) resolved with no context back to their machine code, on a sample
  spot codes   distance from each sampled entrance to the centre of its decoded spot cell; over the
               whole registry, the entrances beyond the frame that codes them (SPEC 5.1: a point in no
               commune outline may take its nearest commune's nearest edge cell) and their distance
  collisions   codes that would share their remembered form with another area's code if every area
               numbered from the bottom of its own range instead of a block of a national range
"""
import collections
import csv
import gzip
import json
import math
import os
import random
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import bf_engine as E  # noqa: E402

SAMPLE = 20000
random.seed(20261020)


def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()


def metres(lat1, lon1, lat2, lon2):
    kx = 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon1 - lon2) * kx, (lat1 - lat2) * 110574)


def check_rates(codes):
    """Detection rates of the Damm digit over the checked digit string of each code."""
    hits = collections.Counter()
    tries = collections.Counter()
    for code in codes:
        pc, kind, place, number = code['postcode'], code['kind'], code['place'], code['number']
        s = E.check_input(pc, kind, place, number, code['nid'])
        c = E.damm(s)
        full = s + str(c)
        def test(kind_, t):
            tries[kind_] += 1
            if t != full and E.damm(t) == 0:
                return
            hits[kind_] += 1
        for i, d in enumerate(full):
            for r in '0123456789':
                if r != d:
                    test('single', full[:i] + r + full[i + 1:])
        for i in range(len(full) - 1):
            a, b = full[i], full[i + 1]
            if a != b:
                test('adjacent', full[:i] + b + a + full[i + 2:])
            elif a == b:
                for r in '0123456789':
                    if r != a:
                        test('twin', full[:i] + r + r + full[i + 2:])
        for i in range(len(full) - 2):
            a, b = full[i], full[i + 2]
            if a != b:
                test('jump', full[:i] + b + full[i + 1] + a + full[i + 3:])
    return {k: {'tested': tries[k], 'detected': hits[k], 'rate': round(hits[k] / tries[k], 5)} for k in tries}


def counterfactual_collisions(reg, codes):
    """Every area numbered from 10^(d-1) of its own digit count, same block size and step rule, for
    the codes it holds in the published registry (codes: area key -> count)."""
    by = collections.defaultdict(list)
    for a in reg['areas']:
        if codes.get(a['key'], 0) > 0:
            by[a['nameKey']].append(a)
    colliding = 0
    shared_codes = 0
    for key, areas in by.items():
        if len(areas) < 2:
            continue
        seen = collections.Counter()
        sets = []
        for a in areas:
            n = codes[a['key']]
            d = E.digits_for(n)
            lo = 10 ** (d - 1)
            B = E.block_size(n)
            main = (2 * B) // 3
            step = max(1, main // max(1, int(n * 1.5)))
            nums = [lo + i * step for i in range(n)]
            sets.append(nums)
            seen.update(set(nums))
            shared_codes += n
        for nums in sets:
            colliding += sum(1 for x in nums if seen[x] > 1)
    return {'codesInSharedNames': shared_codes, 'wouldCollide': colliding}


def main():
    reg = E._load_json(os.path.join(REPO, 'engine', 'data', 'register.json'))
    nid = {a['key']: a['nameId'] for a in reg['areas']}
    machines = set()
    homes = set()
    total = 0
    no_spot = 0
    edge = 0
    edge_max = 0.0
    edge_codes = set()
    lengths = collections.Counter()
    digits = collections.Counter()
    reservoir = []
    per_area = collections.Counter()
    files = sorted(f for f in os.listdir(os.path.join(REPO, 'registry')) if f.endswith('.csv.gz') and f != 'areas.csv.gz')
    for name in files:
        with gzip.open(os.path.join(REPO, 'registry', name), 'rt', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                total += 1
                per_area[r['zone']] += 1
                machines.add(hash(r['machine']))
                homes.add(hash(E.name_key(r['home'].rsplit(' ', 1)[0]) + ' ' + r['number']))
                lengths[len(r['written'])] += 1
                no_spot += not r['spot_code']
                sm = E.SPOT_RE.match(r['spot_code'])
                if sm:
                    lat, lon = float(r['entrance_lat']), float(r['entrance_lng'])
                    if E.spot_frame_beyond(lat, lon, E.frames()[sm.group(1)]) > 0:
                        edge += 1
                        edge_codes.add(r['machine'])
                        clat, clon = E.spot_decode(r['spot_code'])
                        edge_max = max(edge_max, metres(clat, clon, lat, lon))
                digits[len(r['number'])] += 1
                if len(reservoir) < SAMPLE:
                    reservoir.append(r)
                else:
                    j = random.randrange(total)
                    if j < SAMPLE:
                        reservoir[j] = r
    ordered = sorted(lengths.elements())
    out = {
        'codes': total,
        'uniqueMachine': len(machines) == total,
        'uniqueRemembered': len(homes) == total,
        'writtenLength': {'min': ordered[0], 'median': ordered[len(ordered) // 2], 'p99': ordered[int(len(ordered) * 0.99)],
                          'max': ordered[-1], 'mean': round(sum(ordered) / total, 2),
                          'atMost16': round(sum(1 for x in ordered if x <= 16) / total, 4)},
        'digits': dict(sorted(digits.items())),
    }
    del machines, homes, ordered
    ok = collections.Counter()
    spot_max = 0.0
    spot_missing = 0
    spot_edge = 0
    sample_codes = []
    for r in reservoir:
        m = E.parse_machine(r['machine'], nid[r['zone']])
        sample_codes.append({'postcode': m['postcode'], 'kind': m['kind'], 'place': m['place'], 'number': m['number'],
                             'nid': nid[r['zone']]})
        variants = {'written': r['written'], 'plainLower': plain(r['written']), 'ungrouped': r['home']}
        for k, text in variants.items():
            try:
                ok[k] += E.resolve_remembered(text)['code'] == r['machine']
            except ValueError:
                pass
        if not r['spot_code']:
            spot_missing += 1
            continue
        if r['machine'] in edge_codes:
            spot_edge += 1
            continue
        lat, lon = E.spot_decode(r['spot_code'])
        spot_max = max(spot_max, metres(lat, lon, float(r['entrance_lat']), float(r['entrance_lng'])))
    out['decoding'] = {'sample': len(reservoir), **{k: round(v / len(reservoir), 5) for k, v in ok.items()}}
    out['spotMaxMetres'] = round(spot_max, 2)
    out['spotMissingInSample'] = spot_missing
    out['spotMissing'] = no_spot
    out['spotEdgeInSample'] = spot_edge
    out['spotEdgeCells'] = edge
    out['spotEdgeMaxMetres'] = round(edge_max, 1)
    out['checkDigit'] = check_rates(sample_codes[:2000])
    out['counterfactual'] = counterfactual_collisions(reg, per_area)
    with open(os.path.join(REPO, 'model', 'stats', 'evaluation.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
