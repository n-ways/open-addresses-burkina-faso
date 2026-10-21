#!/usr/bin/env python3
"""N-Ways address engine for Burkina Faso: reference implementation (standard library only).

This file is the executable form of engine/SPEC.md. It is not a shared library: it exists
for Burkina Faso only.

What it does
  * machine form   BF-<La Poste postcode>-V<area index>-<number>-<Damm check digit>, for systems
  * remembered form "Bissiga 16 870": the area's plate name and a number of 3 to 5 digits, unique in
                   the whole country on its own (one national number range per plate name, a frozen
                   block per area, so the number says which Bissiga). The plate name has at most
                   12 characters and 2 words and no digit (plate_names.py); the official name is
                   printed small and, typed, still decodes when it maps to one plate name. Secteur
                   forms ("Secteur 15 Ouaga · 48 217") are refused: no secteur map is public
  * spot code      BF-<postcode> E<east> N<north>: metres east/north of the commune frame
                   origin in 10 m units (4 digits per axis, 5 where the commune is wider than 99.99 km);
                   a point in no outline takes the nearest commune within 10 km (spot_commune)
  * commune lookup (point in polygon over model/units/communes.geojson) -> La Poste postcode
  * registry       groups footprints into compounds (concessions), orders compounds along a
                   Hilbert curve and issues numbers with infill gaps and a tail reserve;
                   provisional numbers for new homes ("Ajouter ma maison")

Command line
  bf_engine.py spot LAT LON            spot code + commune + postcode for a point
  bf_engine.py unspot "BF-10000 E1811 N1309"
  bf_engine.py check BF-10000-V064-1776     -> full machine code with its check digit
  bf_engine.py verify BF-10000-V064-1776-9
  bf_engine.py resolve Bobo 26 206     remembered form -> machine form, no context needed
  bf_engine.py frames                  (re)build model/units/frames.json (frozen once published)
  bf_engine.py registry CSV DIGITS     group + number a sample of footprints (sample-ouaga-*.csv)
"""
import csv, json, math, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_names  # noqa: E402  (the plate-name rule: at most 12 characters, 2 words)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
UNITS = os.path.join(REPO, 'model', 'units')


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _read_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_json(obj, path, **kw):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, **kw)

# ---------------------------------------------------------------------------
# Damm check digit (H. M. Damm, 2004): a weakly totally anti-symmetric quasigroup of
# order 10. Detects every single-digit error and every adjacent transposition.
DAMM = [
    [0, 3, 1, 7, 5, 9, 8, 6, 4, 2],
    [7, 0, 9, 2, 1, 5, 4, 8, 6, 3],
    [4, 2, 0, 6, 8, 7, 1, 3, 5, 9],
    [1, 7, 5, 0, 9, 8, 3, 4, 2, 6],
    [6, 1, 2, 3, 0, 4, 5, 9, 7, 8],
    [3, 6, 7, 4, 2, 0, 9, 5, 8, 1],
    [5, 8, 6, 9, 7, 2, 0, 1, 3, 4],
    [8, 9, 4, 5, 3, 6, 2, 0, 1, 7],
    [9, 4, 3, 8, 6, 1, 7, 2, 0, 5],
    [2, 5, 8, 1, 4, 3, 6, 7, 9, 0],
]


def damm(digits):
    i = 0
    for d in digits:
        i = DAMM[i][int(d)]
    return i


KIND_DIGIT = {'S': '1', 'V': '2'}  # secteur (town) / village; part of the checked string

# ---------------------------------------------------------------------------
# National names (SPEC 2.4): "Bissiga 16 870" must name one place in the whole
# country on its own. Every village with the same normalised name draws from one national range
# for that name, cut into frozen blocks, one per area (SPEC 2.4). Secteur codes carry the town word.

NAME_SPARE = 0.1  # top tenth of every name's range: blocks for areas that will carry the name later


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).upper()


GENERIC_RE = re.compile(r"^\s*(village|campe?m\w*|camp\b|site\b|hameau\s*$|ferme\b|chantier\b|zone\b)", re.I)


def is_generic(name):
    """Labels that are not place names ("village", "Campement d'éleveurs", "Site de recasement"):
    renamed with the commune before issue; they never get a block."""
    return bool(GENERIC_RE.match(name))


def name_key(name):
    """Normalised name for Burkina (French spelling of Mooré, Dioula, Fulfulde, Gulmancema names):
    accents and case folded; a leading "Q"/"Quartier"/"Hameau"/"Village de" and the French articles
    le/la/les/l' dropped; spaces, hyphens, apostrophes and dots dropped; the French/Africanist
    spelling pairs folded: tch=c, dj=j, gh=g, ph=f, ou=w=u, gu before i/e = g; doubled letters single.
    So Douré = Doure, Ouatinoma = Watinoma = Wattinooma, Goghin = Gogin, Tanguin = Tanghin, Sanga = Sangha.
    St/Ste expand to Saint/Sainte. Qualifiers that are part of the name stay ("Bissiga-Peulh" != "Bissiga")."""
    s = _fold(name)
    # standard saint abbreviations of a plate name expand back: "St-Camille" = "Saint-Camille"
    s = re.sub(r"(?<![A-Z])STE(?![A-Z])\.?", 'SAINTE', s)
    s = re.sub(r"(?<![A-Z])ST(?![A-Z])\.?", 'SAINT', s)
    s = re.sub(r"^(Q|QUARTIER|HAMEAU|VILLAGE DE|VILLAGE)[\s\-.]+", '', s)
    s = re.sub(r"^(LES|LE|LA)\s+|^L'", '', s)
    s = re.sub(r"[^A-Z0-9]", '', s)
    for a, b in (('TCH', 'C'), ('DJ', 'J'), ('GH', 'G'), ('PH', 'F'), ('OU', 'U'), ('W', 'U')):
        s = s.replace(a, b)
    s = re.sub(r'GU(?=[IE])', 'G', s)  # French gu before i/e: Tanguin = Tanghin = Tangin
    return re.sub(r'([A-Z])\1+', r'\1', s)  # doubled letters single; digits stay ("Ouaga 2000" is not "Ouaga 20")


