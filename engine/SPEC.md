# N-Ways address engine for Burkina Faso — specification

Issued on 20 October 2026: one code for every compound in Burkina Faso, frozen in `engine/data/register.json` and published in `registry/`.
Reference implementation: [`reference/bf_engine.py`](reference/bf_engine.py) (Python standard library only). Tests: [`reference/test_bf.py`](reference/test_bf.py) with [`reference/test_vectors.json`](reference/test_vectors.json); conformance vectors from the frozen register: [`reference/vectors.json`](reference/vectors.json) (`tools/vectors.py`).

This engine is Burkina Faso's. "MUST", "SHOULD", "MAY" as in RFC 2119.

## 1. Objects

| Object | What it is | Identifier |
|---|---|---|
| Commune | one of the 351 communes (HDX COD-AB, 2025-08-01) | La Poste postcode, 5 digits (Komsilga, which La Poste does not list, uses 10990, a number La Poste does not use, until La Poste gives it one) |
| Code area | a named place of a commune: village, hamlet, locality or, in towns, a quarter (OpenStreetMap and GeoNames names, `tools/build-areas.py`); a home takes the nearest one of its commune | `V001`–`V999` (`S` is kept for secteur codes, not issued: no secteur map is public) |
| Plate name | the short name of a code area used in the code (≤ 12 characters, ≤ 2 words, §2.5); the official name is kept beside it | area |
| Name range | the national number range of one normalised village plate name, cut into one frozen block per village (§2.4) | name key + frozen name id (5 digits) |
| Town word | the plate name of a commune ("Ouaga", "Bobo", "Fada"...), kept for the secteur codes that may be added later as aliases | La Poste postcode |
| Compound | concession / cour / plot, walled or not, with a primary gate | area + number |
| Structure | one footprint inside a compound | compound + `.n` |
| Entrance | a gate or door of a compound; `/1` is the primary gate | compound + `/n` |
| Spot | any point, 10 m cell of the commune frame | postcode + `E…` `N…` |

## 1b. The border decides

A Burkina Faso code is only ever issued for a building whose entrance lies inside the national border, OpenStreetMap's `boundary=administrative`, `admin_level=2` relation of Burkina Faso (192783), or within **300 m** of it (the line's own accuracy, and gates on the line). Commune outlines and spot frames reach over the border; they never decide. A building more than 300 m outside it is in a neighbouring country and gets no code, whatever outline or frame holds it.

- **Build.** The pipeline uses the full boundary: footprints are kept only when their centre lies inside it, and a compound whose point lies more than 300 m outside it is dropped (`tools/README.md`, "The border decides").
- **Issue.** The server and decoders use `engine/data/border.json`, the boundary simplified so that every point of either outline lies within `toleranceM` = 3 m of the other (measured by `tools/country-border.py`: 2.0 m both ways; 25,507 of the 30,240 vertices kept, 542 kB). A point is refused when it lies more than 300 − 3 = 297 m outside the simplified outline (`bf_border.abroad`). So nothing more than 300 m outside the true border is ever accepted, and nothing inside it or within 294 m of it is ever refused.
- **Registry.** Of the 8,369,987 published codes, 3,985 have their entrance outside the full border: 3,975 within 300 m of it, and 10 between 300.0 and 300.5 m. The 61 published entrances more than 297 m outside the full border lie beyond what the shipped outline accepts: they are found by their code and at their entrance, but no new code and no entrance move is accepted there.

## 2. Forms

### 2.1 Machine form

```
BF-<postcode>-<kind><place>-<number>-<check>
postcode : 5 digits, La Poste Burkina Faso commune code (model/units/communes.csv)
kind     : S (secteur, 2-digit place) | V (village, 3-digit place)
number   : 3, 4 or 5 digits, first digit 1-9; length fixed per secteur, and per name for villages
check    : Damm check digit, kindDigit S=1, V=2, over
             secteur:  postcode + kindDigit + place + number
             village:  nameId(5 digits) + postcode + kindDigit + place + number
regex    : ^BF-(\d{5})-([SV])(\d{2,3})-([1-9]\d{2,4})-(\d)$
```

