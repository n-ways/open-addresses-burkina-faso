#!/usr/bin/env python3
"""Plate names and national name ranges for Burkina Faso.

  python3 tools/name-ranges.py        (light: reads model/stats/area-compounds.csv)

Two rules of the model:
  * a remembered code must be unique in the whole country on its own, without the town said after
    it or the phone's position;
  * the name in the code (the PLATE name) is short: at most 12 characters and 2 words
    (engine/reference/plate_names.py). The official name is kept for small print and still decodes.

Writes
  model/areas/name-ranges.json   one entry per normalised plate name: frozen id, digits, blocks, aliases
  model/areas/town-words.json    the town word of each commune (secteur codes carry it), with its plate rule
  model/areas/register.json   adds plateName / plateRule (and the council fields) to every village
  model/stats/name-stats.json    the counts quoted in docs/model.md and the papers

Plate names (SPEC 2.5):
  * derived from the official name by plate_names.derive (lang 'fr'), with Burkina word lists:
    leading "Q" (quartier) is generic; ethnic and status qualifiers (Peulh, Foulbé, Mossi, Silmimossi,
    Rimaïbé, Yarcé, Gourmantché, Bella, Traditionnel...), Mooré "Yiri"/"Tenga"/"Naba"/"Silmi", Fulfuldé "Ouro"/"Wouro"
    (camp, village), "Nouveau", "Site", "Village" and mine/station words are weak: never a plate name
    alone, and a short form that drops one of them goes to the commune (needsCouncilChoice);
  * a short form must not equal a commune, province or region name or a big city of the region;
    a short form equal to the area's own commune ("Base de Vie Mine de Kalsaka") goes to the commune;
  * "Lieu-dit" is generic; Tamasheq "n" ("Ti-n-Bassata") is a linking word, not a word;
  * a short form that drops a number of the official name ("Daribiti n°1") goes to the commune;
  * a short form equal to the name of another place of the same commune ("Gambo (moulin)" next to
    "Gambo") goes to the commune;
  * a hyphenated name too long for the plate ("Baskoudré-Peulh", "Bayandi-Nabyiri") is never cut
    automatically: it goes to the commune with its parts as candidates, the first one provisional;
  * a flagged area keeps a provisional plate name (first candidate) and its codes are issued under
    it; the commune may choose once, and the provisional name stays an alias. A name with no fitting
    candidate (one word over 12 letters, a name with a digit such as "VK6") takes the commune's name
    provisionally (BARE_WORDS and SPEC 2.5).

Name ranges (SPEC 2.4), on the plate name:
  * every village / hamlet whose PLATE name has the same key (bf_engine.name_key) draws its numbers
    from ONE national range for that name;
  * the range is cut into blocks, one per area, in register order (postcode, index) at first issue;
    block size = compounds x 2 rounded up to a multiple of 10, at least 20;
  * digits of the name (3, 4 or 5, same for all its areas) = smallest d whose range holds all blocks
    with the top tenth of the range left spare for areas that will carry the name later;
  * a single area too large for 5 digits on its own is split by named quartiers before issue;
    a name whose areas together do not fit 5 digits keeps the bare name for the blocks that fit in
    register order and gives the others the commune as qualifier, decided once here and listed;
  * an official name whose key differs from its plate key is an alias of that plate name when it
    maps to one plate name only; an alias claimed by two plate names, or equal to another plate
    name, is dropped and listed (droppedAliases);
  * generic labels ("village", "Campement d'éleveurs"...) are not names: they are renamed with the
    commune before issue and take no block.
"""
import collections, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import bf_engine as e  # noqa: E402
import plate_names as P  # noqa: E402

LANG = 'fr'
SPARE = e.NAME_SPARE
areas = list(csv.DictReader(open(os.path.join(REPO, 'model', 'stats', 'area-compounds.csv'), encoding='utf-8')))
crows = list(csv.DictReader(open(os.path.join(REPO, 'model', 'units', 'communes.csv'), encoding='utf-8')))
communes = {r['laposte_postcode']: r for r in crows}
regions = json.load(open(os.path.join(REPO, 'model', 'regions.json'), encoding='utf-8'))
V = [a for a in areas if a['kind'] == 'V']
T = [a for a in areas if a['kind'] == 'T']
generic = [a for a in V if e.is_generic(a['officialName'])]
named = [a for a in V if not e.is_generic(a['officialName'])]
for a in named:
    a['compounds'] = int(a['compounds'])