PLATE_LANG = 'fr'


def floors_from_height(h):
    """Floors from an OpenStreetMap height (m): h / 3, rounded, at least 1. The Google/Microsoft
    height is a rendering filler and never gives floors (SPEC 8.1)."""
    return max(1, int(round(h / 3.0)))


def plate_ok(name):
    """A plate name (village name or town word in the code): at most 12 characters (an accented
    letter, a hyphen or an apostrophe count one) and 2 words (de/du/des/la... do not count), no digit."""
    return plate_names.fits(name, PLATE_LANG)


def block_size(compounds):
    """Block of one area in its name's range: twice today's compounds (room to grow), rounded up
    to a multiple of 10, at least 20."""
    return max(20, -(-2 * int(compounds) // 10) * 10)


_NAMES = None
_TOWNS = None


def names():
    """model/areas/name-ranges.json, indexed: plate key -> entry, (postcode, index) -> (key, block), and
    official-name key -> plate key (aliases that map to one plate name only)."""
    global _NAMES
    if _NAMES is None:
        d = _load_json(os.path.join(REPO, 'model', 'areas', 'name-ranges.json'))['names']
        by_area = {}
        for k, v in d.items():
            for pc, ix, _c, lo, hi in v['blocks']:
                by_area.setdefault((pc, ix), []).append((k, lo, hi))
            for pc, ix in v['areasWithoutCompounds']:
                by_area.setdefault((pc, ix), [])
                by_area[(pc, ix)].append((k, None, None))
        aliases = _load_json(os.path.join(REPO, 'model', 'areas', 'name-ranges.json')).get('aliasKeys', {})
        _NAMES = {'names': d, 'byArea': by_area, 'aliases': aliases}
    return _NAMES


def towns():
    global _TOWNS
    if _TOWNS is None:
        t = _load_json(os.path.join(REPO, 'model', 'areas', 'town-words.json'))
        by = {}
        for pc, v in t.items():
            for w in [v['word']] + v['aliases']:
                by[name_key(w)] = pc
        _TOWNS = {'byPostcode': t, 'byWord': by}
    return _TOWNS


def area_name(postcode, index):
    """(key, entry) of the national name a village area carries."""
    hits = names()['byArea'].get((str(postcode), str(index)))
    if not hits:
        raise ValueError(f'no village V{index} in commune {postcode}')
    k = hits[0][0]
    return k, names()['names'][k]


def name_id(postcode, index):
    return area_name(postcode, index)[1]['id']


def check_input(postcode, kind, place, number, nid=None):
    """Digits under the Damm check. Village: the frozen national name id (5 digits) + postcode +
    kind + index + number, so the check binds name, area and number together. Secteur: postcode +
    kind + secteur + number (the postcode is the commune, i.e. the town word)."""
    if kind == 'V':
        if nid is None:
            nid = name_id(postcode, place)
        return f'{int(nid):05d}{postcode}{KIND_DIGIT[kind]}{place}{number}'
    return f'{postcode}{KIND_DIGIT[kind]}{place}{number}'


def machine(postcode, kind, place, number, nid=None):
    """BF-10000-S15-48217-c. place: 2 digits for a secteur, 3 for a village."""
    postcode, place, number = str(postcode), str(place), str(number)
    if not re.fullmatch(r'\d{5}', postcode):
        raise ValueError('postcode must be the 5-digit La Poste code')
    if kind == 'S' and not re.fullmatch(r'\d{2}', place):
        raise ValueError('secteur is 2 digits')
    if kind == 'V' and not re.fullmatch(r'\d{3}', place):
        raise ValueError('village index is 3 digits')
    if not re.fullmatch(r'[1-9]\d{2,4}', number):
        raise ValueError('number is 3-5 digits without a leading zero')
    c = damm(check_input(postcode, kind, place, number, nid))
    return f'BF-{postcode}-{kind}{place}-{number}-{c}'


MACHINE_RE = re.compile(r'^BF-(\d{5})-([SV])(\d{2,3})-([1-9]\d{2,4})(?:-(\d))?$')


def parse_machine(code, nid=None):
    m = MACHINE_RE.match(code.strip().upper().replace(' ', ''))
    if not m:
        raise ValueError(f'not a Burkina N-Ways code: {code!r}')
    postcode, kind, place, number, c = m.groups()
    if (kind == 'S') != (len(place) == 2):
        raise ValueError('S takes 2 digits, V takes 3')
    if kind == 'S' and nid is None:
        raise ValueError('secteur codes are not issued: a town\'s homes have the code of their quarter')
    ok = c is None or damm(check_input(postcode, kind, place, number, nid)) == int(c)
    in_area = None
    if kind == 'V' and nid is None:
        # the number must lie in one of this village's blocks of its name's range
        hits = names()['byArea'].get((postcode, place), [])
        in_area = any(lo is not None and lo <= int(number) <= hi for _k, lo, hi in hits)
        ok = ok and in_area
    return {'postcode': postcode, 'kind': kind, 'place': place, 'number': number,
            'check': int(c) if c is not None else None, 'valid': ok, 'inArea': in_area}


def block_of(key, number):
    """The area (postcode, index) whose block holds this number in the name's range, or None."""
    n = int(number)
    for pc, ix, _c, lo, hi in names()['names'][key]['blocks']:
        if lo <= n <= hi:
            return pc, ix
    return None


CHECK_TAIL = r'(?:\s*-\s*(\d))?'  # optional check digit where the code is written: "Bissiga 16 870-9"
REMEMBERED_S = re.compile(r'^\s*secteur\s+(\d{1,2})\s+([^\d\s].*?)\s*[·.,:\-]?\s*([1-9][\d ]{2,6}?)' + CHECK_TAIL + r'\s*$', re.I)
REMEMBERED_V = re.compile(r'^\s*(.+?)\s+([1-9][\d ]{2,6}?)' + CHECK_TAIL + r'\s*$')


def _check_tail(res, c):
    if c is not None and int(c) != int(res['code'][-1]):
        raise ValueError(f'check digit {c} does not match {res["area"]} {res["number"]}: mistyped name or number')
    res['checked'] = c is not None
    return res


def resolve_remembered(text):
    """Remembered form -> machine form, with no context: no position, no commune asked.
    "Secteur 15 Ouaga · 48 217" (town word is part of the code) or "Bissiga 16 870" (the number says
    which Bissiga). Returns the machine code and the area, or raises ValueError."""
    t = text.replace('·', ' ').strip()
    if re.match(r'^\s*secteur\b', t, re.I):
        # no secteur map is public: a town's homes carry the code of their quarter (SPEC 2.2)
        raise ValueError('secteur codes are not issued: say the quarter or village and its number')
    m = REMEMBERED_S.match(t)
    if m:
        sec, town, num = m.group(1), m.group(2), m.group(3).replace(' ', '')
        pc = towns()['byWord'].get(name_key(town))
        if pc is None:
            raise ValueError(f'unknown town word {town!r}: say the commune ("Secteur 15 Ouaga")')
        return _check_tail({'code': machine(pc, 'S', f'{int(sec):02d}', num), 'postcode': pc, 'kind': 'S',
                            'place': f'{int(sec):02d}', 'number': num,
                            'area': f'Secteur {int(sec)} {towns()["byPostcode"][pc]["word"]}'}, m.group(4))
    if re.match(r'^\s*secteur\b', t, re.I):
        raise ValueError('a secteur code needs its town word: "Secteur 15 Ouaga · 48 217"')
    m = REMEMBERED_V.match(t)
    if not m:
        raise ValueError(f'not a remembered Burkina address: {text!r}')
    key, num = name_key(m.group(1)), m.group(2).replace(' ', '')
    via = None
    if key not in names()['names'] and key in names()['aliases']:
        via, key = m.group(1), names()['aliases'][key]  # the official name typed: decodes to its plate name
    entry = names()['names'].get(key)
    if entry is None:
        raise ValueError(f'unknown place name {m.group(1)!r}')
    if len(num) != entry['digits']:
        raise ValueError(f'{m.group(1).strip()} numbers have {entry["digits"]} digits')  # the name typed
    hit = block_of(key, num)
    if hit is None:
        raise ValueError(f'{entry["plateName"]} {num} is not issued (spare or free space)')
    pc, ix = hit
    res = {'code': machine(pc, 'V', ix, num, entry['id']), 'postcode': pc, 'kind': 'V', 'place': ix,
           'number': num, 'area': entry['plateName'], 'nameId': entry['id']}
    if via:
        res['typedOfficialName'] = via
    return _check_tail(res, m.group(3))


def group_number(number):
    """How the number is written and said: 3 digits '217', 4 digits '48 17', 5 digits '48 217'."""
    n = str(number)
    if len(n) == 4:
        return f'{n[:2]} {n[2:]}'
    if len(n) == 5:
        return f'{n[:2]} {n[2:]}'
    return n


def remembered(area_name, number, kind, town=None, provisional=False):
    """The form people remember: no letters to learn, no check digit, unique in the whole country
    on its own: the area's plate name, whose national range says which area ("Bissiga 16 870")."""
    if kind == 'S':
        raise ValueError('secteur codes are not issued (SPEC 2.2): no secteur map is public')
    if not plate_ok(area_name) and not provisional:
        # a provisional name the commune may still shorten is issued as it is (SPEC 2.5)
        raise ValueError(f'plate name {area_name!r} is over the plate limit (12 characters, 2 words): the commune chooses its short form')
    return f'{area_name} {group_number(number)}'


FR_UNITS = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix',
            'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize']
FR_TENS = {2: 'vingt', 3: 'trente', 4: 'quarante', 5: 'cinquante', 6: 'soixante'}


def fr_0_99(n):
    if n <= 16:
        return FR_UNITS[n]
    if n < 20:
        return 'dix-' + FR_UNITS[n - 10]
    t, u = divmod(n, 10)
    if t in (7, 9):  # Burkina says soixante-dix / quatre-vingt-dix (no septante/nonante)
        base = 'soixante' if t == 7 else 'quatre-vingt'
        rest = n - (60 if t == 7 else 80)
        return base + ('-et-onze' if rest == 11 and t == 7 else '-' + fr_0_99(rest))
    if t == 8:
        return 'quatre-vingts' if u == 0 else 'quatre-vingt-' + FR_UNITS[u]
    w = FR_TENS[t]
    if u == 0:
        return w
    return w + ('-et-un' if u == 1 else '-' + FR_UNITS[u])


def say_fr(number):
    """Spoken French by groups, as phone numbers are read: '48 17' -> 'quarante-huit dix-sept'."""
    out = []
    for g in group_number(number).split(' '):
        if len(g) == 3:
            h, r = divmod(int(g), 100)
            out.append(('cent' if h == 1 else FR_UNITS[h] + ' cent') + ('' if r == 0 else ' ' + fr_0_99(r)))
        else:
            out.append(fr_0_99(int(g)))
    return ' '.join(out)


# ---------------------------------------------------------------------------
# Communes, postcodes, frames

def _rings(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates']]
    return geom['coordinates']


def _inside(x, y, polys):
    for poly in polys:
        ins = False
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    ins = not ins
                j = i
        if ins:
            return True
    return False


_COMMUNES = None


def communes():
    """[(pcode, name, polys, box)] with La Poste postcode from communes.csv."""
    global _COMMUNES
    if _COMMUNES is None:
        pc = {r['pcode']: r for r in _read_csv(os.path.join(UNITS, 'communes.csv'))}
        g = _load_json(os.path.join(UNITS, 'communes.geojson'))
        out = []
        for f in g['features']:
            polys = _rings(f['geometry'])
            xs = [p[0] for poly in polys for p in poly[0]]
            ys = [p[1] for poly in polys for p in poly[0]]
            p = f['properties']
            out.append({'pcode': p['pcode'], 'name': p['name'], 'polys': polys,
                        'box': (min(xs), min(ys), max(xs), max(ys)),
                        'postcode': pc.get(p['pcode'], {}).get('laposte_postcode') or None})
        _COMMUNES = out
    return _COMMUNES


def commune_at(lat, lon):
    for c in communes():
        x0, y0, x1, y1 = c['box']
        if x0 <= lon <= x1 and y0 <= lat <= y1 and _inside(lon, lat, c['polys']):
            return c
    return None


M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQ = 111320.0
UNIT_M = 10.0


def frame_for_box(box):
    """Frame of a commune: origin = box SW corner floored to 0.01 degree; reference latitude =
    box centre rounded to 0.01 degree; digits per axis = 4 if the frame spans <= 99,990 m, else 5."""
    x0, y0, x1, y1 = box
    lon0 = math.floor(x0 * 100) / 100
    lat0 = math.floor(y0 * 100) / 100
    latc = round((y0 + y1) / 2, 2)
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(latc))
    w = (x1 - lon0) * kx
    h = (y1 - lat0) * M_PER_DEG_LAT
    return {'lon0': lon0, 'lat0': lat0, 'latc': latc,
            'dx': 4 if w < 99990 else 5, 'dy': 4 if h < 99990 else 5}


_FRAMES = None


def frames():
    global _FRAMES
    if _FRAMES is None:
        p = os.path.join(UNITS, 'frames.json')
        _FRAMES = _load_json(p) if os.path.exists(p) else {}
    return _FRAMES


def build_frames():
    out = {}
    for c in communes():
        if not c['postcode']:
            continue
        f = frame_for_box(c['box'])
        f['commune'] = c['name']
        f['pcode'] = c['pcode']
        out[c['postcode']] = f
    _write_json(dict(sorted(out.items())), os.path.join(UNITS, 'frames.json'),
              ensure_ascii=False, indent=1)
    return out


# A point in no commune outline (a gap between two outlines, or just over a border line) takes
# the commune with the nearest outline within SPOT_OUTLINE_M whose frame holds it; else the one
# with the nearest outline within SPOT_OUTLINE_M whose frame it lies at most SPOT_NEAR_CELLS
# beyond on each axis, and the frame's nearest edge cell (SPEC 5.1). Frames never move.
SPOT_OUTLINE_M = 10000.0   # every issued compound lies within 8,566 m of an outline
SPOT_NEAR_CELLS = 300      # 3,000 m; the farthest issued compound lies 14 cells beyond its frame


_COS_TERMS = (2.08767569878681e-09, -2.755731922398589e-07, 2.48015873015873e-05,
              -0.001388888888888889, 0.041666666666666664, -0.5)


def cos_lat(lat):
    """cos(latitude) as a fixed Taylor polynomial (to r^12; error under 1e-8 at any latitude),
    so that every port computes the same double, operation for operation, whatever its math
    library."""
    r = lat * 0.017453292519943295
    r2 = r * r
    p = _COS_TERMS[0]
    for k in _COS_TERMS[1:]:
        p = k + r2 * p
    return 1.0 + r2 * p


def edge_d2(lat, lon, polys):
    """Squared distance from a point to the nearest edge of any ring of an outline, in degrees
    of latitude, with longitude differences scaled by cos_lat(latitude of the point)."""
    c = cos_lat(lat)
    best = math.inf
    for poly in polys:
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                ax, ay = (ring[j][0] - lon) * c, ring[j][1] - lat
                vx, vy = (ring[i][0] - lon) * c - ax, (ring[i][1] - lat) - ay
                ll = vx * vx + vy * vy
                t = 0.0
                if ll > 0:
                    t = min(1.0, max(0.0, -(ax * vx + ay * vy) / ll))
                px, py = ax + t * vx, ay + t * vy
                d = px * px + py * py
                if d < best:
                    best = d
                j = i
    return best


def spot_cells(lat, lon, f):
    """(east, north) cell of a point in a commune frame; either may fall outside the frame."""
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
    return (int(math.floor((lon - f['lon0']) * kx / UNIT_M)),
            int(math.floor((lat - f['lat0']) * M_PER_DEG_LAT / UNIT_M)))


def _beyond(v, digits):
    """Cells by which an index lies outside 0 .. 10^digits - 1 (0 inside)."""
    if v < 0:
        return -v
    return max(0, v - (10 ** digits - 1))


def spot_frame_beyond(lat, lon, f):
    e, n = spot_cells(lat, lon, f)
    return max(_beyond(e, f['dx']), _beyond(n, f['dy']))


def nearest_spot_commune(lat, lon, outlines, frames_by_pc):
    """The spot commune of a point in no outline (SPEC 5.1). outlines: [(postcode, polys, box)];
    frames_by_pc: postcode -> frame. Among the communes whose outline lies within SPOT_OUTLINE_M,
    those whose frame holds the point come first, then those whose frame it lies at most
    SPOT_NEAR_CELLS beyond; then the nearest outline, then the lower postcode. None: refused."""
    lim = SPOT_OUTLINE_M / M_PER_DEG_LAT
    lim = lim * lim
    my = 2 * SPOT_OUTLINE_M / M_PER_DEG_LAT
    mx = my / max(cos_lat(lat), 0.01)
    best = None
    for pc, polys, box in outlines:
        f = frames_by_pc.get(pc) if pc else None
        if f is None:
            continue
        over = spot_frame_beyond(lat, lon, f)
        if over > SPOT_NEAR_CELLS:
            continue
        x0, y0, x1, y1 = box
        if lon < x0 - mx or lon > x1 + mx or lat < y0 - my or lat > y1 + my:
            continue
        d = edge_d2(lat, lon, polys)
        if d > lim:
            continue
        k = (over > 0, d, pc)
        if best is None or k < best:
            best = k
    return best[2] if best else None


def spot_commune(lat, lon):
    """Postcode of the commune whose frame gives a point its spot code: the commune holding it,
    else nearest_spot_commune. None: refused."""
    c = commune_at(lat, lon)
    if c is not None and c['postcode']:
        return c['postcode']
    return nearest_spot_commune(lat, lon, [(c['postcode'], c['polys'], c['box']) for c in communes()], frames())


def spot_encode(lat, lon, postcode=None):
    """Spot code of a point; postcode: the commune whose frame to use (default: spot_commune). A
    point at most SPOT_NEAR_CELLS beyond the frame takes its nearest edge cell."""
    if postcode is None:
        postcode = spot_commune(lat, lon)
        if postcode is None:
            raise ValueError('point is in no commune, and no commune within 10 km has a frame within 3,000 m')
    f = frames()[postcode]
    e, n = spot_cells(lat, lon, f)
    if max(_beyond(e, f['dx']), _beyond(n, f['dy'])) > SPOT_NEAR_CELLS:
        raise ValueError('point is more than 3,000 m beyond the commune frame')
    e = min(max(e, 0), 10 ** f['dx'] - 1)
    n = min(max(n, 0), 10 ** f['dy'] - 1)
    return f'BF-{postcode} E{e:0{f["dx"]}d} N{n:0{f["dy"]}d}'


SPOT_RE = re.compile(r'^BF-?(\d{5})\s*E(\d{4,5})\s*N(\d{4,5})$')


def spot_decode(code):
    m = SPOT_RE.match(code.strip().upper())
    if not m:
        raise ValueError(f'not a Burkina spot code: {code!r}')
    postcode, e, n = m.group(1), m.group(2), m.group(3)
    f = frames()[postcode]
    if len(e) != f['dx'] or len(n) != f['dy']:
        raise ValueError('wrong number of digits for this commune frame')
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
    lon = f['lon0'] + (int(e) + 0.5) * UNIT_M / kx
    lat = f['lat0'] + (int(n) + 0.5) * UNIT_M / M_PER_DEG_LAT
    return round(lat, 7), round(lon, 7)


# ---------------------------------------------------------------------------
# Registry: compounds and numbers

def gap_m(a, b):
    """Gap between two footprints, approximated from centroids and areas (the production build uses
    true polygon distance): centre distance minus the radii of equal-area discs."""
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians((a['cy'] + b['cy']) / 2))
    d = math.hypot((a['cx'] - b['cx']) * kx, (a['cy'] - b['cy']) * M_PER_DEG_LAT)
    return d - math.sqrt(a['area'] / math.pi) - math.sqrt(b['area'] / math.pi)