Examples: `BF-50650-V022-3530-1` (Nabadogo, Ziga), `BF-40650-V004-14980-3` (Bissiga, Sabou), `BF-57450-V003-16870-9` (Bissiga, La-Toden), `BF-30200-V036-100-8` (Yamako, Bere). The secteur kind `S` (for example `BF-10000-S15-48217-6`) is reserved and not issued (§2.2).

Parsers MUST accept the form without the check digit (then report it unchecked), MUST reject S with 3 digits or V with 2, MUST treat a wrong check digit as invalid, and MUST treat a village code whose number lies in none of that village's blocks (§2.4) as invalid.

### 2.2 Remembered form

- Towns: their homes carry the code of their quarter or of the village the town grew over, like everywhere else. Secteur codes (`Secteur 15 Ouaga · 48 217`) are not issued: the secteur maps are not public; once a commune shares its map, each home's secteur code is added as an alias and its number never changes.
- Village: `<plate name> <number grouped>`, e.g. `Nabadogo 35 30`, `Bissiga 14 980` (Sabou), `Bissiga 16 870` (La-Toden), `Yamako 100` (official name Soussougou Yamako, §2.5).
- Implementations MUST NOT produce a remembered form whose plate name or town word breaks the plate limit (§2.5); reference: `remembered` raises.
- Grouping: 4 digits `AB CD`; 5 digits `AB CDE`; 3 digits `ABC`.
- No letters. No check digit is ever shown to people or asked of them: a check digit people must copy is one more thing to get wrong, and the plate name and the block test already catch most slips. A decoder accepts one after a hyphen from systems that send it (`Bissiga 16 870-9`) and verifies it.

Resolving a remembered form uses **no context**: not the user's position, not the commune of the phone, not a town said after a comma. Implementations MUST NOT complete a code from context.

- A secteur form is refused with a message: secteur codes are not issued yet.
- `<name> <number>` → name key (§2.4) → the plate name's range, or, if the key is an alias (an official name, §2.5), the plate name it maps to; a number of the wrong length MUST be refused → the block that holds the number → (postcode, village index) → machine form. A number in no block (spare or free space) MUST be refused as not issued.

One remembered form maps to exactly one machine form in the whole country. The app SHOULD show the village (or secteur) and the commune it found before guiding there. Reference: `resolve_remembered`.

### 2.3 Spoken form

French, groups from the left as phone numbers are read: 48 217 → "quarante-huit deux cent dix-sept"; 41 17 → "quarante-et-un dix-sept"; 70 → "soixante-dix", 80 → "quatre-vingts", 91 → "quatre-vingt-onze" (no septante/nonante). The app's voice MAY say the number in Mooré, Dioula or Fulfulde; those voice tables are to be written with native speakers.

### 2.4 National name ranges and town words

Village names repeat across Burkina Faso, so a remembered code must be unique in the whole country on its own, with no commune or position to tell two places apart.

**Name key** (`name_key`): NFKD, combining marks removed, upper case; `ST`/`ST.` and `STE` as whole words expanded to `SAINT`/`SAINTE`; leading `Q`, `QUARTIER`, `HAMEAU`, `VILLAGE DE`, `VILLAGE` followed by a space, hyphen or dot removed; leading `LES `, `LE `, `LA `, `L'` removed; every character outside A–Z, 0–9 removed; then, in this order, `TCH→C`, `DJ→J`, `GH→G`, `PH→F`, `OU→U`, `W→U`, `GU→G` before I or E; runs of one letter collapsed to one (digits are never collapsed: `Ouaga 2000` → `UAGA2000`, not `UAGA20`). Vectors: `nameKeys` in `test_vectors.json` (Douré = Doure → `DURE`; Ouatinoma = Watinoma = Wattinooma → `UATINOMA`; Tanguin = Tanghin = Tangin → `TANGIN`).

**Generic labels** (`is_generic`: names starting with *village*, *campement*, *camp*, *site*, *ferme*, *chantier*, *zone*, or exactly *hameau*) are not names and MUST NOT receive a block; they are renamed with the commune before issue.