# ---------------------------------------------------------------------------
# Burkina word lists for the plate rule
GENERIC_EXTRA = ['q', 'lieu-dit']  # "Q Tangonkin": Q = quartier, as name_key already drops it
WEAK_EXTRA = ['peulh', 'peul', 'peuls', 'foulbé', 'foulbe', 'foulbés', 'foulbes', 'mossi', 'silmimossi', 'silmissi',
              'silmiougou', 'rimaïbé', 'rimaibé', 'rimaibe', 'rimaibes', 'yarcé', 'yarce', 'yarse', 'gourmantché',
              'gourmantche', 'bella', 'traditionnel', 'nouveau', 'site', 'village', 'yiri', 'tenga', 'ouro', 'wouro',
              'gold', 'mine', 'station', 'recherche', 'base', 'vie', 'halte', 'silmi', 'naba']
# Big cities a plate name must not equal: Burkina Faso's own, and the capitals and large cities of
# its six neighbours (Mali, Niger, Benin, Togo, Ghana, Côte d'Ivoire) that people in Burkina name daily.
BIG_CITIES = ['Abidjan', 'Lomé', 'Cotonou', 'Accra', 'Bamako', 'Ouagadougou', 'Niamey', 'Kumasi', 'Sikasso', 'Mopti',
              'Ouaga', 'Bobo', 'Fada', 'Bobo-Dioulasso', "Fada N'Gourma"]
AVOID_BASE = ({r['commune'] for r in crows} | {r['province_2025'] for r in crows} | {r['laposte_province'] for r in crows if r['laposte_province']}
              | {r['region_2025'] for r in crows} | {g['nameFr'] for g in regions} | set(BIG_CITIES)) - {''}

# Documented short forms people already say (each with a source). Areas: the place nodes named after
# the two cities whose short form is documented (SOURCES.md, "Short place names").
KNOWN_VILLAGES = {
    'Bobo-Dioulasso': ('Bobo', 'https://en.wikipedia.org/wiki/Bobo_people ("Bobo is also a shortened name of the second-largest city in Burkina Faso, Bobo-Dioulasso")'),
    "Fada N'Gourma": ('Fada', "https://fr.wikipedia.org/wiki/Fada_N%27Gourma (\"les colonisateurs l'appelèrent « Fada »\")"),
}
# A plate name that is only one of these words is no name ("Secteur 4" -> "Secteur", "1200 Logements"
# -> "Logements"): the area takes its commune's name until the commune chooses.
BARE_WORDS = {'secteur', 'zone', 'cite', 'quartier', 'village', 'hameau', 'lotissement', 'logements', 'logement',
              'camp', 'site', 'centre', 'extension'}
KNOWN_TOWNS = {
    'Ouagadougou': ('Ouaga', 'https://en.wikipedia.org/wiki/Ouagadougou ("The city\'s name is often shortened to Ouaga")'),
    'Bobo-Dioulasso': ('Bobo', 'https://en.wikipedia.org/wiki/Bobo_people ("Bobo is also a shortened name of the second-largest city in Burkina Faso, Bobo-Dioulasso")'),
    'Fada-Ngourma': ('Fada', "https://fr.wikipedia.org/wiki/Fada_N%27Gourma (\"les colonisateurs l'appelèrent « Fada »\")"),
}

freq = P.word_freq([a['officialName'] for a in named], LANG)


def hyphen_candidates(cleaned, freq_, taken=lambda k: False):
    """Parts of a hyphenated name that fit, for the commune to choose from (never automatic)."""
    cs = P.candidates(cleaned.replace('-', ' '), LANG, freq_, WEAK_EXTRA)
    cs = [c for c in cs if all(len(w) >= 2 for w in P.content_words(c[0], LANG))]  # never a lone letter
    return [P._cap(c[0], LANG) for c in cs if not taken(e.name_key(c[0]))][:3]


