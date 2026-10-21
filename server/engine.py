"""The reference engine (engine/reference/bf_engine.py) as the server uses it.

Name keys, check digits, machine and remembered forms, spot codes, plate names, the Hilbert curve
and block sizes all come from the reference engine. This module adds what a running register
needs on top of it:

  * the frozen area table, read from the database (registry/areas.csv), with the blocks an area
    takes after first issue;
  * the national name records, aliases, commune frames and commune outlines of
    engine/data/register.json and engine/data/units.json, the same files the N-Ways issuer embeds;
  * decoding against those live blocks, so a block added by this deployment decodes at once;
  * numbering a new compound (SPEC 6.5: NextFree, NextBlock, Insert), decision for decision as the
    N-Ways issuer does it;
  * the distance formulas the issuer uses, each where the issuer uses it.
"""
import json
import math
import os
import re
import sys
import threading
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import bf_engine as E  # noqa: E402
import bf_border as B  # noqa: E402

SPEC = 'SPEC v1.0'
DATA = os.path.join(REPO, 'engine', 'data')

TAIL_FRACTION = 2       # the top third of an area's first block is the tail reserve
MACHINE_RE = re.compile(r'^BF-(\d{5})-([SV])(\d{2,3})-([1-9]\d{2,4})(?:-(\d))?(?:\.(\d+))?(?:/(\d+))?$')


class FindError(ValueError):
    """A typed code that does not decode; `code` is the API error code."""

    def __init__(self, code, message):
        ValueError.__init__(self, message)
        self.code = code


# ---------------------------------------------------------------- distances
# Local plane, exact enough at the scale of a home. Two formulas are in use and each stays where
# the issuer uses it, so that a deployment decides exactly as the N-Ways issuer does.
M_LAT = 110574.0
M_LON_EQ = 111320.0
EARTH_R = 6371008.8


def dist_plane(lat1, lon1, lat2, lon2):
    """The issuer's distance for choosing the nearest area (cosine of the second latitude)."""
    return math.hypot((lat1 - lat2) * M_LAT, (lon1 - lon2) * M_LON_EQ * math.cos(math.radians(lat2)))


def dist_door(lat1, lng1, lat2, lng2):
    """The issuer's distance for the 80 m door rule and for moving an entrance (mean latitude)."""
    dy = (lat2 - lat1) * 111320
    dx = (lng2 - lng1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def dist_m(lat1, lng1, lat2, lng2):
    """Ground distance in metres for look-ups by point (great circle on the mean Earth radius)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(h)))


def metres_per_degree(lat):
    return M_LAT, M_LON_EQ * max(0.01, math.cos(math.radians(lat)))


def ring_area(ring):
    """Area in m² of an outline [[lng, lat], ...] (open ring), as the issuer computes it."""
    if len(ring) < 3:
        return 0.0
    k = math.cos(math.radians(ring[0][1]))
    a = 0.0
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        xi, yi = ring[i][0] * M_LON_EQ * k, ring[i][1] * M_LAT
        xj, yj = ring[j][0] * M_LON_EQ * k, ring[j][1] * M_LAT
        a += xi * yj - xj * yi
    return abs(a) / 2


def ring_perimeter(ring):
    return sum(dist_door(ring[i][1], ring[i][0], ring[(i + 1) % len(ring)][1], ring[(i + 1) % len(ring)][0])
               for i in range(len(ring)))


def ring_contains(ring, lng, lat):
    return E._inside(lng, lat, [[ring]])


def ring_centre(ring):
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def round1(x):
    """One decimal, ties to even (the issuer's rounding)."""
    return round(x * 10) / 10


# ---------------------------------------------------------------- Plus Codes (shown on a card)
_OLC = '23456789CFGHJMPQRVWX'


def plus_code(lat, lng):
    """The 11-character Open Location Code of a point."""
    def r6(x):
        return round(x * 1e6) / 1e6
    lat = min(90.0, max(-90.0, lat))
    lng = ((lng + 180) % 360 + 360) % 360 - 180
    lat_v = int(math.floor(r6((lat + 90) * 25000000)))
    lng_v = int(math.floor(r6((lng + 180) * 8192000)))
    tail = ''
    for _ in range(5):
        tail = _OLC[(lat_v % 5) * 4 + lng_v % 4] + tail
        lat_v //= 5
        lng_v //= 4
    head = ''
    for _ in range(5):
        head = _OLC[lat_v % 20] + _OLC[lng_v % 20] + head
        lat_v //= 20
        lng_v //= 20
    full = head + tail
    return full[:8] + '+' + full[8:11]


def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s or '') if not unicodedata.combining(c))