**Blocks.** For every plate-name key (§2.5), the villages of the register carrying it (at first issue, ordered by postcode then index) each get a block of `max(20, ceil(2 × compounds / 10) × 10)` numbers, laid end to end from `10^(d−1)`. `d` is the smallest of 3, 4, 5 with `Σ blocks ≤ floor(0.9 × 9 × 10^(d−1))` (`NAME_SPARE = 0.1`: the top tenth is always spare). All villages of one name have `d` digits. Villages with no compound yet get no block until their first compound. The name id is the 1-based rank of the key in the sorted list at first issue, then append-only. Published in `model/areas/name-ranges.json` (`names[key] = {id, plateName, officialNames, aliases, digits, range, spareFrom, blocks: [[postcode, index, compounds, lo, hi]...], areasWithoutCompounds, needsCouncilChoice?}`, `aliasKeys[officialKey] = plateKey`, `droppedAliases`); built by `tools/name-ranges.py`.

**Too large.** A village whose own block exceeds `0.9 × 90,000` MUST be split by named quartiers before issue; with the GeoNames quarters added none does. If the blocks of one name together exceed 5 digits, the name keeps its bare form for the blocks that fit in register order and every other village takes the qualified name `<name>-<commune>`, a key of its own; the decision is made once and listed (`qualified` in `model/stats/name-stats.json`; empty at issue). Quartier areas created by a split and named with a common quarter word (Natenga, Nayiri, Tanghin, Zongo) take the village as qualifier (`Boassa-Zongo`); a qualified name follows the plate limit (§2.5) like any other: where village + quarter word is too long, the commune chooses.

**Frozen.** Blocks are frozen at issue and never renumbered. A new village with an existing name, or a full block, takes the next block from `spareFrom` upward (`spare_block`); when the range is used up, the new village takes the commune qualifier. A renamed village keeps its block; the new name becomes an alias of the old key.

**Town words** (`model/areas/town-words.json`: `{word, official, aliases, plateRule, source?, needsCouncilChoice?, plateCandidates?, plateReason?}`): the commune name under the plate rule (§2.5); documented short forms `Ouaga` (10000), `Bobo` (90000), `Fada` (75000) with their sources and the full names as aliases; the three names carried by two communes each take the province (Boussouma-Boulgou / Boussouma-Sanmatenga, Namissiguima-Sanmatenga / Namissiguima-Yatenga, Thiou-Boulkiemdé / Thiou-Yatenga), are over the limit and are flagged; the bare name is no alias. A town-word candidate MUST NOT equal another commune, a province or a region. Town-word keys (normalised as above) MUST be unique; an alias claimed by two towns is dropped.

**Counts (design register of OpenStreetMap villages, plate names)**: 7,854 named villages, 6,862 plate names, 707 names repeated over 1,695 villages (official names: 6,954, 646 over 1,542); largest shared range Barogo (2 villages, 17,505 compounds, 35,010 numbers, 5 digits); villages by digits 3,386 / 4,137 / 265 (3 / 4 / 5; official names: 3,442 / 4,114 / 232); no name needs a qualifier; 4 villages split before issue. `model/stats/name-stats.json`.

### 2.5 Plate names

A code is only remembered if its name is short enough to say and paint; the rule below bounds every plate name.

Every code area has an **official name** (shown in small print, never required) and a **plate name** (in the code). A plate name MUST have at most 12 characters (NFC; every letter, space, hyphen and apostrophe counts one) and at most 2 words (parts between spaces or hyphens, not counting the linking words `de du des d la le les l et sur en au aux à` and Tamasheq `n`), and no digit. Reference: `plate_names.fits`, `bf_engine.plate_ok`.