def plate_for(official, own, freq_, known, taken=lambda k: False):
    av = AVOID_BASE - {own}
    r = P.derive(official, LANG, freq_, known=known, avoid=av, generic_extra=GENERIC_EXTRA, weak_extra=WEAK_EXTRA,
                 avoid_key=e.name_key)
    if r['rule'] in ('distinctive', 'cleaned') and re.search(r'\d', official) and not re.search(r'\d', r['plate']):
        r.update(rule='council', needsCouncilChoice=True, reason='the short form drops a number of the official name')
    if r['rule'] == 'distinctive' and e.name_key(r['plate']) == e.name_key(own):
        r.update(needsCouncilChoice=True, reason="the short form is the commune's own name")
    if r['rule'] == 'distinctive' and taken(e.name_key(r['plate'])):
        r.update(rule='council', needsCouncilChoice=True, reason='the short form is already another town word')
    if r['needsCouncilChoice'] and not r['candidates'] and '-' in P.clean(official, LANG, GENERIC_EXTRA, WEAK_EXTRA)[0]:
        cl = P.clean(official, LANG, GENERIC_EXTRA, WEAK_EXTRA)[0]
        hc = hyphen_candidates(cl, freq_, taken)
        if hc:
            r.update(candidates=hc, plate=hc[0], reason='a hyphenated name: every short form drops one of its parts')
    if r['needsCouncilChoice'] and r['candidates'] and taken(e.name_key(r['plate'])):
        ok = [c for c in r['candidates'] if not taken(e.name_key(c))]
        r['plate'] = ok[0] if ok else P.clean(official, LANG, GENERIC_EXTRA, WEAK_EXTRA)[0]
    if r['needsCouncilChoice']:
        r['rule'] = 'council'
    # punctuation never ends or starts a plate name or a candidate ("Kaya-" from "Kaya-Secteur 1")
    tidy = lambda x: re.sub(r"^[^\w]+|[^\w]+$", '', x).strip()
    r['plate'] = tidy(r['plate']) or r['plate']
    r['candidates'] = [c for c in dict.fromkeys(tidy(c) for c in r['candidates']) if c]
    r['fits'] = P.fits(r['plate'], LANG)
    return r


def fallback_plate(r, own, official):
    """A provisional plate name the code can carry: never a digit (SPEC 2.5), never a bare generic word,
    never fewer than 3 letters, never a well-known town elsewhere ("Ouaga" for "Ouaga 2000" is
    Ouagadougou's short form). Otherwise the area takes its commune's name, provisionally."""
    p = r['plate']
    letters = sum(1 for ch in p if ch.isalpha())
    derived = r['rule'] not in ('as-is', 'known')
    bad = (re.search(r'\d', p) or P.plain(p) in BARE_WORDS
           or (r['rule'] not in ('as-is', 'known', 'cleaned') and letters < 3) or (derived and e.name_key(p) in CITY_KEYS and e.name_key(p) != e.name_key(own)))
    if not bad:
        return r
    ok = [c for c in r['candidates'] if not re.search(r'\d', c) and sum(ch.isalpha() for ch in c) >= 3
          and P.plain(c) not in BARE_WORDS and (e.name_key(c) not in CITY_KEYS or e.name_key(c) == e.name_key(own))]
    own = SPELLING.get(e.name_key(own), own)
    own = KNOWN_VILLAGES.get(own, (own,))[0]  # "Fada", not "Fada N'Gourma"
    r.update(plate=own, rule='council', needsCouncilChoice=True, fits=P.fits(own, LANG),
             candidates=list(dict.fromkeys([own] + ok))[:3],
             reason='the short form has a number, a bare generic word or another town\'s name: the commune\'s name until it chooses')
    return r


# ---------------------------------------------------------------------------
# Village plate names
CITY_KEYS = {e.name_key(x) for x in BIG_CITIES}
# a commune's name as its own places spell it ("Pabré", not the boundary file's "Pabre")
_sp = collections.defaultdict(collections.Counter)
for a in named:
    _cl = P.clean(a['officialName'], LANG, GENERIC_EXTRA, WEAK_EXTRA)[0]
    if _cl and not re.search(r'\d', _cl):
        _sp[e.name_key(_cl)][_cl] += 1