# ---------------------------------------------------------------- blocks
def parse_blocks(text):
    """'1000-1759|8600-8619' -> [[1000, 1759], [8600, 8619]]."""
    out = []
    for part in (text or '').split('|'):
        if part:
            lo, hi = part.split('-')
            out.append([int(lo), int(hi)])
    return out


def format_blocks(blocks):
    return '|'.join('%d-%d' % (lo, hi) for lo, hi in blocks)


def in_blocks(area, n):
    return any(lo <= n <= hi for lo, hi in area['blocks'])


def numbered(area):
    return bool(area['blocks'])


def area_from_row(row):
    """An area of the frozen table from its areas.csv row (database names)."""
    postcode, index = row['zone'].split('-')
    frame = [float(x) for x in row['frame'].split()]
    point = None
    if row['place_lat'] and row['place_lon']:
        point = [float(row['place_lon']), float(row['place_lat'])]
    return {'key': row['zone'], 'id': int(row['area_id']), 'postcode': postcode, 'index': index,
            'plate': row['plate_name'], 'official': row['official_name'], 'commune': row['commune'],
            'nameKey': row['name_key'], 'nameId': int(row['name_id']), 'digits': int(row['digits']),
            'blocks': parse_blocks(row['blocks']), 'provisional': row['provisional_name'] == 'true',
            'compounds': int(row['compounds']), 'alertZone': row['alert_zone'] == 'true',
            'point': point, 'frame': frame, 'ord': int(row['ord'])}


# ---------------------------------------------------------------- numbering (SPEC 6.5)
def curve(area, lat, lon):
    """A point's position on its area's Hilbert curve over the frozen frame."""
    return E.curve_pos(lon, lat, area['frame'])


def tail_start(area):
    """The first number of the tail reserve of the area's first block."""
    lo, hi = area['blocks'][0]
    return lo + (hi - lo + 1) * TAIL_FRACTION // 3


def next_free(area, issued, lat, lon):
    """A new compound's number in an area that has numbers: between its neighbours on the curve
    (below the tail reserve), the free number nearest their midpoint, the lower first; else the
    lowest free number of the tail reserve; else of the area's later blocks; else None.

    issued: [{'number', 'lat', 'lon', 'key'}] for every number the area holds, retired ones too."""
    h = curve(area, lat, lon)
    tail = tail_start(area)
    used = set()
    seq = []
    for c in issued:
        used.add(c['number'])
        seq.append((curve(area, c['lat'], c['lon']), c['key'], c['number']))
    seq.sort(key=lambda t: (t[0], t[1]))
    lo, hi = area['blocks'][0]
    low_n, high_n, found = lo - 1, tail, False
    for kh, _key, n in seq:
        if kh <= h:
            low_n = n
        elif not found:
            high_n, found = n, True
    if high_n - low_n > 1:
        mid = (low_n + high_n) // 2
        for d in range(high_n - low_n):
            for c in (mid - d, mid + d):
                if low_n < c < high_n and lo <= c < tail and c not in used:
                    return c
    for c in range(tail, hi + 1):
        if c not in used:
            return c
    for b in area['blocks'][1:]:
        for c in range(b[0], b[1] + 1):
            if c not in used:
                return c
    return None


