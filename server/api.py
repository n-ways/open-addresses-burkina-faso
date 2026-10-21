"""The JSON API (/v1) over HTTP.

Every response is JSON. Errors are {"error": {"code": "...", "message": "..."}} with the matching HTTP
status. Reads need no key. Issuing and changing codes need a bearer key from ISSUE_KEYS, and are
refused outright on a deployment that has none (a read-only deployment).
"""
import hashlib
import hmac
import json
import re
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from . import API_VERSION, COUNTRY, COUNTRY_NAME, CREDIT, CREDIT_URL
from . import issue as I
from . import store as S
from .engine import E, SPEC, Engine, FindError, dist_m, in_blocks, numbered, plus_code, ring_contains, tail_start

AT_M = 12.0             # /v1/at: a code whose entrance is this close is the compound at the point
SPOT_ON_HOME_M = 15.0   # a spot code names a compound when a code's entrance is this close to its centre
NEAR_MAX_M = 500.0
NEAR_MAX_N = 100
PAGE_MAX = 1000
BODY_MAX = 65536
LICENCES = {'data': 'ODbL-1.0', 'code': 'Apache-2.0', 'documents': 'CC-BY-4.0'}
EXAMPLES = {'remembered': 'Koulouba 17 76', 'machine': 'BF-10000-V064-1776-9', 'spot': 'BF-10000 E1809 N1351',
            'official': 'Rue du Baobab, Bobo-Dioulasso'}