SPELLING = {k: max(c.items(), key=lambda kv: (kv[1], sum(ch > '~' for ch in kv[0]), kv[0]))[0] for k, c in _sp.items()}
for a in named:
    own = communes[a['postcode']]['commune']
    known = KNOWN_VILLAGES if a['officialName'] in KNOWN_VILLAGES and e.name_key(own) == e.name_key(a['officialName']) else None
    r = fallback_plate(plate_for(a['officialName'], own, freq, known), own, a['officialName'])
    a['plate'] = r
    a['key'] = e.name_key(r['plate'])
    a['okey'] = e.name_key(a['officialName'])
# a short form equal to the name of another place of the same commune ("Gambo (moulin)" next to
# "Gambo") is not taken automatically: the commune chooses
incommune = collections.defaultdict(set)
for a in named:
    incommune[(a['postcode'], a['key'])].add(a['okey'])
for a in named:
    r = a['plate']
    if r['rule'] in ('cleaned', 'distinctive') and len(incommune[(a['postcode'], a['key'])]) > 1:
        r.update(rule='council', needsCouncilChoice=True, candidates=r['candidates'] or [r['plate']],
                 reason='another place of the same commune has this name')


def cap(d):
    return int(9 * 10 ** (d - 1) * (1 - SPARE))


def ranges(keyf, displayf):
    """Name ranges with the repo's allocation rule; keyf(area) -> key."""
    byname = collections.defaultdict(list)
    for a in sorted(named, key=lambda a: (a['postcode'], a['index'])):
        byname[keyf(a)].append(a)
    split, qualified, entries = [], [], {}

    def place(members):
        blocks, total = [], 0
        for a in members:
            if a['compounds'] == 0:
                continue  # no compound yet: its block comes from the spare at its first compound
            b = e.block_size(a['compounds'])
            blocks.append((a, b))
            total += b
        return blocks, total, next((d for d in (3, 4, 5) if total <= cap(d)), None)

    for key in sorted(byname):
        keep = []
        for a in byname[key]:
            if e.block_size(a['compounds']) > cap(5):
                split.append({'officialName': a['officialName'], 'plateName': displayf(a), 'postcode': a['postcode'],
                              'index': a['index'], 'commune': communes[a['postcode']]['commune'], 'compounds': a['compounds']})
            else:
                keep.append(a)
        if not keep:
            continue
        blocks, total, d = place(keep)
        groups = [(key, keep, None)]
        if d is None:  # combined areas do not fit 5 digits: qualifier for the overflow, decided once
            bare, rest, used = [], [], 0
            for a in keep:
                b = e.block_size(a['compounds']) if a['compounds'] else 0
                if used + b <= cap(5):
                    bare.append(a)
                    used += b
                else:
                    rest.append(a)
            groups = [(key, bare, None)]
            for a in rest:
                q = f"{displayf(a)}-{communes[a['postcode']]['commune']}"
                qualified.append({'plateName': displayf(a), 'qualified': q, 'postcode': a['postcode'], 'index': a['index'],
                                  'compounds': a['compounds']})
                groups.append((e.name_key(q), [a], q))
        for k, ms, qname in groups:
            blocks, total, d = place(ms)
            lo = 10 ** (d - 1)
            cur, bl = lo, []
            for a, b in blocks:
                bl.append([a['postcode'], a['index'], a['compounds'], cur, cur + b - 1])
                cur += b
            spell = collections.Counter(qname or displayf(a) for a in ms)
            entries[k] = {'plateName': spell.most_common(1)[0][0], 'members': ms, 'digits': d, 'range': [lo, 10 ** d - 1],
                          'spareFrom': cur, 'areasWithoutCompounds': [[a['postcode'], a['index']] for a in ms if a['compounds'] == 0],
                          'blocks': bl}
    return entries, split, qualified


