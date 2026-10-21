# Tools: Burkina Faso's registry

All inputs are read-only: the N-Ways data folder (`NWAYS_ROOT`), the N-Ways database (`NWAYS_DB`, tables `regions` and `places`) and the GeoNames dump `BF.txt` (https://download.geonames.org/export/dump/, CC BY 4.0). Run one heavy step at a time: DuckDB runs with `memory_limit='3GB'` and spills to the work folder; the grouping and the numbering read the footprints one code area at a time.

| Step | Script | Writes |
|---|---|---|
| 1 | osmium exports (below) | `admin`, `bar`, `place`, `hw` `.geojsonseq` in the work folder |
| 2 | `prepare-inputs.py <work>` | `units.geojson` (the 351 communes, HDX 2025), `streets.csv` (the named streets of Ouagadougou and Bobo-Dioulasso, with the communes' street codes), `enclosures.geojson`, `estates.geojson`, `gates.csv`, `places.csv`, `country.geojson` (the national border: OpenStreetMap relation 192783, `admin_level=2`, read from `data/osm/westafrica-admin.osm.pbf` because the country extract does not carry it) |
| 2a | `country-border.py <work>` | `engine/data/border.json`: the national border of `country.geojson` simplified to 2 m, with a 3 m tolerance (both directions checked), for the server and decoders |
| 3 | `build-areas.py <work> <BF.txt>` | `model/areas/register.json`: the 17,518 code areas, from OpenStreetMap places and GeoNames populated places |
| 4 | `extract-buildings.py <work>` | `buildings-raw.csv` (every footprint inside Burkina Faso with its enclosure, estate, commune and nearest official street within 30 m), `buildings-pts.csv`, `enclosure-gates.csv` |
| 5 | `assign-areas.py <work>` | `area-of.csv` (each footprint's code area: the nearest named place of its commune), `area-boxes.json` (each area's frame) |
| 6 | `sort-buildings.py <work>` | `buildings.csv`, sorted by area |
| 7 | `issue_registry.py group <work>` | `compounds.jsonl.gz` (compounds and profiles; city rules in Ouagadougou and Bobo-Dioulasso, huts clustered elsewhere), `area-counts.json`, `group-stats.json` |
| 8 | `build-register.py <work> --freeze` | `area-compounds.py` and `name-ranges.py` on the real compounds: plate names, national ranges and blocks; `model/areas/name-ranges.json`, `engine/data/register.json`, `engine/data/units.json`, `model/stats/register.json` |
| 9 | `issue_registry.py number <work> <work>/lotes.jsonl.gz` | the lotes, area by area, with the reference's numbers and the official street |
| 10 | the N-Ways backend: `homecodes issue -country BF -lotes <work>/lotes.jsonl.gz`, then `homecodes export -country BF -out <dir>` | the codes, after checking every number against the reference's; the registry (every code, one file per commune, and the area table), gzipped with `gzip -n` into `registry/` |
| 11 | `vectors.py`, `paper-stats.py <work> <work>/lotes.jsonl.gz` | `engine/reference/vectors.json`, `model/stats/building-stats.json` |
| 12 | `paper-figures.py`, `paper-evaluation.py` (from the published registry only) | `docs/figures/*.dat`, the data of the report's figures; `model/stats/evaluation.json`, the measurements of its evaluation chapter |

### The border decides

A code is only ever issued for a building whose entrance lies inside Burkina Faso's national border (OpenStreetMap `admin_level=2`, `country.geojson`) or within 300 m of it (`engine/SPEC.md` 1b). The commune outlines (HDX) and the spot frames reach over the border; they never decide:

- step 4 keeps only footprints whose centre lies inside the border (stricter than 300 m);
- step 7 drops any compound whose point lies more than 300 m outside it (`abroad` in `group-stats.json`; 0 on the N-Ways inputs);
- the server (`422 outside`) and the N-Ways issuer refuse a new code or an entrance more than 300 m outside it; the server uses `engine/data/border.json` from step 2a and `engine/reference/bf_border.py`.

Check a registry against the border with `bf_border.Border.load('<work>/country.geojson')` and `outside_m(lat, lon)` on every `entrance_lat`, `entrance_lng`: of the 8,369,987 published codes, 3,985 lie outside the border, 3,975 of them within 300 m and 10 between 300.0 and 300.5 m.

**After first issue** the register is frozen: never run `build-register.py --freeze` again. An area is renamed only through `model/areas/renames.json` and `rename-areas.py`, which appends new name ids, leaves every other name alone and prints each moved block (old start, new start) for the database.

`engine/reference/gen_vectors.py` writes the design vectors (`engine/reference/test_vectors.json`) from the frozen blocks. The statistics scripts of the design (`stats.py`, `analyse.py`, `places-areas.py`, `national-areas.py`, `sample.sh`) are kept for the record.

### osmium exports

```
P=data/osm/burkina-faso-latest.osm.pbf
osmium tags-filter -o b.osm.pbf $P r/boundary=administrative
osmium export -a type,id -f geojsonseq --geometry-types=polygon -o admin.geojsonseq b.osm.pbf
osmium tags-filter -o bar.osm.pbf $P w/barrier=wall,fence,hedge,retaining_wall n/barrier=gate,entrance,lift_gate,sliding_gate,swing_gate n/entrance
osmium export -a type,id -f geojsonseq -o bar.geojsonseq bar.osm.pbf
osmium tags-filter -o place.osm.pbf $P n/place w/place r/place
osmium export -a type,id -f geojsonseq -o place.geojsonseq place.osm.pbf
osmium tags-filter -o hw.osm.pbf $P w/highway
osmium export -a type,id -f geojsonseq -o hw.geojsonseq hw.osm.pbf
```
