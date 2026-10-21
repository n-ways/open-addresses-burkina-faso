"""Tests of the registry server: python3 -m unittest discover -s server/tests -t .

The fixture (server/testdata/registry) is the published registry of one commune, Wolonkoto
(postcode 95500, 2,931 codes), with the areas of the names it uses. parity-expected.json holds what
the N-Ways issuer gives for the issue scenario in parity-scenario.json on that fixture.
server/testdata/registry-gaps holds 24 published codes, in 17 communes, whose entrances lie in no
commune outline (gaps between outlines), with their areas.
"""
import csv
import gzip
import hashlib
import http.client
import io
import json
import os
import shutil
import tempfile
import threading
import time
import unittest

from server import store as S
from server.api import App, make_server
from server.engine import Engine, dist_door

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(os.path.dirname(HERE), 'testdata')
FIXTURE = os.path.join(TESTDATA, 'registry')
GAPS = os.path.join(TESTDATA, 'registry-gaps')
KEY = 'test-issuing-key'
CODE = 'BF-95500-V001-100-4'          # Diurmanko 100
CODE_POINT = (10.6495898, -5.0373371)


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def gunzip(path):
    with gzip.open(path, 'rb') as f:
        return f.read()


def quiet(_msg):
    pass


class Server:
    """The API on a free local port, over real HTTP."""

    def __init__(self, db, keys=(), per_day=1000, cors=()):
        self.app = App(db, keys=keys, per_day=per_day, cors=cors, log=False)
        self.httpd = make_server(self.app, '127.0.0.1', 0)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def call(self, method, path, body=None, key=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        h = dict(headers or {})
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
            h['Content-Type'] = 'application/json'
        if key:
            h['Authorization'] = 'Bearer ' + key
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        self.last_headers = dict(r.getheaders())
        return r.status, (json.loads(raw.decode('utf-8')) if raw else None)

    def get(self, path):
        return self.call('GET', path)

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='bf-server-')
        self.db = os.path.join(self.tmp, 'addresses.sqlite')
        S.import_registry(FIXTURE, self.db, log=quiet)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def assertError(self, got, status, code):
        self.assertEqual(got[0], status, got[1])
        self.assertEqual(set(got[1]), {'error'})
        self.assertEqual(got[1]['error']['code'], code, got[1])
        self.assertTrue(got[1]['error']['message'])