def summary(entries):
    rep = {k: v for k, v in entries.items() if len(v['blocks']) + len(v['areasWithoutCompounds']) > 1}
    da, dc = collections.Counter(), collections.Counter()
    for v in entries.values():
        for b in v['blocks']:
            da[v['digits']] += 1
            dc[v['digits']] += b[2]
    tc = sum(dc.values())
    lk, lv = max(rep.items(), key=lambda kv: (kv[1]['spareFrom'] - kv[1]['range'][0], kv[0]))
    return {
        'names': len(entries),
        'repeatedNames': len(rep),
        'areasUnderRepeatedNames': sum(len(v['blocks']) + len(v['areasWithoutCompounds']) for v in rep.values()),
        'mostAreas': sorted(([v['plateName'], len(v['blocks']) + len(v['areasWithoutCompounds'])] for v in rep.values()),
                            key=lambda x: (-x[1], x[0]))[:10],
        'largestSharedRange': {'name': lv['plateName'], 'key': lk, 'areas': len(lv['blocks']),
                               'compounds': sum(b[2] for b in lv['blocks']), 'blocksUsed': lv['spareFrom'] - lv['range'][0],
                               'digits': lv['digits'], 'range': lv['range']},
        'repeatedByDigits': dict(sorted(collections.Counter(v['digits'] for v in rep.values()).items())),
        'areasByDigits': dict(sorted(da.items())),
        'compoundShareByDigits': {k: round(v / tc, 3) for k, v in sorted(dc.items())},
    }


# Before the plate rule: ranges on the official name (the rule of 0.2.0), for the comparison only
before_entries, _, _ = ranges(lambda a: a['okey'], lambda a: a['officialName'])
entries, split, qualified = ranges(lambda a: a['key'], lambda a: a['plate']['plate'])
for i, k in enumerate(sorted(entries)):
    entries[k] = dict(id=i + 1, **entries[k])

# aliases: official name -> plate name, when it maps to one plate name only
claims = collections.defaultdict(set)
for k, v in entries.items():
    for a in v['members']:
        if a['okey'] != k and a['okey']:
            claims[a['okey']].add(k)
aliases, dropped = {}, []
for ak, ks in sorted(claims.items()):
    offs = sorted({a['officialName'] for k in ks for a in entries[k]['members'] if a['okey'] == ak})
    if ak in entries:
        dropped.append({'official': offs, 'key': ak, 'claimedBy': sorted(entries[k]['plateName'] for k in ks),
                        'why': 'is itself the plate name of other areas'})
    elif len(ks) > 1:
        dropped.append({'official': offs, 'key': ak, 'claimedBy': sorted(entries[k]['plateName'] for k in ks),
                        'why': 'claimed by two plate names'})
    else:
        aliases[ak] = next(iter(ks))

# ---------------------------------------------------------------------------
# Town words: the commune name (plate rule applies); three names carried by two communes each take
# the province, then the plate rule decides or flags.
PROVINCE_SAID = {'Sandbondtenga': 'Sanmatenga', 'Boulkiemde': 'Boulkiemdé'}  # 2025 province name -> the name people say
cnt = collections.Counter(e.name_key(r['commune']) for r in communes.values())
tfreq = P.word_freq([r['commune'] for r in crows], LANG)
all_commune_keys = set(cnt)
towns, tchosen = {}, {}
# first pass: names that fit as they are, and the known short forms
for pc, r in sorted(communes.items()):
    if not pc:
        continue
    w = r['commune']
    if cnt[e.name_key(w)] > 1:
        w = f"{w}-{PROVINCE_SAID.get(r['province_2025'], r['province_2025'])}"
    tchosen[pc] = w
fixed = {e.name_key(tchosen[pc]) for pc in tchosen if P.fits(tchosen[pc], LANG) or communes[pc]['commune'] in KNOWN_TOWNS}
used_t = set()
tplates = {}
for pc in sorted(tchosen, key=lambda pc: (not (P.fits(tchosen[pc], LANG) or communes[pc]['commune'] in KNOWN_TOWNS), pc)):
    w = tchosen[pc]
    official = communes[pc]['commune']
    known = {w: KNOWN_TOWNS[official]} if official in KNOWN_TOWNS else None
    avoid_k = {e.name_key(x) for x in AVOID_BASE - {official}}
    taken = lambda k, me=e.name_key(w), av=avoid_k: (k != me and (k in all_commune_keys or k in used_t or k in fixed or k in av))
    r = plate_for(w, official, tfreq, known, taken)
    used_t.add(e.name_key(r['plate']))
    tplates[pc] = r