class ApiError(Exception):
    def __init__(self, status, code, message, extra=None):
        Exception.__init__(self, message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


# ---------------------------------------------------------------- representations
def area_json(eng, a, counts=None):
    if a is None:
        return None
    out = {'key': a['key'], 'id': a['id'], 'index': a['index'], 'plateName': a['plate'],
           'officialName': a['official'] or None, 'nameProvisional': a['provisional'],
           'commune': {'postcode': a['postcode'], 'name': eng.place_line(a)},
           'nameKey': a['nameKey'], 'nameId': a['nameId'], 'digits': a['digits'],
           'blocks': [list(b) for b in a['blocks']], 'numbered': numbered(a),
           'compoundsAtIssue': a['compounds'], 'travelAdvisory': a['alertZone'],
           'point': {'lat': a['point'][1], 'lng': a['point'][0]} if a['point'] else None,
           'frame': a['frame']}
    if counts is not None:
        out['codes'] = counts.get(a['key'], 0)
    return out


def registry_json(row):
    """Every registry column, by its published name, exactly as published."""
    return {c: row[S.sql_name(c)] for c in S.CODE_COLUMNS}


def card(eng, row):
    a = eng.area(row['zone'])
    lat, lng = float(row['entrance_lat']), float(row['entrance_lng'])
    number = int(row['number'])
    forms = eng.forms(a, number) if a else {}
    c = eng.commune(row['unit'])
    return {
        'machine': row['machine'],
        'remembered': row['written'],
        'home': row['home'],
        'spoken': forms.get('spoken'),
        'spokenFr': forms.get('spokenFr'),
        'plateName': a['plate'] if a else None,
        'officialName': row['official_name'] or None,
        'number': number,
        'check': int(row['check_digit']),
        'status': row['status'],
        'issued': row['issued'],
        'issuedAt': row['issued_at'],
        'officialAddress': row['official_address'] or None,
        'place': eng.place_line(a),
        'entrance': {'lat': lat, 'lng': lng, 'kind': row['entrance_kind']},
        'spotCode': row['spot_code'],
        'plusCode': plus_code(lat, lng),
        'area': area_json(eng, a),
        'zone': {'key': row['unit'], 'name': c['name'] if c else None},
        'building': {'class': row['class_'] or None, 'use': row['use_'] or None, 'kind': row['kind'] or None,
                     'structures': int(row['structures'] or 0), 'floorAreaM2': float(row['floor_area_m2'] or 0),
                     'rule': row['rule'] or None, 'estate': row['estate'] or None},
        'registry': registry_json(row),
        'credit': CREDIT,
    }


def brief(row, d=None):
    out = {'machine': row['machine'], 'remembered': row['written'], 'status': row['status'],
           'entrance': {'lat': float(row['entrance_lat']), 'lng': float(row['entrance_lng']), 'kind': row['entrance_kind']},
           'spotCode': row['spot_code'], 'officialAddress': row['official_address'] or None, 'area': row['zone']}
    if d is not None:
        out['distanceM'] = round(d, 1)
    return out


def _sentence(s):
    s = s.strip()
    return (s[:1].upper() + s[1:]).rstrip('.') + '.'


# ---------------------------------------------------------------- the application
class App:
    def __init__(self, db, keys=(), per_day=5, cors=(), log=True):
        self.db = db
        self.log = log
        self.keys = [k for k in keys if k]
        self.per_day = per_day
        self.cors = list(cors)
        S.upgrade(db)
        st = S.Store(db, readonly=True)
        try:
            self.engine = Engine(st.area_rows())
            st.meta()
        finally:
            st.close()
        routes = [
            ('GET', r'/v1/health', self.health),
            ('GET', r'/v1/info', self.info),
            ('GET', r'/v1/find', self.find),
            ('GET', r'/v1/at', self.at),
            ('GET', r'/v1/near', self.near),
            ('GET', r'/v1/verify', self.verify),
            ('GET', r'/v1/spot', self.spot),
            ('GET', r'/v1/spot/decode', self.spot_decode),
            ('GET', r'/v1/zones', self.zones),
            ('GET', r'/v1/zones/(?P<key>[^/]+)', self.zone),
            ('GET', r'/v1/zones/(?P<key>[^/]+)/codes', self.zone_codes),
            ('GET', r'/v1/areas', self.areas_search),
            ('GET', r'/v1/areas/(?P<key>[^/]+)', self.area),
            ('GET', r'/v1/codes/(?P<machine>[^/]+)', self.code),
            ('POST', r'/v1/codes', self.issue),
            ('PATCH', r'/v1/codes/(?P<machine>[^/]+)', self.change),
        ]
        self.routes = [(m, re.compile(p + r'/?$'), f) for m, p, f in routes]

    # -------------------------------------------------------------- dispatch
    def handle(self, method, path, query, headers, body):
        """Returns (status, payload, extra headers)."""
        allowed = sorted({m for m, rx, _ in self.routes if rx.match(path)})
        for m, rx, fn in self.routes:
            mt = rx.match(path)
            if mt and m == method:
                st = S.Store(self.db, readonly=(method == 'GET'))
                try:
                    out = fn(st, query=query, headers=headers, body=body, **{k: unquote(v) for k, v in mt.groupdict().items()})
                finally:
                    st.close()
                if isinstance(out, tuple):
                    return out[0], out[1], {}
                return 200, out, {}
        if allowed:
            raise ApiError(405, 'method_not_allowed', '%s is not allowed on %s; use %s.' % (method, path, ', '.join(allowed)),
                           {'Allow': ', '.join(allowed)})
        raise ApiError(404, 'not_found', 'No endpoint %s. See /v1/info and docs/api.md.' % path)

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _q(query, name, required=True):
        v = query.get(name, [None])[0]
        if v is not None:
            v = v.strip()
        if required and not v:
            raise ApiError(400, 'bad_request', 'The query parameter %s is required.' % name)
        return v

    def _float(self, query, name, lo, hi, default=None):
        v = self._q(query, name, required=default is None)
        if v is None or v == '':
            return default
        try:
            x = float(v)
        except ValueError:
            raise ApiError(400, 'bad_request', '%s must be a number, not %r.' % (name, v))
        if x != x or not (lo <= x <= hi):
            raise ApiError(400, 'bad_request', '%s must be between %g and %g.' % (name, lo, hi))
        return x

    def _int(self, query, name, lo, hi, default):
        v = self._q(query, name, required=False)
        if not v:
            return default
        if not re.fullmatch(r'\d+', v):
            raise ApiError(400, 'bad_request', '%s must be a whole number.' % name)
        x = int(v)
        if not (lo <= x <= hi):
            raise ApiError(400, 'bad_request', '%s must be between %d and %d.' % (name, lo, hi))
        return x

    def _key(self, headers):
        if not self.keys:
            raise ApiError(403, 'read_only', 'This deployment is read-only: it does not issue or change codes. '
                                             'Only the issuer designated by the State or N-WAYS LIMITED does.')
        auth = headers.get('Authorization') or ''
        m = re.match(r'Bearer\s+(\S+)$', auth.strip())
        if not m:
            raise ApiError(401, 'unauthorized', 'Send the issuing key as "Authorization: Bearer <key>".', {'WWW-Authenticate': 'Bearer'})
        got = m.group(1).encode('utf-8')
        for k in self.keys:
            if hmac.compare_digest(got, k.encode('utf-8')):
                return 'key:' + hashlib.sha256(k.encode('utf-8')).hexdigest()[:16]
        raise ApiError(401, 'unauthorized', 'That key is not one of this deployment\'s issuing keys.', {'WWW-Authenticate': 'Bearer'})

    @staticmethod
    def _json(body):
        if not body:
            raise ApiError(400, 'bad_request', 'The request needs a JSON body.')
        try:
            return json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, 'bad_request', 'The body is not valid JSON.')

    def _machine(self, text):
        """(canonical machine form, area, number) of `text`; a wrong check digit or a number in no
        block is refused, never guessed."""
        try:
            a, n, _checked = self.engine.parse_machine(text)
        except FindError as e:
            raise ApiError(400, e.code, str(e))
        return self.engine.forms(a, n)['machine'], a, n

    def _not_issued(self, a, n):
        f = self.engine.forms(a, n)
        return ApiError(404, 'not_issued', 'No compound has %s yet (%s): the number is in the range of %s, %s.'
                        % (f['written'], f['machine'], a['plate'], self.engine.place_line(a)))

    def _live(self, r):
        if r['status'] == 'retired':
            raise ApiError(410, 'retired', '%s was retired: there is no home there any more. A retired code is never given again.' % r['written'])
        return r

    # -------------------------------------------------------------- endpoints
    def health(self, st, **_):
        man = st.manifest()
        return {'status': 'ok', 'country': COUNTRY, 'codes': st.count(), 'registryExported': man.get('exported'),
                'changedSinceImport': st.meta().get('changed') == '1', 'issuing': bool(self.keys)}

    def info(self, st, **_):
        man = st.manifest()
        by_unit = st.counts_by_unit()
        zones = [{'key': u, 'name': (self.engine.commune(u) or {}).get('name'), 'codes': n} for u, n in sorted(by_unit.items())]
        areas = self.engine.areas
        return {'country': COUNTRY, 'name': COUNTRY_NAME, 'api': API_VERSION, 'engine': man.get('engine'), 'spec': SPEC,
                'registryExported': man.get('exported'), 'importedAt': st.meta().get('imported_at'),
                'counts': {'codes': st.count(), 'byStatus': st.counts_by_status(), 'zones': len(zones),
                           'communes': len(self.engine.communes), 'areas': len(areas),
                           'numberedAreas': sum(1 for a in areas if numbered(a)), 'names': len(self.engine.names)},
                'zones': zones, 'licences': LICENCES, 'credit': CREDIT, 'creditUrl': CREDIT_URL,
                'issuing': bool(self.keys), 'issuePerDay': self.per_day if self.keys else 0, 'forms': EXAMPLES}

    def code(self, st, machine, **_):
        m, a, n = self._machine(machine)
        r = st.by_machine(m)
        if r is None:
            raise self._not_issued(a, n)
        return card(self.engine, r)

    def find(self, st, query, **_):
        q = ' '.join(self._q(query, 'q').split())
        if len(q) > 200:
            raise ApiError(400, 'bad_request', 'q is at most 200 characters.')
        u = q.upper().replace(' ', '')
        if u.startswith('BF-') and not E.SPOT_RE.match(q.upper()):
            m, a, n = self._machine(q)
            r = st.by_machine(m)
            if r is None:
                raise self._not_issued(a, n)
            return {'query': q, 'kind': 'machine', 'count': 1, 'results': [card(self.engine, self._live(r))]}
        if E.SPOT_RE.match(q.upper()):
            try:
                lat, lng, _c = self.engine.spot_point(q)
            except ValueError as e:
                raise ApiError(400, 'bad_code', _sentence(str(e)))
            pt = {'lat': round(lat, 7), 'lng': round(lng, 7)}
            near = st.nearest(lat, lng, SPOT_ON_HOME_M)
            if near is None:
                raise ApiError(404, 'not_found', 'The spot %s is not on a compound with a code (no entrance within %d m of %.6f, %.6f).'
                               % (q, SPOT_ON_HOME_M, lat, lng), {'point': pt})
            return {'query': q, 'kind': 'spot', 'point': pt, 'count': 1,
                    'results': [dict(card(self.engine, near[1]), distanceM=round(near[0], 1))]}
        err = None
        try:
            a, n, _checked = self.engine.parse_remembered(q)
        except FindError as e:
            err = e
        if err is None:
            r = st.by_name_number(a['nameId'], n)
            if r is None or r['zone'] != a['key']:
                raise self._not_issued(a, n)
            return {'query': q, 'kind': 'remembered', 'count': 1, 'results': [card(self.engine, self._live(r))]}
        key = S.official_key(q)
        if key:
            total = st.count_official(key)
            if total:
                rows = st.by_official(key, 100)
                return {'query': q, 'kind': 'official', 'count': total, 'more': total > len(rows),
                        'results': [card(self.engine, r) for r in rows]}
        if err.code == 'check_digit':
            raise ApiError(400, 'check_digit', str(err))
        if err.code in ('unknown_name', 'not_in_blocks', 'wrong_digits'):
            raise ApiError(404, err.code, '%s Check the place name and the number on the plate.' % err)
        if err.code == 'secteur':
            raise ApiError(400, 'secteur', str(err))
        raise ApiError(400, 'bad_query', 'Give a code as people say it ("%s"), a machine code ("%s"), a spot code ("%s") '
                       'or an official address ("%s").' % (EXAMPLES['remembered'], EXAMPLES['machine'], EXAMPLES['spot'], EXAMPLES['official']))

    def at(self, st, query, **_):
        lat = self._float(query, 'lat', -90, 90)
        lng = self._float(query, 'lng', -180, 180)
        near = st.nearest(lat, lng, AT_M)
        if near is None:
            for r in st.in_box(lat, lng, 200):
                if r.get('outline') and ring_contains(json.loads(r['outline']), lng, lat):
                    near = (0.0, r)
                    break
        # A published code is found at its entrance wherever it lies; any other point must be in
        # Burkina Faso (the border decides, SPEC 1b).
        if near is None and not self.engine.in_country(lat, lng):
            raise ApiError(404, 'outside', 'The point %.6f, %.6f is outside Burkina Faso.' % (lat, lng))
        c = self.engine.commune_at(lat, lng)
        if c is not None:
            a = self.engine.area_at(lat, lng)
        else:   # in no outline (a gap between outlines): the area a new code takes
            a = I.place_for(st, self.engine, lat, lng)
            c = self.engine.commune(a['postcode']) if a else None
        zone = {'key': c['postcode'], 'name': c['name']} if c else None
        if near is not None:
            return {'status': 'found', 'distanceM': round(near[0], 1), 'code': card(self.engine, near[1]),
                    'area': area_json(self.engine, a), 'zone': zone}
        new = I.place_for(st, self.engine, lat, lng)
        return {'status': 'none', 'area': area_json(self.engine, a), 'zone': zone,
                'newCodeArea': new['key'] if new else None, 'spotCode': self.engine.spot(lat, lng)}

    def near(self, st, query, **_):
        lat = self._float(query, 'lat', -90, 90)
        lng = self._float(query, 'lng', -180, 180)
        radius = self._float(query, 'radius', 1, NEAR_MAX_M, default=100.0)
        limit = self._int(query, 'limit', 1, NEAR_MAX_N, NEAR_MAX_N)
        hits = []
        for r in st.in_box(lat, lng, radius):
            d = dist_m(lat, lng, r['lat'], r['lng'])
            if d <= radius:
                hits.append((d, r['machine'], r))
        hits.sort(key=lambda x: (x[0], x[1]))
        return {'point': {'lat': lat, 'lng': lng}, 'radiusM': radius, 'count': min(len(hits), limit), 'more': len(hits) > limit,
                'results': [brief(r, d) for d, _, r in hits[:limit]]}

    def verify(self, st, query, **_):
        code = self._q(query, 'code')
        out = {'code': code, 'syntax': False, 'checkDigit': None, 'inBlocks': None, 'issued': False, 'status': None, 'machine': None}
        m = re.fullmatch(r'BF-(\d{5})-V(\d{3})-([1-9]\d{2,4})-(\d)', code.strip().upper().replace(' ', ''))
        if not m:
            out['reason'] = 'not a machine code (BF-<postcode>-V<area>-<number>-<check>)'
            return out
        out['syntax'] = True
        a = self.engine.area('%s-%s' % (m.group(1), m.group(2)))
        if a is None:
            out['reason'] = 'no code area V%s in commune %s' % (m.group(2), m.group(1))
            return out
        n = int(m.group(3))
        want = self.engine.check_digit(a, n)
        out['checkDigit'] = want == int(m.group(4))
        out['inBlocks'] = in_blocks(a, n)
        if not out['checkDigit']:
            out['reason'] = 'the check digit does not match: a digit is wrong or two are swapped'
            return out
        if not out['inBlocks']:
            out['reason'] = '%s (%s) has no number %d' % (a['plate'], a['key'], n)
            return out
        out['machine'] = self.engine.forms(a, n)['machine']
        r = st.by_machine(out['machine'])
        if r is not None:
            out.update({'issued': True, 'status': r['status'], 'remembered': r['written']})
        else:
            out['reason'] = 'valid, but not issued'
        return out

    def spot(self, st, query, **_):
        lat = self._float(query, 'lat', -90, 90)
        lng = self._float(query, 'lng', -180, 180)
        try:
            code = self.engine.spot(lat, lng)
        except ValueError:
            raise ApiError(404, 'outside', 'The point %.6f, %.6f is outside Burkina Faso.' % (lat, lng))
        clat, clng, c = self.engine.spot_point(code)
        return {'spotCode': code, 'point': {'lat': lat, 'lng': lng}, 'centre': {'lat': clat, 'lng': clng}, 'cellM': 10,
                'zone': {'key': c['postcode'], 'name': c['name']}}

    def spot_decode(self, st, query, **_):
        code = self._q(query, 'code')
        try:
            lat, lng, c = self.engine.spot_point(code)
        except ValueError as e:
            raise ApiError(400, 'bad_code', _sentence(str(e)))
        return {'spotCode': ' '.join(code.strip().upper().split()), 'centre': {'lat': lat, 'lng': lng}, 'cellM': 10,
                'zone': {'key': c['postcode'], 'name': c['name']},
                'frame': {'lon0': c['lon0'], 'lat0': c['lat0'], 'latc': c['latc'], 'digitsEast': c['dx'], 'digitsNorth': c['dy']}}

    def _zone_json(self, pc, by_unit):
        areas = self.engine.in_commune.get(pc, [])
        c = self.engine.commune(pc)
        return {'key': pc, 'name': c['name'], 'pcode': c.get('pcode'), 'codes': by_unit.get(pc, 0), 'areas': len(areas),
                'numberedAreas': sum(1 for a in areas if numbered(a)),
                'travelAdvisory': any(a['alertZone'] for a in areas)}

    def zones(self, st, **_):
        by_unit = st.counts_by_unit()
        keys = sorted(self.engine.communes)
        return {'count': len(keys), 'zones': [self._zone_json(pc, by_unit) for pc in keys]}

    def _zone_key(self, key):
        if key not in self.engine.communes:
            raise ApiError(404, 'not_found', 'No zone %s: a zone is a commune, keyed by its 5-digit postcode. /v1/zones lists them.' % key)
        return key

    def zone(self, st, key, **_):
        k = self._zone_key(key)
        counts = st.counts_by_zone(k)
        out = self._zone_json(k, {k: sum(counts.values())})
        out['areas'] = [area_json(self.engine, a, counts) for a in self.engine.in_commune.get(k, [])]
        return out

    def zone_codes(self, st, key, query, **_):
        k = self._zone_key(key)
        after = self._q(query, 'after', required=False) or ''
        limit = self._int(query, 'limit', 1, PAGE_MAX, 100)
        rows = st.unit_page(k, after, limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        return {'zone': k, 'after': after or None, 'limit': limit, 'count': len(rows),
                'next': rows[-1]['machine'] if more else None, 'results': [registry_json(r) for r in rows]}

    def area(self, st, key, **_):
        a = self.engine.by_id.get(int(key)) if key.isdigit() else self.engine.area(key)
        if a is None:
            raise ApiError(404, 'not_found', 'No code area %s (a key such as 10000-064, or a numeric id). Search by name with /v1/areas?name=.' % key)
        out = area_json(self.engine, a)
        out['byStatus'] = st.counts_by_status(a['key'])
        out['codes'] = sum(out['byStatus'].values())
        if numbered(a):
            r = st.con.execute('SELECT min(num), max(num), count(*) FROM codes WHERE zone = ?', (a['key'],)).fetchone()
            out['numbers'] = {'lowest': r[0], 'highest': r[1], 'tailReserveFrom': tail_start(a),
                              'free': sum(hi - lo + 1 for lo, hi in a['blocks']) - r[2]}
        out['sameName'] = [x['key'] for x in self.engine.families.get(a['nameKey'], []) if x['key'] != a['key']]
        return out

    def areas_search(self, st, query, **_):
        name = self._q(query, 'name')
        if len(name) > 100:
            raise ApiError(400, 'bad_request', 'name is at most 100 characters.')
        k = E.name_key(name)
        found = self.engine.areas_named(name)
        match = 'name'
        if not found:
            found = [a for a in self.engine.areas if E.name_key(a['official']) == k]
            match = 'official'
        if not found and len(k) >= 3:
            found = [a for a in self.engine.areas if a['nameKey'].startswith(k) or E.name_key(a['official']).startswith(k)][:50]
            match = 'prefix'
        counts = {}
        if found:
            counts = dict(st.con.execute('SELECT zone, sum(n) FROM zone_counts WHERE zone IN (%s) GROUP BY zone' % ','.join('?' * len(found)),
                                         [a['key'] for a in found]).fetchall())
        return {'name': name, 'nameKey': k, 'match': match if found else None, 'count': len(found),
                'results': [area_json(self.engine, a, counts) for a in sorted(found, key=lambda a: a['key'])]}

    def issue(self, st, headers, body, **_):
        who = self._key(headers)
        data = self._json(body)
        try:
            row = I.issue(st, self.engine, who, data, self.per_day, card=lambda r: card(self.engine, r))
        except I.Refused as e:
            raise ApiError(e.status, e.code, e.message, {'existing': e.card} if e.card else None)
        return 201, card(self.engine, row)

    def change(self, st, machine, headers, body, **_):
        self._key(headers)
        m, _a, _n = self._machine(machine)
        data = self._json(body)
        try:
            row = I.change(st, self.engine, m, data)
        except I.Refused as e:
            raise ApiError(e.status, e.code, e.message)
        return card(self.engine, row)


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = 'n-ways-addresses-bf'
    sys_version = ''
    protocol_version = 'HTTP/1.1'

    def _cors(self):
        origin = self.headers.get('Origin')
        cors = self.app.cors
        if origin and ('*' in cors or origin in cors):
            self.send_header('Access-Control-Allow-Origin', '*' if '*' in cors else origin)
            self.send_header('Vary', 'Origin')
            return True
        return False

    def _send(self, status, payload, extra=None):
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public, max-age=60' if self.command in ('GET', 'HEAD') and status == 200 else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self._cors()
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _run(self):
        started = time.time()
        status = 500
        try:
            parts = urlsplit(self.path)
            try:
                n = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                raise ApiError(400, 'bad_request', 'Content-Length is not a number.')
            if n > BODY_MAX:
                self.close_connection = True
                raise ApiError(413, 'too_large', 'The body is over %d bytes.' % BODY_MAX)
            body = self.rfile.read(n) if n else b''
            method = 'GET' if self.command == 'HEAD' else self.command
            status, payload, extra = self.app.handle(method, parts.path, parse_qs(parts.query, keep_blank_values=True),
                                                     self.headers, body)
            self._send(status, payload, extra)
        except ApiError as e:
            status = e.status
            payload = {'error': {'code': e.code, 'message': e.message}}
            headers = {}
            for k, v in (e.extra or {}).items():
                if k[:1].isupper():
                    headers[k] = v
                else:
                    payload['error'][k] = v
            self._send(status, payload, headers)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            status = 500
            self._send(500, {'error': {'code': 'internal', 'message': 'Something went wrong on the server. It has been logged.'}})
        finally:
            if self.app.log:
                sys.stderr.write('%s %s %s %d %.0fms\n' % (self.log_date_time_string(), self.command, self.path.split('?')[0], status,
                                                          (time.time() - started) * 1000))

    do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = do_HEAD = _run

    def do_OPTIONS(self):
        self.send_response(204)
        if self._cors():
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
            self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def make_server(app, host, port):
    handler = type('H', (Handler,), {'app': app})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    return httpd


def serve(app, host, port):
    httpd = make_server(app, host, port)
    sys.stderr.write('N-Ways Addressing for Burkina Faso: serving %s on http://%s:%d/v1 (%s)\n'
                     % (app.db, host, port, 'issuing' if app.keys else 'read-only'))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