# ---------------------------------------------------------------- import and export
class ImportExport(Base):
    def test_round_trip_is_byte_identical(self):
        out = os.path.join(self.tmp, 'out')
        con = S.connect(self.db, readonly=True)
        S.export_registry(con, out, log=quiet)
        con.close()
        for name in ('areas.csv', '95500.csv'):
            self.assertEqual(gunzip(os.path.join(FIXTURE, name + '.gz')), gunzip(os.path.join(out, name + '.gz')), name)
        with open(os.path.join(FIXTURE, 'MANIFEST.json'), 'rb') as a, open(os.path.join(out, 'MANIFEST.json'), 'rb') as b:
            self.assertEqual(a.read(), b.read())
        # the export is itself a valid registry
        S.import_registry(out, os.path.join(self.tmp, 'again.sqlite'), log=quiet)

    def test_counts(self):
        st = S.Store(self.db, readonly=True)
        self.assertEqual(st.count(), 2931)
        self.assertEqual(st.counts_by_unit(), {'95500': 2931})
        st.close()

    def test_reimport_is_safe(self):
        rep = S.import_registry(FIXTURE, self.db, log=quiet)
        self.assertEqual(rep['codes'], 2931)
        self.assertEqual(rep['carriedOver'], {'issued': 0, 'changed': 0, 'conflicts': []})

    def _copy(self):
        d = os.path.join(self.tmp, 'reg')
        shutil.copytree(FIXTURE, d)
        return d

    def _rewrite(self, d, name, data, manifest=None):
        with gzip.GzipFile(os.path.join(d, name + '.gz'), 'wb', mtime=0) as f:
            f.write(data)
        if manifest is not None:
            with open(os.path.join(d, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
                f.write(S.manifest_text(manifest))

    def _refused(self, d, words):
        before = os.path.getmtime(self.db)
        with self.assertRaises(S.RegistryError) as cm:
            S.import_registry(d, self.db, log=quiet)
        self.assertIn(words, str(cm.exception))
        self.assertEqual(os.path.getmtime(self.db), before)   # the database was left alone
        self.assertFalse(os.path.exists(self.db + '.importing'))

    def test_refuses_a_changed_file(self):
        d = self._copy()
        data = gunzip(os.path.join(d, '95500.csv.gz')).replace(b'Diurmanko 100,', b'Diurmanko 101,', 1)
        self._rewrite(d, '95500.csv', data)
        self._refused(d, 'SHA-256')

    def test_refuses_a_wrong_count(self):
        d = self._copy()
        man = load_json(os.path.join(d, 'MANIFEST.json'))
        man['byUnit']['95500'] = 2930
        self._rewrite(d, '95500.csv', gunzip(os.path.join(d, '95500.csv.gz')), man)
        self._refused(d, 'codes')

    def test_refuses_a_missing_or_unlisted_file(self):
        d = self._copy()
        os.remove(os.path.join(d, '95500.csv.gz'))
        self._refused(d, 'missing')
        d2 = os.path.join(self.tmp, 'reg2')
        shutil.copytree(FIXTURE, d2)
        shutil.copy(os.path.join(d2, '95500.csv.gz'), os.path.join(d2, '95501.csv.gz'))
        self._refused(d2, 'not listed')

    def test_refuses_another_country(self):
        d = self._copy()
        man = load_json(os.path.join(d, 'MANIFEST.json'))
        man['country'] = 'XX'
        self._rewrite(d, 'areas.csv', gunzip(os.path.join(d, 'areas.csv.gz')), man)
        self._refused(d, 'not of BF')

    def test_quoting_matches_the_publisher(self):
        self.assertEqual(S._csv_line(['a', 'b,c', 'say "x"', ' lead', '', '\\.']), 'a,"b,c","say ""x"""," lead",,"\\."\n')


# ---------------------------------------------------------------- the API
class Api(Base):
    def setUp(self):
        Base.setUp(self)
        self.srv = Server(self.db, keys=[KEY], cors=['https://example.org'])

    def tearDown(self):
        self.srv.close()
        Base.tearDown(self)

    def test_health_and_info(self):
        s, h = self.srv.get('/v1/health')
        self.assertEqual(s, 200)
        self.assertEqual((h['status'], h['country'], h['codes'], h['registryExported']), ('ok', 'BF', 2931, '2026-10-21T00:13:29Z'))
        s, i = self.srv.get('/v1/info')
        self.assertEqual(s, 200)
        self.assertEqual(i['counts']['codes'], 2931)
        self.assertEqual(i['licences'], {'data': 'ODbL-1.0', 'code': 'Apache-2.0', 'documents': 'CC-BY-4.0'})
        self.assertIn('N-WAYS LIMITED', i['credit'])
        self.assertEqual(i['engine'], 'internal/addressing/bf (SPEC v1.0)')

    def test_code_card(self):
        s, c = self.srv.get('/v1/codes/' + CODE)
        self.assertEqual(s, 200)
        self.assertEqual(c['machine'], CODE)
        self.assertEqual(c['remembered'], 'Diurmanko 100')
        self.assertEqual(c['spotCode'], 'BF-95500 E0466 N0769')
        self.assertEqual(c['zone'], {'key': '95500', 'name': 'Wolonkoto'})
        self.assertEqual(c['area']['key'], '95500-001')
        self.assertEqual(list(c['registry']), S.CODE_COLUMNS)
        self.assertEqual(c['registry']['machine'], CODE)
        self.assertNotIn(str(c['check']), c['remembered'])   # people never see the check digit

    def test_code_errors(self):
        self.assertError(self.srv.get('/v1/codes/BF-95500-V001-100-5'), 400, 'check_digit')
        self.assertError(self.srv.get('/v1/codes/BF-95500-V001-999-1'), 400, 'not_in_blocks')
        self.assertError(self.srv.get('/v1/codes/BF-95500-V099-100-1'), 400, 'unknown_area')
        self.assertError(self.srv.get('/v1/codes/nonsense'), 400, 'bad_code')
        # a valid number nobody has yet
        st = S.Store(self.db, readonly=True)
        eng = Engine(st.area_rows())
        st.close()
        free = next(n for n in range(100, 230) if n not in self._numbers('95500-001'))
        m = eng.forms(eng.area('95500-001'), free)['machine']
        self.assertError(self.srv.get('/v1/codes/' + m), 404, 'not_issued')

    def _numbers(self, zone):
        st = S.Store(self.db, readonly=True)
        try:
            return {r['number'] for r in st.zone_numbers(zone)}
        finally:
            st.close()

    def test_find_every_form(self):
        for q in ('Diurmanko 100', 'diurmanko 100', 'DIURMANKO  100', 'Diourmanko 100', 'Diurmanko 100-4', 'Diurmanko · 100',
                  CODE, CODE.lower(), 'BF-95500-V001-100', 'BF-95500 E0466 N0769'):
            s, f = self.srv.get('/v1/find?q=' + q.replace(' ', '%20').replace('·', '%C2%B7'))
            self.assertEqual(s, 200, (q, f))
            self.assertEqual(f['results'][0]['machine'], CODE, q)
        s, f = self.srv.get('/v1/find?q=Wolonkoto%2037%2028')
        self.assertEqual(s, 404)
        self.assertEqual(f['error']['code'], 'not_issued')

    def test_find_errors(self):
        self.assertError(self.srv.get('/v1/find?q=Diurmanko%20100-5'), 400, 'check_digit')
        self.assertError(self.srv.get('/v1/find?q=BF-95500-V001-100-5'), 400, 'check_digit')
        self.assertError(self.srv.get('/v1/find?q=Nowhereville%20100'), 404, 'unknown_name')
        self.assertError(self.srv.get('/v1/find?q=Diurmanko%201000'), 404, 'wrong_digits')
        self.assertError(self.srv.get('/v1/find?q=Diurmanko%20999'), 404, 'not_in_blocks')
        self.assertError(self.srv.get('/v1/find?q=Secteur%2015%20Ouaga%2048%20217'), 400, 'secteur')
        self.assertError(self.srv.get('/v1/find?q=BF-95500%20E0001%20N0001'), 404, 'not_found')
        self.assertError(self.srv.get('/v1/find?q=hello'), 400, 'bad_query')
        self.assertError(self.srv.get('/v1/find'), 400, 'bad_request')

    def test_find_official_address(self):
        # A copy of the fixture where two compounds carry an official street (synthetic edit; the
        # official streets of Ouagadougou and Bobo-Dioulasso are in their own commune files).
        d = os.path.join(self.tmp, 'official')
        shutil.copytree(FIXTURE, d)
        rows = list(csv.reader(io.StringIO(gunzip(os.path.join(d, '95500.csv.gz')).decode('utf-8'))))
        for r in rows[1:3]:
            r[14] = 'Rue 12.004, Wolonkoto'
        buf = ''.join(S._csv_line(r) for r in rows).encode('utf-8')
        man = load_json(os.path.join(d, 'MANIFEST.json'))
        man['sha256']['95500.csv'] = hashlib.sha256(buf).hexdigest()
        with gzip.GzipFile(os.path.join(d, '95500.csv.gz'), 'wb', mtime=0) as f:
            f.write(buf)
        with open(os.path.join(d, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
            f.write(S.manifest_text(man))
        db = os.path.join(self.tmp, 'official.sqlite')
        S.import_registry(d, db, log=quiet)
        srv = Server(db)
        try:
            for q in ('Rue 12.004, Wolonkoto', 'rue 12.004', 'RUE 12 004'):
                s, f = srv.get('/v1/find?q=' + q.replace(' ', '%20').replace(',', '%2C'))
                self.assertEqual(s, 200, q)
                self.assertEqual((f['kind'], f['count']), ('official', 2))
        finally:
            srv.close()

    def test_at(self):
        s, a = self.srv.get('/v1/at?lat=%f&lng=%f' % CODE_POINT)
        self.assertEqual(s, 200)
        self.assertEqual((a['status'], a['code']['machine'], a['distanceM']), ('found', CODE, 0.0))
        # 8 m north: still the compound (within 12 m of its entrance)
        s, a = self.srv.get('/v1/at?lat=%f&lng=%f' % (CODE_POINT[0] + 8 / 110574, CODE_POINT[1]))
        self.assertEqual((a['status'], a['code']['machine']), ('found', CODE))
        s, a = self.srv.get('/v1/at?lat=10.66&lng=-5.03')
        self.assertEqual(s, 200)
        self.assertEqual(a['status'], 'none')
        self.assertEqual(a['zone']['key'], '95500')
        self.assertTrue(a['area']['key'].startswith('95500-'))
        self.assertTrue(a['spotCode'].startswith('BF-95500 '))
        self.assertError(self.srv.get('/v1/at?lat=48.85&lng=2.35'), 404, 'outside')
        self.assertError(self.srv.get('/v1/at?lat=abc&lng=2'), 400, 'bad_request')
        self.assertError(self.srv.get('/v1/at?lat=91&lng=2'), 400, 'bad_request')

    def test_near(self):
        s, n = self.srv.get('/v1/near?lat=%f&lng=%f&radius=100' % CODE_POINT)
        self.assertEqual(s, 200)
        self.assertEqual(n['results'][0]['machine'], CODE)
        d = [r['distanceM'] for r in n['results']]
        self.assertEqual(d, sorted(d))
        self.assertTrue(all(x <= 100 for x in d))
        s, n = self.srv.get('/v1/near?lat=%f&lng=%f&radius=500&limit=3' % CODE_POINT)
        self.assertEqual(n['count'], 3)
        self.assertError(self.srv.get('/v1/near?lat=%f&lng=%f&radius=501' % CODE_POINT), 400, 'bad_request')
        self.assertError(self.srv.get('/v1/near?lat=%f&lng=%f&limit=101' % CODE_POINT), 400, 'bad_request')

    def test_verify(self):
        s, v = self.srv.get('/v1/verify?code=' + CODE)
        self.assertEqual((s, v['syntax'], v['checkDigit'], v['inBlocks'], v['issued']), (200, True, True, True, True))
        s, v = self.srv.get('/v1/verify?code=BF-95500-V001-100-5')
        self.assertEqual((v['checkDigit'], v['issued']), (False, False))
        s, v = self.srv.get('/v1/verify?code=BF-95500-V001-1-1')
        self.assertFalse(v['syntax'])
        self.assertError(self.srv.get('/v1/verify'), 400, 'bad_request')

    def test_spot(self):
        s, p = self.srv.get('/v1/spot?lat=%f&lng=%f' % CODE_POINT)
        self.assertEqual((s, p['spotCode']), (200, 'BF-95500 E0466 N0769'))
        s, d = self.srv.get('/v1/spot/decode?code=BF-95500%20E0466%20N0769')
        self.assertEqual(s, 200)
        self.assertLess(dist_door(d['centre']['lat'], d['centre']['lng'], *CODE_POINT), 8)
        self.assertError(self.srv.get('/v1/spot?lat=48.85&lng=2.35'), 404, 'outside')
        # in no commune outline (SPEC 5.1): the gap between the Ouagadougou and Komsilga outlines
        s, p = self.srv.get('/v1/spot?lat=12.2781536&lng=-1.5450458')
        self.assertEqual((s, p['spotCode'], p['zone']['key']), (200, 'BF-10990 E2012 N2633', '10990'))
        # south of every frame within 10 km: the nearest edge cell (the entrance of BF-32250-V024-2302-1)
        s, p = self.srv.get('/v1/spot?lat=10.9987819&lng=-0.9736617')
        self.assertEqual((s, p['spotCode']), (200, 'BF-32250 E1052 N0000'))
        self.assertError(self.srv.get('/v1/spot/decode?code=BF-95500%20E466%20N0769'), 400, 'bad_code')
        self.assertError(self.srv.get('/v1/spot/decode?code=BF-00000%20E0466%20N0769'), 400, 'bad_code')

    def test_zones_and_areas(self):
        s, z = self.srv.get('/v1/zones')
        self.assertEqual(s, 200)
        self.assertEqual(z['count'], 351)
        w = next(x for x in z['zones'] if x['key'] == '95500')
        self.assertEqual((w['name'], w['codes']), ('Wolonkoto', 2931))
        s, z = self.srv.get('/v1/zones/95500')
        self.assertEqual(sum(a['codes'] for a in z['areas']), 2931)
        self.assertError(self.srv.get('/v1/zones/99999'), 404, 'not_found')
        s, a = self.srv.get('/v1/areas/95500-001')
        self.assertEqual((s, a['plateName'], a['blocks']), (200, 'Diurmanko', [[100, 229]]))
        s, a2 = self.srv.get('/v1/areas/%d' % a['id'])
        self.assertEqual(a2['key'], '95500-001')
        self.assertError(self.srv.get('/v1/areas/95500-999'), 404, 'not_found')
        s, r = self.srv.get('/v1/areas?name=diourmanko')
        self.assertEqual((r['match'], r['results'][0]['key']), ('name', '95500-001'))
        s, r = self.srv.get('/v1/areas?name=Wolon')
        self.assertEqual(r['match'], 'prefix')
        self.assertError(self.srv.get('/v1/areas'), 400, 'bad_request')

    def test_paging(self):
        seen, after = [], ''
        while True:
            s, p = self.srv.get('/v1/zones/95500/codes?limit=1000&after=' + after)
            self.assertEqual(s, 200)
            seen += [r['machine'] for r in p['results']]
            if not p['next']:
                break
            after = p['next']
        self.assertEqual(len(seen), 2931)
        self.assertEqual(seen, sorted(seen))
        self.assertError(self.srv.get('/v1/zones/95500/codes?limit=1001'), 400, 'bad_request')

    def test_http_errors(self):
        self.assertError(self.srv.get('/v1/nothing'), 404, 'not_found')
        self.assertError(self.srv.call('DELETE', '/v1/codes/' + CODE), 405, 'method_not_allowed')
        self.assertError(self.srv.call('POST', '/v1/codes', {'lat': 10.7, 'lng': -5.0}), 401, 'unauthorized')
        self.assertError(self.srv.call('POST', '/v1/codes', {'lat': 10.7, 'lng': -5.0}, key='wrong'), 401, 'unauthorized')
        self.assertError(self.srv.call('POST', '/v1/codes', b'{not json', key=KEY), 400, 'bad_request')
        self.assertError(self.srv.call('POST', '/v1/codes', b'x' * 70000, key=KEY), 413, 'too_large')

    def test_cors(self):
        self.srv.call('GET', '/v1/health', headers={'Origin': 'https://example.org'})
        self.assertEqual(self.srv.last_headers.get('Access-Control-Allow-Origin'), 'https://example.org')
        self.srv.call('GET', '/v1/health', headers={'Origin': 'https://other.example'})
        self.assertNotIn('Access-Control-Allow-Origin', self.srv.last_headers)

    def test_read_only_deployment(self):
        ro = Server(self.db)
        try:
            self.assertError(ro.call('POST', '/v1/codes', {'lat': 10.7, 'lng': -5.0}, key=KEY), 403, 'read_only')
            self.assertError(ro.call('PATCH', '/v1/codes/' + CODE, {'status': 'confirmed'}, key=KEY), 403, 'read_only')
        finally:
            ro.close()


# ---------------------------------------------------------------- the engine's conformance vectors
class Conformance(unittest.TestCase):
    def test_numbering_vectors(self):
        """The server's numbering reproduces the reference engine's conformance vectors
        (engine/reference/vectors.json, "numbering"): first issue, then 60 new compounds."""
        from server.engine import REPO, next_free
        v = load_json(os.path.join(REPO, 'engine', 'reference', 'vectors.json'))['numbering']
        reg = load_json(os.path.join(REPO, 'engine', 'data', 'register.json'))
        a = next(x for x in reg['areas'] if x['key'] == v['zone'])
        area = {'frame': a['frame'], 'blocks': [list(b) for b in a['blocks']]}
        issued = [{'number': v['numbers'][c['id']], 'lat': c['lat'], 'lon': c['lon'], 'key': c['id']} for c in v['compounds']]
        for i, ins in enumerate(v['inserts']):
            self.assertEqual(next_free(area, issued, ins['lat'], ins['lon']), ins['number'], i)
            issued.append({'number': ins['number'], 'lat': ins['lat'], 'lon': ins['lon'], 'key': 'i%02d' % i})


    def test_spots_outside_vectors(self):
        """Points in no commune outline (engine/reference/vectors.json, "spotsOutside"): the server
        codes them in the same commune frame as the reference engine and counts them in the country
        unless they lie more than 300 m outside the national border (SPEC 1b), or refuses them."""
        from server.engine import REPO
        eng = Engine([])
        vs = load_json(os.path.join(REPO, 'engine', 'reference', 'vectors.json'))['spotsOutside']
        self.assertGreaterEqual(len(vs), 600)
        for v in vs:
            self.assertIsNone(eng.commune_at(v['lat'], v['lon']))
            self.assertEqual(eng.in_country(v['lat'], v['lon']), 'error' not in v and not eng.abroad(v['lat'], v['lon']), v)
            if 'error' in v:
                with self.assertRaises(ValueError):
                    eng.spot(v['lat'], v['lon'])
                continue
            code = eng.spot(v['lat'], v['lon'])
            self.assertEqual(code, v['code'])
            lat, lng, c = eng.spot_point(code)
            self.assertEqual(([lat, lng], c['postcode']), (v['decoded'], v['commune']))


# ---------------------------------------------------------------- issuing
class Issue(Base):
    def setUp(self):
        Base.setUp(self)
        self.srv = Server(self.db, keys=[KEY], per_day=1000)

    def tearDown(self):
        self.srv.close()
        Base.tearDown(self)

    def issue(self, body):
        return self.srv.call('POST', '/v1/codes', body, key=KEY)

    def test_parity_with_the_issuer(self):
        """Every step of the scenario gives the number, forms, spot code and blocks the N-Ways
        issuer gives on the same registry: doors that fill Diurmanko's block, its tail reserve and
        an extension block, then new compounds far from any code across the commune."""
        steps = load_json(os.path.join(TESTDATA, 'parity-scenario.json'))
        want = load_json(os.path.join(TESTDATA, 'parity-expected.json'))
        self.assertEqual(len(steps), len(want))
        extended = False
        for i, (step, w) in enumerate(zip(steps, want)):
            body = {'lat': step['lat'], 'lng': step['lng']}
            if step['kind'] == 'door':
                body['of'] = step['of']
            s, c = self.issue(body)
            if w.get('Err'):
                self.assertEqual(s, 422, (i, c))
                self.assertEqual(c['error']['code'], 'too_far')
                continue
            self.assertEqual(s, 201, (i, c))
            got = (c['area']['key'], c['number'], c['machine'], c['home'], c['remembered'], c['spotCode'], c['area']['blocks'])
            self.assertEqual(got, (w['Zone'], w['Number'], w['Machine'], w['Home'], w['Written'], w['Spot'], w['Blocks']), i)
            self.assertEqual((c['status'], c['issued']), ('provisional', 'on-demand'))
            extended = extended or len(w['Blocks']) > 1
        self.assertTrue(extended)

    def test_new_blocks_persist_and_export(self):
        steps = load_json(os.path.join(TESTDATA, 'parity-scenario.json'))
        for step in steps[:80]:
            self.issue({'lat': step['lat'], 'lng': step['lng'], 'of': step['of']})
        s, a = self.srv.get('/v1/areas/95500-001')
        self.assertEqual(len(a['blocks']), 2)
        out = os.path.join(self.tmp, 'out')
        con = S.connect(self.db, readonly=True)
        man = S.export_registry(con, out, log=quiet)
        con.close()
        self.assertEqual(man['codes'], 2931 + 80)
        self.assertNotEqual(man['exported'], '2026-10-21T00:13:29Z')
        areas = gunzip(os.path.join(out, 'areas.csv.gz')).decode('utf-8')
        self.assertIn('100-229|%d-%d' % tuple(a['blocks'][1]), areas)
        # a fresh server on the exported registry decodes the new block at once
        db2 = os.path.join(self.tmp, 'second.sqlite')
        S.import_registry(out, db2, log=quiet)
        srv2 = Server(db2)
        try:
            n = a['blocks'][1][0]
            s, f = srv2.get('/v1/find?q=Diurmanko%20' + str(n))
            self.assertEqual((s, f['results'][0]['number']), (200, n))
        finally:
            srv2.close()

    def test_reimport_keeps_local_codes(self):
        s, c = self.issue({'lat': CODE_POINT[0] + 0.0002, 'lng': CODE_POINT[1], 'of': CODE})
        self.assertEqual(s, 201)
        self.srv.call('PATCH', '/v1/codes/' + CODE, {'status': 'confirmed'}, key=KEY)
        rep = S.import_registry(FIXTURE, self.db, log=quiet)
        self.assertEqual(rep['carriedOver']['issued'], 1)
        self.assertEqual(rep['carriedOver']['changed'], 1)
        st = S.Store(self.db, readonly=True)
        self.assertEqual(st.by_machine(CODE)['status'], 'confirmed')
        self.assertIsNotNone(st.by_machine(c['machine']))
        st.close()

    def test_already_has_a_code(self):
        s, c = self.issue({'lat': CODE_POINT[0] + 1 / 110574, 'lng': CODE_POINT[1]})   # 1 m from an entrance
        self.assertEqual(s, 409)
        self.assertEqual(c['error']['code'], 'exists')
        self.assertEqual(c['error']['existing']['machine'], CODE)
        d = 0.0001
        ring = [[CODE_POINT[1] - d, CODE_POINT[0] - d], [CODE_POINT[1] + d, CODE_POINT[0] - d],
                [CODE_POINT[1] + d, CODE_POINT[0] + d], [CODE_POINT[1] - d, CODE_POINT[0] + d]]
        s, c = self.issue({'lat': CODE_POINT[0] + 0.00009, 'lng': CODE_POINT[1] + 0.00009, 'outline': ring})
        self.assertEqual((s, c['error']['code']), (409, 'exists'))

    def test_outline_checks(self):
        lat, lng = 10.7406, -5.1342
        tiny = [[lng, lat], [lng + 0.00001, lat], [lng + 0.00001, lat + 0.00001]]
        self.assertError(self.issue({'lat': lat, 'lng': lng, 'outline': tiny}), 422, 'bad_outline')
        huge = [[lng, lat], [lng + 0.01, lat], [lng + 0.01, lat + 0.01], [lng, lat + 0.01]]
        self.assertError(self.issue({'lat': lat, 'lng': lng, 'outline': huge}), 422, 'bad_outline')
        good = [[lng, lat], [lng + 0.0002, lat], [lng + 0.0002, lat + 0.0002], [lng, lat + 0.0002], [lng, lat]]
        s, c = self.issue({'lat': lat + 0.0001, 'lng': lng + 0.0001, 'outline': good})
        self.assertEqual(s, 201, c)
        self.assertEqual((c['building']['structures'], c['building']['class']), (1, 'residential'))
        # the outline issued here now holds its own point
        self.assertError(self.issue({'lat': lat + 0.00015, 'lng': lng + 0.00015}), 409, 'exists')
        s, a = self.srv.get('/v1/at?lat=%f&lng=%f' % (lat + 0.00015, lng + 0.00015))
        self.assertEqual((a['status'], a['code']['machine']), ('found', c['machine']))

    def test_refusals(self):
        self.assertError(self.issue({'lat': 48.85, 'lng': 2.35}), 422, 'outside')
        self.assertError(self.issue({'lat': 'x', 'lng': 2}), 400, 'bad_request')
        self.assertError(self.issue([1, 2]), 400, 'bad_request')
        self.assertError(self.issue({'lat': 10.7, 'lng': -5.0, 'of': 'BF-95500-V001-229-9'}), 404, 'not_found')
        self.assertError(self.issue({'lat': 10.7, 'lng': -5.0, 'of': 'BF-95500-V001-999-1'}), 400, 'not_in_blocks')
        self.assertError(self.issue({'lat': CODE_POINT[0], 'lng': CODE_POINT[1], 'of': CODE[:-1] + '5'}), 400, 'check_digit')
        self.assertError(self.issue({'lat': CODE_POINT[0], 'lng': CODE_POINT[1], 'of': 'Diurmanko 100'}), 400, 'bad_code')
        self.assertError(self.issue({'lat': CODE_POINT[0] + 0.001, 'lng': CODE_POINT[1], 'of': CODE}), 422, 'too_far')

    def test_counts_follow_issues_and_changes(self):
        s, c = self.issue({'lat': CODE_POINT[0], 'lng': CODE_POINT[1], 'of': CODE})
        self.assertEqual(s, 201)
        self.assertEqual(self.srv.get('/v1/health')[1]['codes'], 2932)
        self.srv.call('PATCH', '/v1/codes/' + c['machine'], {'status': 'retired'}, key=KEY)
        s, a = self.srv.get('/v1/areas/95500-001')
        self.assertEqual(a['byStatus'].get('retired'), 1)
        self.assertEqual(a['codes'], 64)
        s, i = self.srv.get('/v1/info')
        self.assertEqual(i['counts']['byStatus'], {'provisional': 2931, 'retired': 1})
        s, z = self.srv.get('/v1/zones/95500')
        self.assertEqual(z['codes'], 2932)

    def test_daily_limit(self):
        limited = Server(self.db, keys=[KEY], per_day=2)
        try:
            for i in range(2):
                s, c = limited.call('POST', '/v1/codes', {'lat': CODE_POINT[0], 'lng': CODE_POINT[1], 'of': CODE}, key=KEY)
                self.assertEqual(s, 201, c)
            self.assertError(limited.call('POST', '/v1/codes', {'lat': CODE_POINT[0], 'lng': CODE_POINT[1], 'of': CODE}, key=KEY),
                             429, 'rate_limited')
        finally:
            limited.close()

    def test_change(self):
        s, c = self.srv.call('PATCH', '/v1/codes/' + CODE, {'status': 'confirmed'}, key=KEY)
        self.assertEqual((s, c['status']), (200, 'confirmed'))
        target = {'lat': CODE_POINT[0] + 30 / 110574, 'lng': CODE_POINT[1]}
        s, c = self.srv.call('PATCH', '/v1/codes/' + CODE, {'entrance': target}, key=KEY)
        self.assertEqual((s, c['entrance']['kind']), (200, 'gate'))
        self.assertAlmostEqual(c['entrance']['lat'], target['lat'], places=6)
        self.assertEqual(c['spotCode'], c['registry']['spot_code'])
        far = {'lat': CODE_POINT[0] + 0.002, 'lng': CODE_POINT[1]}
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + CODE, {'entrance': far}, key=KEY), 422, 'too_far')
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + CODE, {'status': 'lost'}, key=KEY), 400, 'bad_request')
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + CODE, {}, key=KEY), 400, 'bad_request')
        s, c = self.srv.call('PATCH', '/v1/codes/' + CODE, {'status': 'retired'}, key=KEY)
        self.assertEqual(c['status'], 'retired')
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + CODE, {'status': 'confirmed'}, key=KEY), 409, 'retired')
        self.assertError(self.srv.get('/v1/find?q=Diurmanko%20100'), 410, 'retired')
        s, a = self.srv.get('/v1/at?lat=%f&lng=%f' % (target['lat'], target['lng']))
        self.assertTrue(a['status'] == 'none' or a['code']['machine'] != CODE)
        # a retired number is never given again
        st = S.Store(self.db, readonly=True)
        self.assertIn(100, {r['number'] for r in st.zone_numbers('95500-001')})
        st.close()
        self.assertError(self.srv.call('PATCH', '/v1/codes/BF-95500-V001-100-5', {'status': 'confirmed'}, key=KEY), 400, 'check_digit')

    def test_concurrent_issues_never_share_a_number(self):
        steps = load_json(os.path.join(TESTDATA, 'parity-scenario.json'))[:20]
        got = []

        def go(step):
            got.append(self.issue({'lat': step['lat'], 'lng': step['lng'], 'of': step['of']}))
        ts = [threading.Thread(target=go, args=(s,)) for s in steps]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        nums = [c['number'] for s, c in got if s == 201]
        self.assertEqual(len(nums), 20)
        self.assertEqual(len(set(nums)), 20)