for pc, r in sorted(tplates.items()):
    w, official = tchosen[pc], communes[pc]['commune']
    al = {w} | ({official} if cnt[e.name_key(official)] == 1 else set())  # a shared bare name is no alias
    al = {x for x in al if e.name_key(x) != e.name_key(r['plate'])}
    t = {'word': r['plate'], 'official': official, 'aliases': sorted(al), 'plateRule': r['rule']}
    if r.get('source'):
        t['source'] = r['source']
    if r['needsCouncilChoice']:
        t.update(needsCouncilChoice=True, plateCandidates=r['candidates'][:3], plateReason=r.get('reason'))
    towns[pc] = t
# an alias claimed by two towns, or equal to another town's word, is dropped
akeys = collections.Counter(e.name_key(x) for t in towns.values() for x in t['aliases'])
wkeys = {e.name_key(t['word']) for t in towns.values()}
town_dropped = []
for pc, t in towns.items():
    keep = []
    for x in t['aliases']:
        if akeys[e.name_key(x)] > 1 or e.name_key(x) in wkeys:
            town_dropped.append({'alias': x, 'postcode': pc})
        else:
            keep.append(x)
    t['aliases'] = keep
assert len({e.name_key(t['word']) for t in towns.values()}) == len(towns)

# ---------------------------------------------------------------------------
# Stats
rules = collections.Counter(a['plate']['rule'] for a in named)
flag = [a for a in named if a['plate']['needsCouncilChoice']]
over_c = [a for a in named if P.plate_length(a['officialName']) > P.MAX_CHARS]
over_w = [a for a in named if P.word_count(a['officialName'], LANG) > P.MAX_WORDS]
over_any = [a for a in named if not P.fits(a['officialName'], LANG)]
still_over = [a for a in flag if not a['plate']['fits']]


def code_len(name, digits):
    return P.plate_length(name) + 1 + {3: 3, 4: 5, 5: 6}[digits]


longest = {'all': None, 'notFlagged': None}
for k, v in entries.items():
    for a in v['members']:
        if a['compounds'] == 0:
            continue
        L = code_len(a['plate']['plate'], v['digits'])
        blk = next(b for b in v['blocks'] if (b[0], b[1]) == (a['postcode'], a['index']))
        txt = f"{a['plate']['plate']} {e.group_number(blk[4])}"
        for which in ('all', 'notFlagged'):
            if which == 'notFlagged' and a['plate']['needsCouncilChoice']:
                continue
            if longest[which] is None or L > longest[which][1]:
                longest[which] = (txt, L, a['officialName'])
tw_long = max(towns.values(), key=lambda t: P.plate_length(t['word']))
tw_long_ok = max((t for t in towns.values() if not t.get('needsCouncilChoice')), key=lambda t: P.plate_length(t['word']))

