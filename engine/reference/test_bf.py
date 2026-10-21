#!/usr/bin/env python3
"""Offline tests for the Burkina Faso reference engine: python3 test_bf.py"""
import itertools, json, math, os, unittest
import bf_engine as e
import bf_border as b

_load = e._load_json

HERE = os.path.dirname(os.path.abspath(__file__))
V = _load(os.path.join(HERE, 'test_vectors.json'))


class Damm(unittest.TestCase):
    def test_vectors(self):
        for v in V['damm']:
            self.assertEqual(e.damm(v['digits']), v['check'])

    def test_every_single_error_and_adjacent_swap(self):
        base = '100001548217'
        good = base + str(e.damm(base))
        self.assertEqual(e.damm(good), 0)
        for i, ch in enumerate(good):
            for d in '0123456789':
                if d != ch:
                    self.assertNotEqual(e.damm(good[:i] + d + good[i + 1:]), 0)
        for i in range(len(good) - 1):
            if good[i] != good[i + 1]:
                s = good[:i] + good[i + 1] + good[i] + good[i + 2:]
                self.assertNotEqual(e.damm(s), 0)


class Forms(unittest.TestCase):
    def test_machine(self):
        for v in V['machine']:
            self.assertEqual(e.machine(*v['parts']), v['code'])
            p = e.parse_machine(v['code'])
            self.assertTrue(p['valid'])
            self.assertEqual([p['postcode'], p['kind'], p['place'], p['number']], v['parts'])

    def test_typo_caught(self):
        code = V['machine'][0]['code']
        pc, kind, num, chk = code.split('-')[1], code.split('-')[2], code.split('-')[3], code[-1]
        swapped = num[:-2] + num[-1] + num[-2]
        if swapped != num:
            self.assertFalse(e.parse_machine(f'BF-{pc}-{kind}-{swapped}-{chk}')['valid'])
        self.assertFalse(e.parse_machine(f'BF-{pc}-{kind}-{num}-{(int(chk) + 1) % 10}')['valid'])
        with self.assertRaises(ValueError):   # secteur codes are not issued
            e.parse_machine('BF-10000-S15-48217-6')

    def test_rejects(self):
        for bad in ['BF-1000-S15-48217', 'BF-10000-S015-48217', 'BF-10000-V15-48217', 'BF-10000-S15-08217', 'Secteur 15']:
            with self.assertRaises(ValueError):
                e.parse_machine(bad)
        with self.assertRaises(ValueError):
            e.machine('10000', 'S', '15', '08217')

    def test_remembered_has_no_letters_to_learn(self):
        for v in V['remembered']:
            t = e.remembered(v['area'], v['number'], v['kind'], v.get('town'))
            self.assertEqual(t, v['text'])
            digits = ''.join(c for c in t if c.isdigit())
            self.assertTrue(digits.endswith(v['number']))

    def test_secteur_needs_town(self):
        with self.assertRaises(ValueError):
            e.remembered('15', '48217', 'S')

    def test_spoken(self):
        for v in V['spoken_fr']:
            self.assertEqual(e.say_fr(v['number']), v['fr'])