# ---------------------------------------------------------------- points in no commune outline
class Gaps(unittest.TestCase):
    """A point in no commune outline is in Burkina Faso when it has a spot code (SPEC 5.1) and lies
    within 300 m of the national border (SPEC 1b), as the issuer decides: the compounds in the gaps
    between outlines are found by location, can be issued and can have their entrance moved; a point
    far outside is still refused."""
    FREE = (12.2773134, -1.5392087)   # 33 m east of BF-10000-V076-34202-5, in no outline, no code within 12 m

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='bf-gaps-')
        self.db = os.path.join(self.tmp, 'addresses.sqlite')
        S.import_registry(GAPS, self.db, log=quiet)
        self.srv = Server(self.db, keys=[KEY])
        st = S.Store(self.db, readonly=True)
        self.rows = [dict(r) for r in st.con.execute('SELECT machine, zone, entrance_lat, entrance_lng, spot_code FROM codes ORDER BY machine')]
        st.close()

    def tearDown(self):
        self.srv.close()
        shutil.rmtree(self.tmp)

    def assertError(self, got, status, code):
        self.assertEqual(got[0], status, got[1])
        self.assertEqual(got[1]['error']['code'], code, got[1])

    ACROSS = 'BF-60250-V007-291-6'    # published, 297.8 m outside the border: beyond what the shipped outline accepts

    def test_issued_entrances_are_found(self):
        eng = self.srv.app.engine
        self.assertEqual(len(self.rows), 24)
        for r in self.rows:
            lat, lng = float(r['entrance_lat']), float(r['entrance_lng'])
            self.assertIsNone(eng.commune_at(lat, lng), r['machine'])
            self.assertEqual(eng.in_country(lat, lng), r['machine'] != self.ACROSS, r['machine'])
            s, a = self.srv.get('/v1/at?lat=%s&lng=%s' % (r['entrance_lat'], r['entrance_lng']))
            self.assertEqual(s, 200, a)
            self.assertEqual((a['status'], a['code']['machine'], a['distanceM']), ('found', r['machine'], 0.0))
            # the area follows the rule for a new code: here the area of the code itself
            self.assertEqual(a['area']['key'], r['zone'])
            self.assertEqual(a['zone']['key'], r['zone'][:5])

    def test_issue_and_move_in_a_gap(self):
        lat, lng = self.FREE
        self.assertIsNone(self.srv.app.engine.commune_at(lat, lng))
        s, a = self.srv.get('/v1/at?lat=%f&lng=%f' % self.FREE)
        self.assertEqual(s, 200, a)
        self.assertEqual((a['status'], a['newCodeArea'], a['area']['key'], a['zone']['key']), ('none', '10000-076', '10000-076', '10000'))
        self.assertEqual(a['spotCode'], 'BF-10990 E2076 N2624')
        s, c = self.srv.call('POST', '/v1/codes', {'lat': lat, 'lng': lng}, key=KEY)
        self.assertEqual(s, 201, c)
        self.assertEqual((c['area']['key'], c['spotCode'], c['status']), ('10000-076', 'BF-10990 E2076 N2624', 'provisional'))
        s, f = self.srv.get('/v1/at?lat=%f&lng=%f' % self.FREE)
        self.assertEqual((f['status'], f['code']['machine']), ('found', c['machine']))
        # its entrance moves 10 m north, still in the gap
        to = {'lat': lat + 10 / 110574, 'lng': lng}
        self.assertIsNone(self.srv.app.engine.commune_at(to['lat'], to['lng']))
        s, m = self.srv.call('PATCH', '/v1/codes/' + c['machine'], {'entrance': to}, key=KEY)
        self.assertEqual(s, 200, m)
        self.assertEqual(m['spotCode'], self.srv.app.engine.spot(to['lat'], to['lng']))

    def test_published_code_across_the_line_is_found_but_never_moved(self):
        """A published code is found at its entrance wherever it lies; a new code or an entrance
        move there is refused, because the shipped border cannot tell it is within 300 m."""
        r = next(r for r in self.rows if r['machine'] == self.ACROSS)
        lat, lng = float(r['entrance_lat']), float(r['entrance_lng'])
        self.assertTrue(self.srv.app.engine.abroad(lat, lng))
        s, a = self.srv.get('/v1/at?lat=%s&lng=%s' % (r['entrance_lat'], r['entrance_lng']))
        self.assertEqual((s, a['status'], a['code']['machine']), (200, 'found', self.ACROSS))
        self.assertError(self.srv.call('POST', '/v1/codes', {'lat': lat + 20 / 110574, 'lng': lng}, key=KEY), 422, 'outside')
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + self.ACROSS, {'entrance': {'lat': lat + 5 / 110574, 'lng': lng}}, key=KEY), 422, 'outside')

    def test_far_outside_is_refused(self):
        for lat, lng in ((16.0, -1.0), (48.85, 2.35)):
            self.assertFalse(self.srv.app.engine.in_country(lat, lng))
            self.assertError(self.srv.get('/v1/at?lat=%f&lng=%f' % (lat, lng)), 404, 'outside')
            self.assertError(self.srv.call('POST', '/v1/codes', {'lat': lat, 'lng': lng}, key=KEY), 422, 'outside')
        r = self.rows[0]
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + r['machine'], {'entrance': {'lat': 16.0, 'lng': -1.0}}, key=KEY), 422, 'too_far')