bs = summary(before_entries)
af = summary(entries)
stats = {
    'source': 'model/stats/area-compounds.csv (the register\'s areas with the compounds grouped at first issue, 20 October 2026)',
    'normalisation': 'bf_engine.name_key of the plate name',
    'plateRule': {'maxChars': P.MAX_CHARS, 'maxWords': P.MAX_WORDS, 'lang': LANG, 'tool': 'engine/reference/plate_names.py'},
    'spare': SPARE,
    'villageAreas': len(V), 'genericLabels': len(generic), 'genericCompounds': sum(int(a['compounds']) for a in generic),
    'namedAreas': len(named),
    'plates': {
        'officialOverChars': len(over_c), 'officialOverWords': len(over_w), 'officialOverLimit': len(over_any),
        'byRule': dict(sorted(rules.items())),
        'autoShortened': {r: rules.get(r, 0) for r in ('cleaned', 'abbreviated', 'known', 'distinctive')},
        'needsCouncilChoice': len(flag),
        'needsCouncilChoiceByReason': dict(collections.Counter(a['plate'].get('reason') for a in flag).most_common()),
        'stillOverLimit': len(still_over),
        'stillOverLimitWithDigit': sum(1 for a in still_over if re.search(r'\d', a['plate']['plate'])),
        'aliases': len(aliases), 'droppedAliases': len(dropped),
        'longestVillageCode': {'text': longest['all'][0], 'length': longest['all'][1], 'official': longest['all'][2]},
        'longestVillageCodeNotFlagged': {'text': longest['notFlagged'][0], 'length': longest['notFlagged'][1],
                                         'official': longest['notFlagged'][2]},
        'longestTownWord': tw_long['word'], 'longestTownWordNotFlagged': tw_long_ok['word'],
        'longestSecteurCode': f"Secteur 55 {tw_long['word']} · 99 999",
        'longestSecteurCodeNotFlagged': f"Secteur 55 {tw_long_ok['word']} · 99 999",
    },
    'beforePlateRule': bs,
    **af,
    'raisedByRule': None,
    'splitBeforeIssue': split, 'qualified': qualified,
    'townNodes': len(T), 'townCompounds': sum(int(a['compounds']) for a in T),
    'townWords': {'communes': len(towns), 'byRule': dict(sorted(collections.Counter(t['plateRule'] for t in towns.values()).items())),
                  'needsCouncilChoice': {pc: {'official': t['official'], 'provisional': t['word'], 'candidates': t['plateCandidates'],
                                              'reason': t['plateReason']} for pc, t in towns.items() if t.get('needsCouncilChoice')},
                  'stillOverLimit': sorted(t['word'] for t in towns.values() if not P.fits(t['word'], LANG)),
                  'droppedAliases': town_dropped},
}
stats['raisedByRule'] = sum(1 for v in entries.values() for b in v['blocks']
                            if v['digits'] > next(d for d in (3, 4, 5) if b[2] * 2 <= 9 * 10 ** (d - 1)))

# ---------------------------------------------------------------------------
# Write
out = os.path.join(REPO, 'model', 'areas')
names_out = {}
for k, v in sorted(entries.items()):
    offs = sorted({a['officialName'] for a in v['members']})
    names_out[k] = {'id': v['id'], 'plateName': v['plateName'], 'officialNames': offs,
                    'aliases': sorted(o for o in offs if aliases.get(e.name_key(o)) == k),
                    'digits': v['digits'], 'range': v['range'], 'spareFrom': v['spareFrom'],
                    'areasWithoutCompounds': v['areasWithoutCompounds'], 'blocks': v['blocks']}
    if any(a['plate']['needsCouncilChoice'] for a in v['members']):
        names_out[k]['needsCouncilChoice'] = True
json.dump({'rule': 'one national number range per normalised PLATE name, frozen blocks per area (SPEC 2.4, 2.5)',
           'plateRule': 'at most 12 characters and 2 words (engine/reference/plate_names.py)',
           'spare': SPARE, 'version': '1.0 (frozen at first issue, 20 October 2026; OpenStreetMap and GeoNames names)',
           'aliasKeys': dict(sorted(aliases.items())), 'droppedAliases': dropped,
           'names': names_out}, open(os.path.join(out, 'name-ranges.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
json.dump(towns, open(os.path.join(out, 'town-words.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

# register: plate fields on every village (generic labels get none: they are renamed first)
reg_path = os.path.join(out, 'register.json')
reg = json.load(open(reg_path, encoding='utf-8'))
byarea = {(a['postcode'], a['index']): a for a in named}
for pc, c in reg.items():
    for v in c['villages']:
        a = byarea.get((pc, v['index']))
        for f in ('plateName', 'plateRule', 'needsCouncilChoice', 'plateCandidates', 'plateReason'):
            v.pop(f, None)
        if a is None:
            v['plateRule'] = 'generic label: renamed with the commune before issue'
            continue
        r = a['plate']
        v['plateName'] = r['plate']
        v['plateRule'] = r['rule']
        if r['needsCouncilChoice']:
            v.update(needsCouncilChoice=True, plateCandidates=r['candidates'][:3], plateReason=r.get('reason'))
json.dump(reg, open(reg_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(stats, open(os.path.join(REPO, 'model', 'stats', 'name-stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in stats.items() if k not in ('splitBeforeIssue',)}, ensure_ascii=False, indent=1))