Derivation (`plate_names.derive`, `lang='fr'`, Burkina lists in `tools/name-ranges.py`): documented short form with a source; else clean (brackets, after a slash, second spelling, generic words `Q`, `Quartier`, `Lieu-dit`, `Village de`, `Cité`, `Lotissement`, `Zone`, `Secteur`, `Hameau`, `Campement`); if it fits, done; else `Saint`/`Sainte` → `St`/`Ste`; else the most distinctive run of whole words that fits (rarity among all official names, preference for the last word), never a word cut, never only weak words. Burkina weak words (never a plate name alone; a short form that drops one is not automatic): ethnic and status qualifiers (Peulh, Foulbé, Mossi, Silmi, Silmimossi, Rimaïbé, Yarcé, Gourmantché, Bella, Traditionnel, Nouveau, Site, Village), Mooré `Yiri`, `Tenga`, `Naba`, Fulfuldé `Ouro`/`Wouro`, mine and station words. The area is flagged `needsCouncilChoice` (≤ 3 `plateCandidates`, `plateReason`, first candidate provisional) when: no clear best candidate; the short form drops a qualifier or a number; it equals a commune, province, region or big city of the region (the area's own commune excepted), or the area's own commune, or another place of the same commune; or a hyphenated name is too long (its parts are the candidates). With no fitting candidate the cleaned name is kept provisionally and issued; the commune chooses a shorter one. **The commune's name instead** (provisionally, as the commune's own places spell it): when the short form would hold a digit (`VK7`, `b42`), would be a bare generic word (`Secteur 4` → `Secteur`, `1200 Logements` → `Logements`, `Quartier`), would be a derived form of under 3 letters, or would be a big city's short form elsewhere (`Ouaga 2000` → `Ouaga`, Ouagadougou's own short form); after first issue, areas may be renamed only through `model/areas/renames.json` and `tools/rename-areas.py` (new name ids appended, the other names untouched, the old numbers retired): on 21 October 2026 `Ouaga 2000` became **Ouaga** (sharing the name key `UAGA` with the village Waaga, four digits) and `1200 Logements` **Logements**. `tools/build-register.py --freeze` is for first issue only and must not be run again. Documented short forms of areas: `Bobo-Dioulasso` → **Bobo**, `Fada N'Gourma` → **Fada** (SOURCES.md, "Short place names"). Codes are issued under the provisional name, so that no home waits for a naming decision; the commune may choose once, and the old name stays an alias.

Register fields (`model/areas/register.json`, each village): `officialName`, `plateName`, `plateRule` (`as-is`, `cleaned`, `abbreviated`, `known`, `distinctive`, `council`), and for flagged areas `needsCouncilChoice`, `plateCandidates`, `plateReason`.

Aliases: an official name whose key differs from its plate name's key decodes to that plate name when it maps to one plate name only; an alias claimed by two plate names, or equal to another plate name, is dropped and listed (`droppedAliases`). Vectors: `plates`, `plateDecode` (a long official name to its plate name; Debere Boulga and Boulga, equal only after shortening, decoding to different villages), `plateRejected`.

Counts at first issue (20 October 2026; `model/stats/name-stats.json` has the exact figures): 949 areas, holding 397,354 compounds, carried a provisional plate name; after the renames of 21 October 2026, 945 areas and 387,212 compounds. Counts on the design register of OpenStreetMap villages: 474 official names over 12 characters, 58 over 2 words; plate = official 7,277; cleaned 19, abbreviated 1, distinctive 144; flagged 413, of which 189 still over the limit (78 with digits); 377 aliases, 1 dropped. Town words: 329 as-is, 3 known, 18 flagged (13 still over the limit).

## 3. Check digit: Damm

The Damm table (order-10 weakly totally anti-symmetric quasigroup) is in `bf_engine.DAMM`. `check = fold(DAMM, 0, digits)`; a code is valid when `fold(DAMM, 0, digits + check) == 0`. For a village the digits start with the frozen 5-digit name id (§2.1), so the check binds name, area and number: the same index and number under another name give another check digit, and a number moved to another same-named village fails both the check and the block test. It detects every single-digit error and every transposition of two adjacent different digits (both are tested exhaustively on a sample code). Vector: `572` → `4`.

Why Damm and not a letter check: everything in the machine form is digits except S/V, so a decimal check keeps the code typeable on any keypad.

## 4. Communes and frames

- Commune lookup: point-in-polygon (even–odd rule) over `model/units/communes.geojson` (simplified to about 40 m; production uses the full-resolution HDX/IGB boundaries, and near a boundary the registry decides, not the polygon).
- Commune → postcode: `model/units/communes.csv`. Spelling matches marked `(verify)` are to be confirmed with La Poste; Komsilga, which La Poste does not list, uses 10990 (no La Poste code) in machine forms until La Poste gives it one.
- Frame (one per coded commune, frozen in `model/units/frames.json`):
  - `lon0 = floor(minLon × 100) / 100`, `lat0 = floor(minLat × 100) / 100`
  - `latc = round((minLat + maxLat) / 2, 2)`
  - `kx = 111320 × cos(latc)` m per degree of longitude; `ky = 110574` m per degree of latitude
  - digits per axis = 4 if the frame spans less than 99,990 m on that axis, else 5. Today: 346 communes 4+4; Tin-Akoff 5+4; Matiakoali, Pama, Ouo 4+5.