# ---------------------------------------------------------------- the national border
class Border(Base):
    """The border decides (engine/SPEC.md 1b): no code more than 300 m outside Burkina Faso's
    national border, whatever commune outline or spot frame holds the point. The points lie on one
    line across the border with a neighbouring country, at the given distance outside it."""
    INSIDE = (13.455609, 1.043709)    # 200 m inside the border
    NEAR = (13.458676, 1.044509)      # 150 m outside: within 300 m, so in Burkina Faso
    EDGE = (13.459464, 1.044715)      # 240 m outside
    BEYOND = (13.460113, 1.044884)    # 314 m outside, 75 m from EDGE
    BACK = (13.459237, 1.044655)      # 214 m outside, 26 m from EDGE
    ACROSS = [(13.460253, 1.044921),  # 330 m outside, inside a commune outline
              (13.470505, 1.047595),  # 1.5 km outside, inside a commune outline
              (13.401026, 1.204613)]  # 1.5 km outside, in no outline but with a spot code

    def setUp(self):
        Base.setUp(self)
        self.srv = Server(self.db, keys=[KEY])
        self.eng = self.srv.app.engine

    def tearDown(self):
        self.srv.close()
        Base.tearDown(self)

    def test_shipped_border(self):
        from server.engine import REPO
        path = os.path.join(REPO, 'engine', 'data', 'border.json')
        self.assertLess(os.path.getsize(path), 1 << 20)
        d = load_json(path)
        self.assertEqual((d['toleranceM'], d['borderM']), (3.0, 300.0))
        self.assertLessEqual(max(d['measuredM'].values()), d['toleranceM'])

    def test_outlines_reach_over_the_border_but_do_not_decide(self):
        for lat, lng in self.ACROSS:
            self.assertIsNotNone(self.eng.spot_commune(lat, lng), (lat, lng))
            self.assertTrue(self.eng.abroad(lat, lng), (lat, lng))
            self.assertFalse(self.eng.in_country(lat, lng), (lat, lng))
        self.assertIsNotNone(self.eng.commune_at(*self.ACROSS[0]))
        self.assertIsNotNone(self.eng.commune_at(*self.ACROSS[1]))
        self.assertIsNone(self.eng.commune_at(*self.ACROSS[2]))
        for lat, lng in (self.INSIDE, self.NEAR, self.EDGE, self.BACK):
            self.assertFalse(self.eng.abroad(lat, lng), (lat, lng))
            self.assertTrue(self.eng.in_country(lat, lng), (lat, lng))

    def test_issue_across_the_border_is_refused(self):
        for lat, lng in self.ACROSS:
            self.assertError(self.srv.call('POST', '/v1/codes', {'lat': lat, 'lng': lng}, key=KEY), 422, 'outside')
            self.assertError(self.srv.get('/v1/at?lat=%s&lng=%s' % (lat, lng)), 404, 'outside')

    def test_issue_inside_and_near_the_border_is_accepted(self):
        for lat, lng in (self.INSIDE, self.NEAR):
            s, c = self.srv.call('POST', '/v1/codes', {'lat': lat, 'lng': lng}, key=KEY)
            self.assertEqual(s, 201, c)
            self.assertEqual((c['status'], c['issued']), ('provisional', 'on-demand'))

    def test_entrance_never_moves_across_the_border(self):
        s, c = self.srv.call('POST', '/v1/codes', {'lat': self.EDGE[0], 'lng': self.EDGE[1]}, key=KEY)
        self.assertEqual(s, 201, c)
        to = {'lat': self.BEYOND[0], 'lng': self.BEYOND[1]}
        self.assertError(self.srv.call('PATCH', '/v1/codes/' + c['machine'], {'entrance': to}, key=KEY), 422, 'outside')
        to = {'lat': self.BACK[0], 'lng': self.BACK[1]}
        s, m = self.srv.call('PATCH', '/v1/codes/' + c['machine'], {'entrance': to}, key=KEY)
        self.assertEqual(s, 200, m)


if __name__ == '__main__':
    unittest.main()