BF_RULES = {'annex_m2': 25.0, 'attach_m': 8.0, 'hut_m2': 40.0, 'hut_gap_m': 3.0, 'hut_max': 25,
            'enclosure_max_m2': 6000.0}


def group_compounds(buildings, rules=BF_RULES):
    """buildings: list of dicts id, cx, cy, area, eid (enclosure id or None), ea (enclosure m2).
    Returns list of compounds: {'members': [ids], 'rule': ..., 'confidence': ...}.
    Order of rules (SPEC 5.2): mapped enclosure, annex attach, hut cluster, single."""
    by = {b['id']: b for b in buildings}
    parent = {i: i for i in by}
    rule = {i: 'single' for i in by}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    encl = {}
    for b in buildings:
        if b.get('eid') is not None and (b.get('ea') or 0) <= rules['enclosure_max_m2']:
            encl.setdefault(b['eid'], []).append(b['id'])
    for ms in encl.values():
        for m in ms:
            parent[find(m)] = find(ms[0])
            rule[m] = 'enclosure'
    # neighbour lists (grid of ~12 m)
    cell = 0.00011
    grid = {}
    for b in buildings:
        grid.setdefault((int(b['cx'] // cell), int(b['cy'] // cell)), []).append(b['id'])

    def near(b):
        gx, gy = int(b['cx'] // cell), int(b['cy'] // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), []):
                    if j != b['id']:
                        yield gap_m(b, by[j]), j

    for b in sorted(buildings, key=lambda b: b['id']):
        if rule[b['id']] != 'single' or b['area'] >= rules['annex_m2']:
            continue
        cands = sorted((g, j) for g, j in near(b) if g <= rules['attach_m'] and by[j]['area'] >= rules['annex_m2'])
        if cands:
            j = cands[0][1]
            parent[find(b['id'])] = find(j)
            rule[b['id']] = 'annex'
            if rule[j] == 'single':
                rule[j] = 'annex-host'
    size = {}
    for i in by:
        size[find(i)] = size.get(find(i), 0) + 1
    for b in sorted(buildings, key=lambda b: b['id']):
        if b['area'] >= rules['hut_m2'] or rule[b['id']] == 'enclosure':
            continue
        for g, j in sorted(near(b)):
            if g <= rules['hut_gap_m'] and by[j]['area'] < rules['hut_m2'] and rule[j] != 'enclosure':
                ri, rj = find(b['id']), find(j)
                if ri != rj and size[ri] + size[rj] <= rules['hut_max']:
                    parent[rj] = ri
                    size[ri] += size[rj]
                    for k in (b['id'], j):
                        if rule[k] == 'single':
                            rule[k] = 'hut-cluster'
    groups = {}
    for i in by:
        groups.setdefault(find(i), []).append(i)
    conf = {'enclosure': 0.85, 'annex': 0.6, 'annex-host': 0.6, 'hut-cluster': 0.5, 'single': 0.4}
    out = []
    for ms in groups.values():
        r = max((rule[m] for m in ms), key=lambda x: conf[x])
        out.append({'members': sorted(ms), 'rule': r, 'confidence': conf[r]})
    return out


def centroid(compound, by):
    """Point used for ordering: area-weighted centroid of the compound's structures (the gate,
    once known, replaces it only for navigation, never for numbering)."""
    a = sum(by[m]['area'] for m in compound['members'])
    return (sum(by[m]['cx'] * by[m]['area'] for m in compound['members']) / a,
            sum(by[m]['cy'] * by[m]['area'] for m in compound['members']) / a)


# ------------------------------------------------ production grouping (registry)
# The rules of group_compounds at country scale, one code area at a time (SPEC 6.2), with
# Burkina's parameters: annexes under 25 m2 within 8 m; hut clusters everywhere but the two cities.

CITY = {'annex_m2': 25.0, 'attach_m': 8.0, 'hut_m2': 0.0}
RURAL = {'annex_m2': 25.0, 'attach_m': 8.0, 'hut_m2': 40.0, 'hut_gap_m': 3.0, 'hut_max': 25}
CITIES = ('10000', '90000')   # Ouagadougou, Bobo-Dioulasso


def grouping_params(postcode):
    """Grouping parameters of a commune: no hut clusters in Ouagadougou and Bobo-Dioulasso."""
    return CITY if str(postcode) in CITIES else RURAL


def _metres(lat0):
    p = math.radians(lat0)
    return 111132.92 - 559.82 * math.cos(2 * p) + 1.175 * math.cos(4 * p), 111412.84 * math.cos(p) - 93.5 * math.cos(3 * p)


def _plane(poly, lat0, lon0):
    m_lat, m_lon = _metres(lat0)
    return [((x - lon0) * m_lon, (y - lat0) * m_lat) for x, y in poly]


def _gap_plane(pa, pb):
    """Smallest distance in metres between two closed outlines in local metres (0 if they touch or overlap)."""
    if any(_in_ring_xy(x, y, pb) for x, y in pa) or any(_in_ring_xy(x, y, pa) for x, y in pb):
        return 0.0
    d = min(_seg_dist_xy(q, pb[i], pb[i + 1]) for q in pa for i in range(len(pb) - 1))
    return min(d, min(_seg_dist_xy(q, pa[i], pa[i + 1]) for q in pb for i in range(len(pa) - 1)))


def group_footprints(fs, params=RURAL):
    """Production grouping of one code area.

    fs: dicts with id (stable structure id), ring ([lon, lat] closed), area (m2), eid (the smallest
    closed enclosure of at most 6,000 m2 holding the centre, or None). Footprints are taken in id order,
    neighbours found on a 40 m grid, so the result never depends on the data's order. Rules, in order:
      enclosure    every footprint inside one enclosure is one compound;
      annex        a footprint under annex_m2 joins the nearest footprint of at least annex_m2 within
                   attach_m, outline to outline (only annexes join, and only to a building);
      hut-cluster  (outside the two cities) huts under hut_m2 that belong to no house chain within
                   hut_gap_m, at most hut_max per compound: a cluster never joins two houses;
      single       everything else.
    Returns [(member indexes largest first, rule)] sorted by the main footprint's id."""
    if not fs:
        return []
    lat0 = sum(f['ring'][0][1] for f in fs) / len(fs)
    lon0 = sum(f['ring'][0][0] for f in fs) / len(fs)
    order = sorted(range(len(fs)), key=lambda i: fs[i]['id'])
    pts = [_plane(f['ring'], lat0, lon0) for f in fs]
    cent = [(sum(p[0] for p in q[:-1]) / max(1, len(q) - 1), sum(p[1] for p in q[:-1]) / max(1, len(q) - 1)) for q in pts]
    parent = list(range(len(fs)))
    rule = ['single'] * len(fs)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    first_in = {}
    for i in order:
        e = fs[i].get('eid')
        if e:
            r = first_in.setdefault(e, i)
            parent[find(i)] = find(r)
            rule[i] = 'enclosure'
    CELL = 40.0
    grid = {}
    for i in order:
        grid.setdefault((int(cent[i][0] // CELL), int(cent[i][1] // CELL)), []).append(i)

    def around(i, reach):
        cx, cy = int(cent[i][0] // CELL), int(cent[i][1] // CELL)
        k = int(reach // CELL) + 2
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                for j in grid.get((cx + dx, cy + dy), ()):
                    if j != i and math.dist(cent[i], cent[j]) <= 60:
                        yield j
    for i in order:
        if rule[i] != 'single' or fs[i]['area'] >= params['annex_m2']:
            continue
        best = None
        for j in around(i, params['attach_m']):
            if fs[j]['area'] < params['annex_m2']:
                continue
            g = _gap_plane(pts[i], pts[j])
            if g <= params['attach_m'] and (best is None or (g, fs[j]['id']) < (best[0], fs[best[1]]['id'])):
                best = (g, j)
        if best:
            parent[find(i)] = find(best[1])
            rule[i] = 'annex'
            if rule[best[1]] == 'single':
                rule[best[1]] = 'annex'
    if params.get('hut_m2'):
        size = {}
        for i in range(len(fs)):
            size[find(i)] = size.get(find(i), 0) + 1
        for i in order:
            if fs[i]['area'] >= params['hut_m2'] or rule[i] not in ('single', 'hut-cluster'):
                continue
            for j in sorted(around(i, params['hut_gap_m']), key=lambda j: fs[j]['id']):
                if fs[j]['area'] >= params['hut_m2'] or rule[j] not in ('single', 'hut-cluster'):
                    continue
                if _gap_plane(pts[i], pts[j]) > params['hut_gap_m']:
                    continue
                ri, rj = find(i), find(j)
                if ri != rj and size[ri] + size[rj] <= params['hut_max']:
                    parent[rj] = ri
                    size[ri] += size[rj]
                    rule[i] = rule[j] = 'hut-cluster'
    groups = {}
    for i in order:
        groups.setdefault(find(i), []).append(i)
    conf = {'enclosure': 0.85, 'annex': 0.6, 'hut-cluster': 0.5, 'single': 0.4}
    out = []
    for ms in groups.values():
        ms.sort(key=lambda i: (-fs[i]['area'], fs[i]['id']))
        out.append((ms, max((rule[m] for m in ms), key=lambda x: conf[x])))
    return sorted(out, key=lambda g: fs[g[0][0]]['id'])

def _in_ring_xy(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _seg_dist_xy(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def hilbert_index(order, x, y):
    """Distance along a Hilbert curve of side 2**order for integer cell (x, y)."""
    n = 1 << order
    d = 0
    s = n >> 1
    while s > 0:
        rx = 1 if (x & s) else 0
        ry = 1 if (y & s) else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s >>= 1
    return d


ORDER = 16


def curve_pos(lon, lat, box):
    x0, y0, x1, y1 = box
    n = (1 << ORDER) - 1
    gx = min(n, max(0, int((lon - x0) / (x1 - x0) * n)))
    gy = min(n, max(0, int((lat - y0) / (y1 - y0) * n)))
    return hilbert_index(ORDER, gx, gy)


def number_range(digits, block=None):
    """(lo, main_hi, hi) of a secteur's own range (digits) or of a village's block (lo, hi) in its
    name's national range. The top third is the tail reserve in both cases."""
    if block is not None:
        lo, hi = block
    else:
        lo, hi = 10 ** (digits - 1), 10 ** digits - 1
    size = hi - lo + 1
    main_hi = lo + (size * 2) // 3 - 1  # top third = tail reserve
    return lo, main_hi, hi


def digits_for(compounds):
    """Smallest length (3, 4 or 5) whose range holds twice today's compounds."""
    for d in (3, 4, 5):
        if compounds * 2 <= 9 * 10 ** (d - 1):
            return d
    raise ValueError('area too large: split it by quartier or village before issuing codes')


def issue_numbers(points, box, digits=None, block=None):
    """points: {compound_key: (lon, lat)}. Returns {key: number} in Hilbert order with infill gaps.
    Secteur: its own range of `digits`. Village: `block` = (lo, hi), the area's frozen block in its
    name's national range (SPEC 2.4); the block already holds twice today's compounds."""
    keys = sorted(points, key=lambda k: (curve_pos(points[k][0], points[k][1], box), k))
    n = len(keys)
    if block is not None:
        digits = len(str(block[0]))
        if n * 2 > block[1] - block[0] + 1:
            raise ValueError('capacity rule broken: compounds x 2 exceed the block')
    else:
        if digits is None:
            digits = digits_for(n)
        if n * 2 > 9 * 10 ** (digits - 1):
            raise ValueError('capacity rule broken: compounds x 2 exceed the range')
    lo, main_hi, hi = number_range(digits, block)
    step = max(1, (main_hi - lo + 1) // max(1, int(n * 1.5)))
    out = {}
    for i, k in enumerate(keys):
        out[k] = lo + i * step
    assert max(out.values()) <= main_hi
    return out, digits


def provisional_number(point, issued, points, box, digits, block=None):
    """Number for a new compound: a free number between its Hilbert neighbours (closest to the
    midpoint); otherwise the lowest free number of the tail reserve (of the block, for a village).
    Never reuses a number. A full village block takes an extension block from its name's spare."""
    lo, main_hi, hi = number_range(digits, block)
    used = set(issued.values())
    p = curve_pos(point[0], point[1], box)
    order = sorted(issued, key=lambda k: (curve_pos(points[k][0], points[k][1], box), k))
    prev = None
    nxt = None
    for k in order:
        if curve_pos(points[k][0], points[k][1], box) <= p:
            prev = issued[k]
        elif nxt is None:
            nxt = issued[k]
    a = prev if prev is not None else lo - 1
    b = nxt if nxt is not None else main_hi + 1
    free = [x for x in range(a + 1, b) if x not in used and lo <= x <= main_hi]
    if free:
        mid = (a + b) / 2
        return min(free, key=lambda x: (abs(x - mid), x))
    for x in range(main_hi + 1, hi + 1):
        if x not in used:
            return x
    raise ValueError('area full: extension block from the name spare (village) or split (secteur)')


def spare_block(entry, compounds, taken=()):
    """Next block for a new area (or an extension of a full one) with an existing name: taken from
    the name's spare space upward from entry['spareFrom']; existing blocks are never renumbered.
    Returns (lo, hi), or None when the spare is used up (then the new area takes the commune as
    qualifier, a name of its own: SPEC 2.4)."""
    lo = max([entry['spareFrom']] + [b[1] + 1 for b in taken])
    hi = lo + block_size(compounds) - 1
    return (lo, hi) if hi <= entry['range'][1] else None


def load_sample(path):
    rows = []
    for r in _read_csv(path):
        rows.append({'id': int(r['id']), 'cx': float(r['cx']), 'cy': float(r['cy']), 'area': float(r['area']),
                     'eid': int(r['eid']) if r.get('eid') else None, 'ea': float(r['ea']) if r.get('ea') else None})
    return rows


def registry(path, digits=None):
    bs = load_sample(path)
    by = {b['id']: b for b in bs}
    comps = group_compounds(bs)
    box = (min(b['cx'] for b in bs), min(b['cy'] for b in bs), max(b['cx'] for b in bs), max(b['cy'] for b in bs))
    pts = {min(c['members']): centroid(c, by) for c in comps}
    nums, d = issue_numbers(pts, box, digits)
    return comps, pts, nums, d, box


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == 'spot':
        lat, lon = float(argv[2]), float(argv[3])
        code = spot_encode(lat, lon)
        f = frames()[SPOT_RE.match(code).group(1)]
        print(json.dumps({'spot': code, 'commune': f['commune'], 'postcode': SPOT_RE.match(code).group(1),
                          'inOutline': commune_at(lat, lon) is not None}, ensure_ascii=False))
    elif cmd == 'unspot':
        print(spot_decode(argv[2]))
    elif cmd == 'check':
        m = re.match(r'^BF-(\d{5})-([SV])(\d{2,3})-(\d{3,5})$', argv[2].upper())
        if not m:
            raise ValueError('expected BF-<postcode>-<kind><area>-<number> without its check digit')
        print(machine(*m.groups()))
    elif cmd == 'resolve':
        print(json.dumps(resolve_remembered(' '.join(argv[2:])), ensure_ascii=False))
    elif cmd == 'verify':
        print(json.dumps(parse_machine(argv[2])))
    elif cmd == 'frames':
        print(len(build_frames()), 'frames written')
    elif cmd == 'registry':
        comps, pts, nums, d, box = registry(argv[2], int(argv[3]) if len(argv) > 3 else None)
        print(json.dumps({'structures': sum(len(c['members']) for c in comps), 'compounds': len(comps),
                          'digits': d, 'first': sorted(nums.values())[:5]}))
    else:
        print(__doc__)
        return 1
    return 0



# ---------------------------------------------------------------------------
# Code-area register (villages and secteurs per commune), frozen once published


def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).upper()


VILLAGE_KINDS = ('village', 'hamlet', 'isolated_dwelling', 'locality')


def build_register(places_csv=None):
    """The design register: for every coded commune, its named rural places (OSM, ODbL) inside the
    commune polygon, indexed 001.. in alphabetical order of the plain name. tools/name-ranges.py then
    adds the plate fields (plateName, plateRule, needsCouncilChoice, plateCandidates, plateReason). Once published, indices
    are frozen: new places are appended with the next free index, renamed places keep theirs.
    Towns' secteurs (S01..Snn) are listed as pending until the commune's secteur map is obtained."""
    places_csv = places_csv or os.path.join(REPO, 'model', 'areas', 'osm-places.csv')
    pts = [r for r in _read_csv(places_csv) if r['place'] in VILLAGE_KINDS]
    reg = {}
    for c in communes():
        if not c['postcode']:
            continue
        x0, y0, x1, y1 = c['box']
        inside = []
        for r in pts:
            x, y = float(r['lon']), float(r['lat'])
            if x0 <= x <= x1 and y0 <= y <= y1 and _inside(x, y, c['polys']):
                inside.append(r)
        inside.sort(key=lambda r: (plain(r['name']), float(r['lat']), float(r['lon'])))
        if len(inside) > 999:
            raise ValueError(f'{c["name"]}: more than 999 villages, needs 4-digit index')
        reg[c['postcode']] = {'commune': c['name'], 'pcode': c['pcode'], 'secteurs': 'pending',
                              'villages': [{'index': f'{i + 1:03d}', 'officialName': r['name'], 'kind': r['place'],
                                            'lon': float(r['lon']), 'lat': float(r['lat'])}
                                           for i, r in enumerate(inside)]}
    return reg


def village_index(register, postcode, name):
    hits = [v for v in register[postcode]['villages']
            if name_key(name) in (name_key(v['officialName']), name_key(v.get('plateName') or v['officialName']))]
    if len(hits) != 1:
        raise ValueError(f'{name!r} is {"ambiguous" if hits else "unknown"} in {postcode}')
    return hits[0]['index']


# ---------------------------------------------------------------------------
# Add my home: checks before a provisional code (SPEC §10)

def _local_xy(points, lat0):
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(lat0))
    return [((lon) * kx, (lat) * M_PER_DEG_LAT) for lon, lat in points]


def _area_centroid(xy):
    a = cx = cy = 0.0
    for i in range(len(xy)):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % len(xy)]
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    a /= 2
    if a == 0:
        return 0.0, (0.0, 0.0)
    return abs(a), (cx / (6 * a), cy / (6 * a))


def _seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _simple(xy):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    n = len(xy)
    for i in range(n):
        a, b = xy[i], xy[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            c, d = xy[j], xy[(j + 1) % n]
            if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
                return False
    return True


def add_my_home_checks(gate, gps_accuracy_m, outline, ar_outline=None, existing=()):
    """gate (lon, lat); outline / ar_outline: [(lon, lat)...] open rings; existing: outlines of issued
    compounds or parcels. Returns a list of problems; empty means a provisional code may be issued."""
    problems = []
    if gps_accuracy_m > 15:
        problems.append('gate GPS fix worse than 15 m: wait and average longer')
    if len(outline) < 3:
        return problems + ['outline needs at least 3 corners']
    lat0 = sum(p[1] for p in outline) / len(outline)
    xy = _local_xy(outline, lat0)
    if not _simple(xy):
        problems.append('outline crosses itself')
    area, c = _area_centroid(xy)
    if not 20 <= area <= 20000:
        problems.append(f'implausible plot area {area:.0f} m2')
    g = _local_xy([gate], lat0)[0]
    if min(_seg_dist(g, xy[i], xy[(i + 1) % len(xy)]) for i in range(len(xy))) > 5:
        problems.append('gate is not on the outline (more than 5 m away)')
    if ar_outline:
        a2, c2 = _area_centroid(_local_xy(ar_outline, lat0))
        if math.hypot(c[0] - c2[0], c[1] - c2[1]) > 8 or abs(a2 - area) > 0.2 * area:
            problems.append('AR outline and GPS/imagery outline disagree')
    for other in existing:
        oxy = _local_xy(other, lat0)
        inside = sum(1 for p in xy if _inside(p[0], p[1], [[oxy]])) + sum(1 for p in oxy if _inside(p[0], p[1], [[xy]]))
        if inside:
            problems.append('overlaps an issued compound or parcel: flagged, not issued')
            break
    return problems


# ---------------------------------------------------------------------------
# Official addresses first (SPEC §6.0)

def display_address(compound):
    """compound: {'official': {'street': 'Rue 15.123', 'door': '45', 'commune': 'Ouagadougou'} | None,
    'area': ..., 'kind': 'S'|'V', 'number': ...}. The official address, exactly as written, wins."""
    o = compound.get('official')
    if o:
        return f"{o['street']}, porte {o['door']}, {o['commune']}"
    if not compound.get('number'):
        raise ValueError('inside an officially addressed area: no N-Ways number is issued')
    return remembered(compound['area'], compound['number'], compound['kind'], compound.get('town'))


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except ValueError as e:  # a refused or malformed code: one line, not a traceback
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)