Frames are a definition, not a measurement: encode and decode are exact inverses on the same frame, so the small scale distortion of a local equirectangular frame (under 0.2% across a commune) never moves a code.

## 5. Spot codes

```
encode(lat, lon): E = floor((lon − lon0) × kx / 10), N = floor((lat − lat0) × ky / 10)
                  → "BF-<postcode> E<E padded> N<N padded>"
decode:           lon = lon0 + (E + 0.5) × 10 / kx, lat = lat0 + (N + 0.5) × 10 / ky   (cell centre)
```

A point in a commune outline is coded in that commune's frame. The spot code is computed offline from `frames.json` and the commune polygons (a few MB).

### 5.1 Points in no commune outline

The published commune outlines are simplified and do not tile the country exactly: an entrance can fall in a gap between two outlines or just over a border line. 9,235 issued compounds (0.11 %, in 110 communes) lie in no outline. Such a point is coded in the frame of one commune, chosen as follows (reference: `spot_commune`, `nearest_spot_commune`):

1. **Distance to an outline** (`edge_d2`): the squared distance from the point to the nearest edge of any ring of the commune's outline, in degrees of latitude, with longitude differences multiplied by `cos_lat(lat)` of the point. `cos_lat` is a fixed Taylor polynomial (`r = lat × 0.017453292519943295`, terms to `r^12`, coefficients in `bf_engine._COS_TERMS`, evaluated by Horner's rule, each product rounded), so every port computes the same double whatever its math library.
2. **Candidates**: the communes whose outline lies within **10 km** (`SPOT_OUTLINE_M`, distance² ≤ (10,000 / 110,574)²) and whose frame the point lies at most **300 cells (3,000 m)** beyond on each axis (`SPOT_NEAR_CELLS`; a cell index below 0 or above `10^digits − 1` is beyond by that many cells).
3. **Choice**: candidates whose frame holds the point come first; among them, the nearest outline; ties to the lower postcode. If no frame holds the point, the candidate with the nearest outline (ties to the lower postcode), and the point takes that frame's nearest edge cell: `E` and `N` clamped to `0 … 10^digits − 1`.
4. **Refused**: a point with no candidate.

A point is in Burkina Faso when it lies inside the national border or within 300 m of it (§1b), and lies in a commune outline or has a spot code by this rule: a compound in a gap between outlines is found by its location, can be issued a code and can have its entrance moved there (§6.6). A refused point is outside, and so is a point more than 300 m outside the national border: a spot code is a grid reference, and a point beyond the border may have one, but that never makes it Burkina Faso's for a code.

Measured on the issued registry: every compound in no outline lies within 8,566 m of an outline, and the farthest one coded at an edge cell lies 14 cells (140 m) beyond its frame; both limits leave a margin. Of the 9,235, 9,227 are coded in a frame that holds them (decoding error ≤ 7.07 m as above) and 8 at an edge cell; the registry keeps the exact entrance beside the spot code. The commune a spot code names is a frame, not an address: it can differ from the compound code's commune.