class Engine:
    """The register in force: the frozen areas (from the database) and the national names."""

    def __init__(self, area_rows):
        with open(os.path.join(DATA, 'register.json'), encoding='utf-8') as f:
            reg = json.load(f)
        self.names = {n['key']: n for n in reg['names']}
        self.aliases = reg.get('aliases') or {}
        self.communes = {c['postcode']: c for c in reg['communes']}
        with open(os.path.join(DATA, 'units.json'), encoding='utf-8') as f:
            units = json.load(f)
        self.unit_order = list(units)
        self.unit_polys = units
        self.unit_boxes = {}
        for pc, polys in units.items():
            xs = [p[0] for poly in polys for p in poly[0]]
            ys = [p[1] for poly in polys for p in poly[0]]
            self.unit_boxes[pc] = (min(xs), min(ys), max(xs), max(ys))
        self.lock = threading.Lock()
        self.load(area_rows)

    def load(self, area_rows):
        areas = sorted((area_from_row(r) for r in area_rows), key=lambda a: a['ord'])
        by_key, by_id, families, in_commune = {}, {}, {}, {}
        for a in areas:
            by_key[a['key']] = a
            by_id[a['id']] = a
            families.setdefault(a['nameKey'], []).append(a)
            in_commune.setdefault(a['postcode'], []).append(a)
        for m in (families, in_commune):
            for k in m:
                m[k].sort(key=lambda a: a['key'])
        with self.lock:
            self.areas, self.by_key, self.by_id = areas, by_key, by_id
            self.families, self.in_commune = families, in_commune

    def set_blocks(self, key, blocks):
        a = self.by_key.get(key)
        if a is not None:
            a['blocks'] = [list(b) for b in blocks]

    # -------------------------------------------------------------- places
    def area(self, key):
        return self.by_key.get(key)

    def commune(self, postcode):
        return self.communes.get(postcode)

    def commune_at(self, lat, lng):
        """The commune holding a point (the issuer's order of the commune outlines), or None."""
        for pc in self.unit_order:
            x0, y0, x1, y1 = self.unit_boxes[pc]
            if lng < x0 or lng > x1 or lat < y0 or lat > y1:
                continue
            if E._inside(lng, lat, self.unit_polys[pc]):
                return self.communes.get(pc)
        return None

    def in_country(self, lat, lng):
        """The point is in Burkina Faso: within 300 m of the national border (SPEC 1b), and in a
        commune outline, or in no outline but close enough to one to have a spot code
        (spot_commune), as the compounds in the gaps between outlines are. The border decides: a
        commune outline or a spot frame that reaches over it gives no Burkina Faso code there."""
        return not self.abroad(lat, lng) and self.spot_commune(lat, lng) is not None

    def abroad(self, lat, lng):
        """The point lies more than 300 m outside Burkina Faso's national border (OpenStreetMap
        admin_level 2), as engine/data/border.json can tell with its simplification margin."""
        return B.abroad(lat, lng)

    def area_at(self, lat, lng):
        """The code area of a point: the nearest named place of its commune, ties to the lower key."""
        c = self.commune_at(lat, lng)
        if c is None:
            return None
        best, bd = None, float('inf')
        cl = math.cos(lat * math.pi / 180) ** 2
        for a in self.in_commune.get(c['postcode'], []):
            if a['point'] is None:
                continue
            dx, dy = a['point'][0] - lng, a['point'][1] - lat
            d = dx * dx * cl + dy * dy
            if d < bd:
                best, bd = a, d
        return best

    def nearest_area(self, lat, lng):
        """The numbered area whose place point is nearest (the issuer's last resort for a new code)."""
        best, bd = None, float('inf')
        for a in self.areas:
            if not numbered(a) or a['point'] is None:
                continue
            d = dist_plane(a['point'][1], a['point'][0], lat, lng)
            if d < bd:
                best, bd = a, d
        return best

    def place_line(self, area):
        c = self.communes.get(area['postcode']) if area else None
        return c['name'] if c else 'Burkina Faso'

    # -------------------------------------------------------------- spot codes
    def spot_commune(self, lat, lng):
        """The commune whose frame gives a point its spot code (SPEC 5.1): the commune holding it;
        for a point in no outline, the nearest commune within 10 km whose frame holds it, else whose
        frame lies within 3,000 m of it. None: refused."""
        c = self.commune_at(lat, lng)
        if c is not None:
            return c
        pc = E.nearest_spot_commune(lat, lng, [(pc, self.unit_polys[pc], self.unit_boxes[pc]) for pc in self.unit_order], self.communes)
        return self.communes.get(pc) if pc else None

    def spot(self, lat, lng):
        """The spot code of a point, or ValueError outside Burkina Faso (in no commune, and none
        within 10 km has a frame within 3,000 m)."""
        c = self.spot_commune(lat, lng)
        if c is None:
            raise ValueError('the point is outside the communes of Burkina Faso')
        return E.spot_encode(lat, lng, c['postcode'])

    def spot_point(self, code):
        """(lat, lng) of the centre of a spot code's 10 m cell."""
        m = E.SPOT_RE.match((code or '').strip().upper())
        if not m:
            raise ValueError('not a spot code of Burkina Faso (BF-<postcode> E<east> N<north>)')
        c = self.communes.get(m.group(1))
        if c is None:
            raise ValueError('no commune has the postcode %s' % m.group(1))
        if len(m.group(2)) != c['dx'] or len(m.group(3)) != c['dy']:
            raise ValueError('a spot code in %s has %d and %d digits' % (c['name'], c['dx'], c['dy']))
        lat, lng = E.spot_decode(code)
        return lat, lng, c

    # -------------------------------------------------------------- forms
    def check_digit(self, area, number):
        return E.damm(E.check_input(area['postcode'], 'V', area['index'], number, area['nameId']))

    def forms(self, area, number):
        """Machine, home, written (remembered) and spoken forms of a code, and its check digit."""
        machine = E.machine(area['postcode'], 'V', area['index'], number, area['nameId'])
        group = E.group_number(number)
        return {'machine': machine, 'home': '%s %d' % (area['plate'], number), 'written': '%s %s' % (area['plate'], group),
                'spoken': '%s, %s' % (area['plate'], group), 'spokenFr': '%s, %s' % (area['plate'], E.say_fr(number)),
                'check': int(machine[-1])}

    # -------------------------------------------------------------- names
    def name_of(self, text):
        """The national name record of a typed name: its plate name, else the official name it is
        an alias of."""
        k = E.name_key(text)
        n = self.names.get(k)
        if n is None and k in self.aliases:
            n = self.names.get(self.aliases[k])
        return n

    def areas_named(self, text):
        n = self.name_of(text)
        return list(self.families.get(n['key'], [])) if n else []

    def decode(self, name_rec, number):
        """The one area that owns the number under this name anywhere in Burkina Faso, or None."""
        if len(str(number)) != name_rec['digits']:
            return None
        for a in self.families.get(name_rec['key'], []):
            if in_blocks(a, number):
                return a
        return None

    def parse_machine(self, text):
        """(area, number, checked) of a machine form. A wrong check digit is refused, never
        guessed."""
        t = (text or '').strip().upper().replace(' ', '')
        m = MACHINE_RE.match(t)
        if not m:
            raise FindError('bad_code', 'Not a machine code of Burkina Faso; one looks like BF-10000-V064-1776-9.')
        postcode, kind, place, number, chk = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)
        if kind == 'S':
            raise FindError('secteur', 'Secteur codes are not issued: a town\'s homes have the code of their quarter.')
        if len(place) != 3:
            raise FindError('bad_code', 'An area index has 3 digits.')
        a = self.by_key.get('%s-%s' % (postcode, place))
        if a is None:
            raise FindError('unknown_area', 'There is no area V%s in commune %s.' % (place, postcode))
        if not in_blocks(a, number):
            raise FindError('not_in_blocks', 'The number %d is not one of %s: a digit is wrong.' % (number, a['plate']))
        if chk is not None and self.check_digit(a, number) != int(chk):
            raise FindError('check_digit', 'The check digit does not match: a digit is wrong or two are swapped.')
        return a, number, chk is not None

    def parse_remembered(self, text):
        """(area, number, checked) of a remembered or written form ("Koulouba 17 76"), with nothing
        else: the name and the number alone decide the area."""
        t = ' '.join((text or '').replace('·', ' ').split())
        if re.match(r'(?i)^\s*secteur\b', t):
            raise FindError('secteur', 'Secteur codes are not issued: say the quarter or village and its number.')
        m = E.REMEMBERED_V.match(t)
        if not m:
            raise FindError('bad_query', 'Expected a village or quarter name and a number of 3 to 5 digits.')
        name, number, chk = m.group(1), int(m.group(2).replace(' ', '')), m.group(3)
        rec = self.name_of(name)
        if rec is None:
            raise FindError('unknown_name', 'No N-Ways area of Burkina Faso is called "%s".' % name.strip())
        if len(str(number)) != rec['digits']:
            raise FindError('wrong_digits', 'Numbers of %s have %d digits.' % (name.strip(), rec['digits']))
        a = self.decode(rec, number)
        if a is None:
            raise FindError('not_in_blocks', '%s %s is not issued: no %s area holds this number.'
                            % (rec['plateName'], E.group_number(number), rec['plateName']))
        if chk is not None and self.check_digit(a, number) != int(chk):
            raise FindError('check_digit', 'The check digit does not match: a mistyped name or number.')
        return a, number, chk is not None

    # -------------------------------------------------------------- new numbers
    def next_block(self, area, compounds):
        """A further block of the area's name, taken from its spare upward from spareFrom and
        above every block given since; appended to `area`. None when the range is used up."""
        nm = self.names.get(area['nameKey'])
        if nm is None:
            return None
        lo = nm['spareFrom']
        for x in self.families.get(area['nameKey'], []):
            for b in x['blocks']:
                lo = max(lo, b[1] + 1)
        for b in area['blocks']:
            lo = max(lo, b[1] + 1)
        hi = lo + E.block_size(compounds) - 1
        if hi > nm['range'][1]:
            return None
        area['blocks'].append([lo, hi])
        return [lo, hi]

    def insert(self, area, issued, lat, lon):
        """A new compound's number in its area (a copy whose blocks may grow), or None when the
        name's range is used up."""
        if not area['blocks']:
            b = self.next_block(area, 1)
            return b[0] if b else None
        n = next_free(area, issued, lat, lon)
        if n is not None:
            return n
        b = self.next_block(area, len(issued) + 1)
        return b[0] if b else None