class NationalNames(unittest.TestCase):
    """The remembered code is unique in the whole country on its own (SPEC 2.4)."""

    def test_vectors_decode_without_context(self):
        for v in V['names']:
            r = e.resolve_remembered(v['text'])
            self.assertEqual(r['code'], v['code'], v['text'])
            self.assertEqual((r['postcode'], r['kind'], r['place']), (v['postcode'], v['kind'], v['place']))
            self.assertTrue(e.parse_machine(r['code'])['valid'])

    def test_same_name_two_places(self):
        a = e.resolve_remembered(V['names'][0]['text'])
        b = e.resolve_remembered(V['names'][1]['text'])
        self.assertEqual(a['nameId'], b['nameId'])
        self.assertNotEqual((a['postcode'], a['place']), (b['postcode'], b['place']))
        # secteur codes are not issued: a town's homes carry the code of their quarter
        with self.assertRaises(ValueError):
            e.resolve_remembered('Secteur 15 Ouaga · 48 217')

    def test_rejected(self):
        for v in V['rejected']:
            with self.assertRaises(ValueError, msg=v['text']):
                e.resolve_remembered(v['text'])

    def test_name_keys(self):
        for v in V['nameKeys']:
            for n in v['names']:
                self.assertEqual(e.name_key(n), v['key'], n)
        self.assertNotEqual(e.name_key('Bissiga-Peulh'), e.name_key('Bissiga'))
        self.assertEqual(e.name_key('Lekoro'), 'LEKORO')  # 'Le' is an article only before a space
        self.assertTrue(e.is_generic("Campement d'éleveurs") and e.is_generic('village'))
        self.assertFalse(e.is_generic('Villy'))

    def test_one_area_per_number(self):
        RENAMED_FROM = {'UAGADUGU'}  # Ouaga 2000 and 1200 Logements left it (model/areas/renames.json)
        for k, v in e.names()['names'].items():
            last = v['range'][0] - 1
            for pc, ix, c, lo, hi in v['blocks']:
                # blocks follow each other and never overlap; an area renamed after first issue
                # (model/areas/renames.json) leaves its numbers retired, never reused
                self.assertGreater(lo, last, k)
                self.assertTrue(lo == last + 1 or k in RENAMED_FROM, k)
                self.assertGreaterEqual(hi - lo + 1, 2 * c)  # room to grow inside the block
                self.assertEqual(len(str(lo)), v['digits'])
                last = hi
            self.assertEqual(v['spareFrom'], last + 1)
            self.assertLessEqual(last, v['range'][0] + int((v['range'][1] - v['range'][0] + 1) * (1 - e.NAME_SPARE)) - 1)
            self.assertLessEqual(v['digits'], 5)

    def test_check_binds_name_number_area(self):
        # one area of a name with another area's number: no silent landing
        a, b = V['names'][0], V['names'][1]
        num_a = a['code'].split('-')[3]
        self.assertFalse(e.parse_machine(f"BF-{b['postcode']}-V{b['place']}-{num_a}")['inArea'])
        # same digits, other name id -> other check digit
        nid = e.name_id(a['postcode'], a['place'])
        self.assertNotEqual(e.machine(a['postcode'], 'V', a['place'], num_a, nid), e.machine(a['postcode'], 'V', a['place'], num_a, nid + 1))
        name = a['text'].rsplit(' ', 2)[0]
        good = int(a['code'][-1])
        with self.assertRaises(ValueError):
            e.resolve_remembered(f"{a['text']}-{(good + 1) % 10}")
        sw = num_a[:-2] + num_a[-1] + num_a[-2]
        if sw != num_a:
            try:
                r = e.resolve_remembered(f"{name} {sw}-{good}")
            except ValueError:
                r = None  # spare, or check digit caught it
            self.assertIsNone(r, 'a swapped number decoded silently')

    def test_frozen_blocks(self):
        entry = e.names()['names'][e.name_key(V['remembered'][0]['area'])]
        before = [b[:] for b in entry['blocks']]
        new = e.spare_block(entry, 120)
        self.assertEqual(new, (entry['spareFrom'], entry['spareFrom'] + 239))
        self.assertEqual(entry['blocks'], before)
        self.assertEqual(e.spare_block(entry, 120, taken=[new])[0], new[1] + 1)
        self.assertIsNone(e.spare_block(entry, (entry['range'][1] - entry['spareFrom']) // 2 + 10))  # spare used up -> qualifier

    def test_town_words_unique(self):
        t = e.towns()['byPostcode']
        self.assertEqual(len({e.name_key(v['word']) for v in t.values()}), len(t))
        with self.assertRaises(ValueError):   # kept for the secteur codes to come, not issued
            e.resolve_remembered('Secteur 2 Boussouma-Boulgou 1234')


class PlateNames(unittest.TestCase):
    """The name in the code is at most 12 characters and 2 words (SPEC 2.5)."""

    def test_vectors(self):
        for v in V['plates']:
            self.assertEqual(e.plate_ok(v['plateName']), v['fits'], v)
        for v in V['plateDecode']:
            r = e.resolve_remembered(v['text'])
            self.assertEqual(r['code'], v['code'], v['text'])
            self.assertEqual(r['area'], v['plateName'])
            self.assertTrue(e.plate_ok(r['area']))

    def test_long_official_name_decodes(self):
        off = [v for v in V['plateDecode'] if v['why'].startswith('the official')]
        for v in off:
            plate_text = v['plateName'] + ' ' + v['text'].rsplit(' ', 2)[-2] + ' ' + v['text'].rsplit(' ', 1)[-1] if len(v['text'].split()) > 2 else None
            a = e.resolve_remembered(v['text'])
            self.assertEqual(a['area'], v['plateName'])
            self.assertEqual(a['code'], v['code'])

    def test_over_limit_refused(self):
        for v in V['plateRejected']:
            self.assertFalse(e.plate_ok(v['plate']))
        with self.assertRaises(ValueError):
            e.remembered('Diakoumafindougou', '1929', 'V')
        # a provisional name is issued as it is (SPEC 2.5): no home waits for a naming decision
        self.assertEqual(e.remembered('Diakoumafindougou', '1929', 'V', provisional=True), 'Diakoumafindougou 19 29')
        with self.assertRaises(ValueError):
            e.remembered('15', '48217', 'S', 'Ouaga')   # secteur codes are not issued

    def test_every_issued_plate_fits_or_is_flagged(self):
        reg = _load(os.path.join(HERE, '..', '..', 'model', 'areas', 'register.json'))
        for pc, c in reg.items():
            for v in c['villages']:
                if 'plateName' not in v:
                    continue
                if not e.plate_ok(v['plateName']):
                    self.assertTrue(v.get('needsCouncilChoice'), v)
                if v.get('needsCouncilChoice'):
                    self.assertLessEqual(len(v['plateCandidates']), 3)
        for pc, t in e.towns()['byPostcode'].items():
            if not e.plate_ok(t['word']):
                self.assertTrue(t.get('needsCouncilChoice'), t)

    def test_aliases_unambiguous(self):
        al = e.names()['aliases']
        for ak, k in al.items():
            self.assertNotIn(ak, e.names()['names'])
            self.assertIn(k, e.names()['names'])


class Spot(unittest.TestCase):
    def test_vectors(self):
        for v in V['spot']:
            c = e.commune_at(v['lat'], v['lon'])
            self.assertEqual(c['postcode'], v['postcode'])
            self.assertEqual(e.spot_encode(v['lat'], v['lon']), v['spot'])
            lat, lon = e.spot_decode(v['spot'])
            self.assertAlmostEqual(lat, v['decoded'][0], places=6)
            self.assertAlmostEqual(lon, v['decoded'][1], places=6)

    def test_round_trip_within_cell(self):
        for v in V['spot']:
            lat, lon = e.spot_decode(v['spot'])
            dy = (lat - v['lat']) * e.M_PER_DEG_LAT
            dx = (lon - v['lon']) * e.M_PER_DEG_LON_EQ * math.cos(math.radians(lat))
            self.assertLess(math.hypot(dx, dy), 10 * math.sqrt(2) / 2 + 0.5)
            self.assertEqual(e.spot_encode(lat, lon, v['postcode']), v['spot'])

    def test_points_in_no_outline(self):
        """SPEC 5.1: the nearest commune within 10 km whose frame holds the point, else whose frame
        lies within 3,000 m (nearest edge cell); else refused. Decoding uses the commune named."""
        for v in V['spotOutside']:
            self.assertIsNone(e.commune_at(v['lat'], v['lon']), v['name'])
            if 'error' in v:
                self.assertIsNone(e.spot_commune(v['lat'], v['lon']))
                with self.assertRaises(ValueError):
                    e.spot_encode(v['lat'], v['lon'])
                continue
            self.assertEqual(e.spot_commune(v['lat'], v['lon']), v['postcode'])
            self.assertEqual(e.spot_encode(v['lat'], v['lon']), v['spot'])
            self.assertEqual(e.spot_frame_beyond(v['lat'], v['lon'], e.frames()[v['postcode']]) > 0, v['clamped'])
            self.assertEqual(list(e.spot_decode(v['spot'])), v['decoded'])
        self.assertEqual({('error' in v, v.get('clamped')) for v in V['spotOutside']}, {(False, False), (False, True), (True, None)})

    def test_vectors_points_in_no_outline(self):
        vs = _load(os.path.join(HERE, 'vectors.json'))['spotsOutside']
        self.assertGreaterEqual(len(vs), 600)
        for v in vs:
            if 'error' in v:
                self.assertIsNone(e.spot_commune(v['lat'], v['lon']))
                continue
            self.assertEqual(e.spot_encode(v['lat'], v['lon']), v['code'])
            self.assertEqual(e.spot_frame_beyond(v['lat'], v['lon'], e.frames()[v['commune']]) > 0, v['clamped'])

    def test_cos_lat(self):
        for i in range(-900, 901):
            self.assertAlmostEqual(e.cos_lat(i / 10), math.cos(math.radians(i / 10)), delta=1e-8)

    def test_frames_fit_every_commune(self):
        for pc, f in e.frames().items():
            self.assertIn(f['dx'], (4, 5))
            self.assertIn(f['dy'], (4, 5))


class Registry(unittest.TestCase):
    def test_samples(self):
        for v in V['registry']:
            comps, pts, nums, d, box = e.registry(os.path.join(HERE, v['sample']), v['digits'])
            self.assertEqual(len(comps), v['compounds'])
            self.assertEqual(sum(len(c['members']) for c in comps), v['structures'])
            got = sorted(nums.items(), key=lambda kv: kv[1])[:5]
            self.assertEqual([{'compound': k, 'number': n} for k, n in got], v['first'])
            self.assertEqual(len(set(nums.values())), len(nums))
            lo, main_hi, hi = e.number_range(d)
            self.assertTrue(all(lo <= n <= main_hi for n in nums.values()))
            p = e.provisional_number((v['newHome']['lon'], v['newHome']['lat']), nums, pts, box, d)
            self.assertEqual(p, v['newHome']['provisional'])
            self.assertNotIn(p, nums.values())

    def test_hilbert_neighbours(self):
        seen = set()
        for x, y in itertools.product(range(8), range(8)):
            seen.add(e.hilbert_index(3, x, y))
        self.assertEqual(seen, set(range(64)))

    def test_village_block(self):
        v = V['registry'][1]
        comps, pts, nums, d, box = e.registry(os.path.join(HERE, v['sample']), v['digits'])
        keys = sorted(pts)[:300]
        sub = {k: pts[k] for k in keys}
        entry = e.names()['names'][e.name_key(V['remembered'][0]['area'])]
        block = tuple(entry['blocks'][0][3:5])  # a real block of a shared name
        if block[1] - block[0] + 1 < 2 * len(sub):
            block = (block[0], block[0] + 2 * len(sub) + 9)
        got, dd = e.issue_numbers(sub, box, block=block)
        lo, main_hi, hi = e.number_range(None, block)
        self.assertEqual(dd, len(str(block[0])))
        self.assertTrue(all(lo <= n <= main_hi for n in got.values()))
        p = e.provisional_number((v['newHome']['lon'], v['newHome']['lat']), got, sub, box, dd, block)
        self.assertTrue(block[0] <= p <= block[1])
        self.assertNotIn(p, got.values())
        with self.assertRaises(ValueError):
            e.issue_numbers(sub, box, block=(block[0], block[0] + 2 * len(sub) - 2))

    def test_capacity_rule(self):
        self.assertEqual(e.digits_for(450), 3)
        self.assertEqual(e.digits_for(451), 4)
        self.assertEqual(e.digits_for(45000), 5)
        with self.assertRaises(ValueError):
            e.digits_for(45001)



class AddMyHome(unittest.TestCase):
    # a 15 m x 20 m plot in Ouagadougou (real location near the city-centre sample), gate on the south wall
    lat, lon = 12.37000, -1.52700
    dlat, dlon = 20 / e.M_PER_DEG_LAT, 15 / (e.M_PER_DEG_LON_EQ * math.cos(math.radians(12.37)))
    plot = [(lon, lat), (lon + dlon, lat), (lon + dlon, lat + dlat), (lon, lat + dlat)]
    gate = (lon + dlon / 2, lat)

    def test_good(self):
        self.assertEqual(e.add_my_home_checks(self.gate, 6, self.plot, self.plot), [])

    def test_problems(self):
        far_gate = (self.lon + self.dlon / 2, self.lat + self.dlat / 2)
        self.assertTrue(any('gate' in p for p in e.add_my_home_checks(far_gate, 6, self.plot)))
        self.assertTrue(any('GPS' in p for p in e.add_my_home_checks(self.gate, 30, self.plot)))
        bow = [self.plot[0], self.plot[2], self.plot[1], self.plot[3]]
        self.assertTrue(any('crosses' in p for p in e.add_my_home_checks(self.gate, 6, bow)))
        self.assertTrue(any('overlaps' in p for p in e.add_my_home_checks(self.gate, 6, self.plot, existing=[self.plot])))



class OfficialFirst(unittest.TestCase):
    def test_official_wins(self):
        c = {'official': {'street': 'Rue 15.123', 'door': '45', 'commune': 'Ouagadougou'}, 'area': '15', 'kind': 'S', 'number': None}
        self.assertEqual(e.display_address(c), 'Rue 15.123, porte 45, Ouagadougou')

    def test_nways_elsewhere(self):
        self.assertEqual(e.display_address({'official': None, 'area': 'Bissiga', 'kind': 'V', 'number': '4117'}), 'Bissiga 41 17')
        with self.assertRaises(ValueError):   # secteur codes are not issued
            e.display_address({'official': None, 'area': '15', 'kind': 'S', 'town': 'Ouaga', 'number': '48217'})


class Border(unittest.TestCase):
    """SPEC 1b: the national border decides, with the simplification margin of the shipped outline."""

    def test_square(self):
        sq = b.Border([[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1)]])
        self.assertTrue(sq.contains(0.05, 0.05))
        self.assertEqual(sq.outside_m(0.05, 0.05), 0.0)
        self.assertAlmostEqual(sq.outside_m(0.05, 0.1 + 300 / 111320.0), 300.0, places=3)
        self.assertFalse(sq.beyond(0.05, 0.1 + 299 / 111320.0))
        self.assertTrue(sq.beyond(0.05, 0.1 + 301 / 111320.0))
        margin = b.Border([[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1)]], 50)
        self.assertFalse(margin.abroad(0.05, 0.1 + 249 / 111320.0))
        self.assertTrue(margin.abroad(0.05, 0.1 + 251 / 111320.0))

    def test_burkina_faso(self):
        self.assertFalse(b.abroad(12.3714, -1.5197))          # Ouagadougou
        self.assertFalse(b.abroad(13.458676, 1.044509))       # 150 m outside: within 300 m
        self.assertTrue(b.abroad(13.460253, 1.044921))        # 330 m outside, though in a commune outline
        self.assertIsNotNone(e.commune_at(13.460253, 1.044921))
        self.assertTrue(b.abroad(13.401026, 1.204613))        # a neighbouring country, though it has a spot code
        self.assertIsNone(e.commune_at(13.401026, 1.204613))
        self.assertIsNotNone(e.spot_commune(13.401026, 1.204613))


if __name__ == '__main__':
    unittest.main(verbosity=1)