Frames never move, and codes of points in an outline are unchanged by this rule. Decoding uses the frame of the commune the code names, so an edge-cell code decodes to the centre of that edge cell. Vectors: `spotOutside` in `test_vectors.json` (a gap between the Ouagadougou and Komsilga outlines, a compound 8.6 km over its commune's outline, an edge cell, refused points) and `spotsOutside` in `vectors.json` (621 points: 411 issued entrances and 150 other points with a spot code, 28 of them at an edge cell, and 60 refused points).

Example: Ouagadougou, a public building at 12.3721856 N, −1.5236057 → `BF-10000 E1809 N1351`; decodes to 12.3722258, −1.5235809 (cell centre, 5 m away).

## 6. Official addresses first, then the registry build

### 6.0 Official addresses

Where a commune has already given an address, that address is the one people and services use; the N-Ways code adds a gate position and a code that works everywhere, and never competes with it. The registry build MUST start by importing the communes' official door addresses:

- **Source**: the communal address databases of Ouagadougou and Bobo-Dioulasso (AMB/EU PASIU platforms "Easy Geo", "Webmapping grand Ouaga data"), under a data-sharing agreement; not open today. Fields kept: street code (`Rue 15.123`), street name if any, door number, arrondissement, secteur, point or door position, source and version date.
- **Display**: exactly as officially written ("Rue 15.123, porte 45, Ouagadougou"); spelling and numbers are never altered.
- **Display**: in Ouagadougou and Bobo-Dioulasso the official street within 30 m of the compound comes first on every card (OpenStreetMap names and street codes, `Rue 15.123, Ouagadougou`, `coverage = official-street`); a door number from the communes' databases, once shared or confirmed by residents, replaces it. Every compound keeps its N-Ways code beside the official address, so that one form of address works in every commune.
- **Sync**: re-import each communal release; diff by official identifier; official changes always win; N-Ways reports suspected errors to the commune and never edits official records.
- **Later readdressing**: if a commune readdresses an area, each compound shows the official address first; its N-Ways code is unchanged.

The reference function `display_address(compound)` returns the official address when present, else the N-Ways remembered form.

Run per commune, offline, from the N-Ways building map; output is the published registry. Steps in this order:

### 6.1 Inputs

Structures: OpenStreetMap buildings (ODbL) and Google Open Buildings / Microsoft footprints (CC BY 4.0 / ODbL) with ML height `h`; OSM walls, fences, hedges (closed ways), gates (`barrier=gate|lift_gate|swing_gate|sliding_gate`), entrances; N-Ways gated compounds and gates (`data/valhalla/compounds.geojsonseq`, `gates.geojsonseq`); N-Ways places; DGI parcels where shared; people's confirmations (§9).

### 6.2 Group structures into compounds (before any numbering)

Union–find over structures, rules in this order (Burkina parameters):

1. **enclosure** (confidence 0.85): structures whose centroid lies in the same smallest closed barrier polygon of ≤ 6,000 m². Larger enclosures with many compounds become **estates** (outer level, own gate), and their inside is grouped by rules 2–4.
2. **annex** (0.60): a structure < 25 m² not in an enclosure joins the nearest structure ≥ 25 m² whose footprint gap is ≤ 8 m.
3. **hut cluster** (0.50; not in Ouagadougou and Bobo-Dioulasso): huts < 40 m² that belong to no house (not an annex, not in an enclosure) with gaps ≤ 3 m chain together, at most 25 per compound: a cluster never joins two houses.
   Production: `bf_engine.group_footprints` (the same rules on a 40 m grid, footprints in stable-id order, true outline gaps).
4. **single** (0.40).
5. **people** (0.9 and above): confirmed groupings and gates override 1–4 before issue; after issue they can merge or split only under §7.

Gaps are true outline distances in local metres (0 when outlines touch or overlap).

### 6.3 Primary gate

Mapped gate on the enclosure ring if any; else the N-Ways gate nearest to the compound on its access road; else an **inferred gate**: the point of the compound's hull nearest to the nearest drivable or walkable way, flagged `inferred` until someone confirms it. The gate is the navigation target.

### 6.4 Code areas

Each footprint is assigned to the nearest named place of its commune (`model/areas/register.json`, local metres, ties to the lower index; `tools/assign-areas.py`); a compound's area is its footprints' area, and its ordering point the centre of its largest structure. Area indices are alphabetical at first issue, then append-only. The area's frame is the box of its footprints' centres at first issue widened by 0.0005° on every side, frozen.

### 6.5 Numbers

```
secteur: d = smallest of 3, 4, 5 with N × 2 ≤ 9 × 10^(d−1)   (N = compounds in the area)
         range = [10^(d−1), 10^d − 1]
village: range = the village's block [lo, hi] in its name's national range (§2.4); d = digits of the name
main     = first two thirds of the range; tail reserve = last third
order    = compounds sorted by Hilbert index (order 16) of their ordering point in the area's box, ties by id
step     = max(1, floor(|main| / floor(N × 1.5)))
number_i = 10^(d−1) + i × step
```

Neighbours on the ground get close numbers; between two neighbours `step − 1` numbers stay free for infill.

### 6.6 New compound (provisional number)

The issuer's rule, which `server/` reproduces number for number (`server/engine.py`, tests in `server/tests/`):

1. The area is that of the nearest live code within 250 m of the new compound (a new house joins its neighbours); else the code area of the point (§6.4); else the numbered area whose place point is nearest. Another door of an existing code takes that code's area, and must be within 80 m of it.
2. Every number the area holds, retired ones included, is ordered by the Hilbert index of its point (ties by key). `low` is the number of the last compound at or before the new point's index (else `lo − 1`), `high` the number of the first after it (else the first number of the tail reserve).
3. Between them, below the tail reserve, the free number nearest `floor((low + high) / 2)` is taken, searching `mid − d` before `mid + d` for `d = 0, 1, 2, …`.
4. Else the lowest free number of the tail reserve; else the lowest free number of the area's later blocks.
5. Else the area takes an extension block from its name's spare (§2.4): from `spareFrom`, above every block of the name, of `block_size(N + 1)` numbers, where `N` is the count of numbers the area holds; the block is stored with the area and published in `registry/areas.csv.gz`. An area with no block at all takes `block_size(1)` the same way. When the name's range is used up, the code is refused until the commune chooses a qualifier.

A point outside Burkina Faso (more than 300 m outside the national border, §1b; or no commune outline holds it and it has no spot code, §5.1) gets no code, and no entrance is moved there. A new compound gets no code when a live code lies within 3 m, or when its outline (6 m² to 2 ha) covers a live code: the building already has one. Provisional numbers are visible at once and become confirmed under §9.

## 7. Stability

- A number is never reused or moved.
- Demolished: retired (kept in the registry with status `demolished`).
- Split: the part with the larger floor area keeps the code; others get provisional numbers.
- Merge: the oldest code survives; the other becomes an alias that still resolves.
- Rename or renumbering of a secteur or village: update the alias table only; a village keeps its block in its old name's range.
- Name blocks are frozen at issue; new same-named villages and extensions come from the name's spare, never by renumbering (§2.4).
- Grouping corrections after issue follow split/merge; regrouping never re-issues codes.

## 8. Profiles

### 8.1 Structure

`id, compound, footprint, footprintM2, perimeterM, heightM, floors, floorAreaM2, class, subclass, classConfidence, name (business/public only), status, entrances[], sources{attribute: {source, date}}, lastConfirmed`.

Class inference (first strongest evidence, +0.05 per agreeing source; residential + commercial evidence → `mixed` 0.6):

| Evidence | Confidence |
|---|---|
| OSM `building=*` (house, school, mosque, warehouse...) | 0.85 |
| OSM amenity/shop/office/tourism/healthcare on the building | 0.75 |
| N-Ways place inside the footprint | 0.65 |
| OSM landuse containing the centroid | 0.50 |
| size: < 6 m² annex; > 2,500 m² industrial | 0.40 / 0.30 |
| default residential | 0.45 (0.55 in residential landuse) |

Floors: OSM `building:levels`; else OSM `height` / 3 (rounded, at least 1); else unknown. The Google/Microsoft `h` is a rendering filler (36 values over 3.5–7 m) and never gives floors. Floor area = footprint × floors. Taxonomy: see `model/design.json` → `building.taxonomy` (cour, yiri/zaka, case ronde, cour commune, célibatorium, villa, immeuble, habitat spontané, grenier...).

### 8.2 Compound

`code, area, number, gates[], entrances[], plotAreaM2, plotSource (enclosure|outline|parcel|hull), structures[], structureCount, floorAreaM2, class, classConfidence, crossRefs{laposteZone, agency, street, doorNumber, section, ilot, parcelle, titre}, status, provisional, firstIssued, lastConfirmed, aliases[]`.

Compound class: `institutional` if any education/health/religious/government structure; `mixed` if residential and commercial; `commercial`; `industrial`; `residential-multi-storey` if a dwelling has ≥ 3 floors; `residential-multi-household` if ≥ 2 dwellings ≥ 25 m² or a row building (aspect ratio ≥ 3, ≥ 40 m²: célibatorium); `residential-one-household`; else `unclassified`.

## 9. Confirmation (people and partners)

Signals, each with a weight; a grouping, gate or provisional code is **confirmed** when the weights pass the threshold and nothing contradicts it, without anyone queuing it for review:

- arrivals: N-Ways drivers and walkers ending trips at the gate; couriers marking "delivered at gate";
- residents: "these buildings are one home", "this is the gate", a resident confirming twice on different days;
- businesses claiming their shop (name, entrance);
- new imagery or footprints showing the structures;
- partners (La Poste zone, DGI parcel, commune street address) adding cross-references.

A contradiction (two claims on one plot, a neighbour's dispute) holds the item as `disputed`: still navigable, not published as confirmed.

## 10. Add my home

Inputs: gate point (GPS averaged ≥ 5 s; the reference rejects a fix with reported accuracy worse than 15 m), one gate photo, an outline (imagery taps, AR walk, or plan import), a description (households count, structures, floors, use). Checks before a provisional code: outline is a closed simple polygon; area between 20 m² and 20,000 m²; gate within 5 m of the outline; AR and GPS outlines agree within 8 m (centroid) and 20% (area); no overlap above 10% with an issued compound or a known parcel (else flagged, not issued). Plan imports: beacon coordinates with declared datum (WGS84, UTM 30N or 31N until IGB confirms the national datum). Output: provisional code (§6.6), shown with "Une adresse N-Ways n'est pas un titre foncier." Offline: spot code at once; the compound code is fetched at the next connection (the area registry is not stored on phones in full).

## 11. Data files

| File | Content | Size |
|---|---|---|
| `model/units/communes.geojson` | 351 commune polygons (HDX 2025, simplified) | 2.0 MB |
| `model/units/communes.csv` | commune ↔ La Poste postcode, building counts | 29 kB |
| `model/units/laposte-postcodes.json` | La Poste table (582 codes) | 116 kB |
| `model/units/frames.json` | frozen spot frames, one per coded commune | 47 kB |
| `engine/data/border.json` | the national border (OpenStreetMap `admin_level=2`), simplified to within 3 m (§1b) | 542 kB |
| `model/areas/register.json` | village/hamlet register per commune (OpenStreetMap and GeoNames places): official and plate names | 1.3 MB |
| `model/areas/name-ranges.json` | national name ranges: name id, plate and official names, aliases, digits, frozen blocks per village | 1.4 MB |
| `model/areas/town-words.json` | town word of each commune (secteur codes), plate rule and council fields | 35 kB |
| `engine/reference/plate_names.py` | the plate-name rule (limit check and derivation) | 17 kB |
| `model/stats/area-compounds.csv` | estimated compounds per village and town node (input of the name ranges) | 0.5 MB |
| `registry/areas.csv.gz` | the frozen area table: plate and official names, name ids, digits, blocks, compounds at issue, place points, frames | 0.9 MB |
| `registry/<postcode>.csv.gz` | every code of one commune: machine, home and written forms, number, check, status, entrance, spot code, official address, building profile | per commune |
| `registry/MANIFEST.json` | counts per commune and the SHA-256 of every file uncompressed | 20 kB |

Offline on a phone: frames + simplified communes + name ranges + town words + the registry of the user's own commune(s). Name ranges are enough to resolve any remembered code in the country to its village offline.

## 12. Privacy rules in the engine

Published registry rows carry no person data: a code, its area, its entrance point, its spot code, the official address where one exists and a building profile (use, kind, structures, floor area). The registry publishes every issued code. It never carries outlines drawn by residents, gate photos, the people who confirmed a code, or sites for displaced people. The column `alert_zone` of `areas.csv` marks the communes covered by the UK FCDO's advice against all travel (every commune since 10 December 2025), as context for services that plan visits; it does not change what is published.

## 13. Conformance

An implementation conforms when it reproduces every vector in `reference/test_vectors.json` (Damm, machine, remembered, plate names and their decoding, refused over-long plate names, national names: same-named villages decoding to different places and rejected forms, name keys, spoken French, spot encode/decode, points in no commune outline, registry samples and the provisional number).
