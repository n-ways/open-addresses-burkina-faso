# N-Ways Addressing for Burkina Faso

**Status: issued on 20 October 2026.** Every compound in Burkina Faso has an N-Ways code: 8,369,987 of them, provisional until residents confirm them in the N-Ways app. Where a commune gives an address (the coded streets of Ouagadougou and Bobo-Dioulasso today, their door numbers once shared), that address is the official one and is shown first, exactly as the commune writes it, with the N-Ways code beside it. Every machine code starts with La Poste Burkina Faso's postcode.

A home's code is **the name of a quarter or village people already say plus a number of three to five digits**:

| Code | Machine form | What it is |
|---|---|---|
| `Koulouba 17 76` | `BF-10000-V064-1776-9` | a compound in Ouagadougou, on Avenue Uemoa (shown first) |
| `Bobo 26 206` | `BF-90000-V006-26206-1` | five digits, said as a pair and a hundred: by Bobo-Dioulasso's Grand Marché |
| `Natenga 10 016`, `Natenga 10 286` | | two of 74 places of one name, in Pabré and in Dapélogo: one national range, a block each |
| `BF-10000 E1885 N1262` | | any point: its spot code, a 10 m cell of its commune's grid |

The code is unique in the whole country on its own: every area with the same plate name shares one national range of numbers, cut into frozen blocks of twice its compounds, so "Name number" never needs a commune after it. No number has more than five digits. People never see or type a check digit: a Damm check over the name's national index, the postcode, the area and the number lives in the machine form, for systems. The name is a **plate name** of at most 12 characters and 2 words, with no digit; the official name still finds it. 945 areas carry a provisional short name their commune may change once; their codes are issued, and the number never changes.

No secteur map is public, so towns are coded by their named quarters (OpenStreetMap and GeoNames), like the villages; a secteur form ("Secteur 15 Ouaga") is refused, never guessed.

**The registry is complete.** [`registry/`](registry/) publishes every issued code, one file per commune, with its area, entrance point, spot code, official address where one exists and building profile. Every code has a spot code: an entrance in no published commune outline (a gap between two outlines, or just over a border line) is coded in the frame of the commune with the nearest outline within 10 km whose frame holds it, else at the nearest edge cell of a frame within 3,000 m ([SPEC 5.1](engine/SPEC.md)). The border decides where a code can exist: no code lies more than 300 m outside Burkina Faso's national border (OpenStreetMap `admin_level=2`), whatever commune outline reaches over it ([SPEC 1b](engine/SPEC.md)). It holds places, never people: no names, telephone numbers, household sizes or gate photos. [`server/`](server/) is a ready-made service that serves exactly these addresses as a JSON API, and on the one deployment designated as the issuer, issues new codes by the same rules.

## What is where

| Path | Contents |
|---|---|
| [docs/paper.fr.md](docs/paper.fr.md), [paper.md](docs/paper.md) | the research report in French and English: data, the model with every formula and a worked example, implementation, measured evaluation, the designs rejected, and the benefits for citizens, logistics, emergency services and government; typeset as [PDF (fr)](docs/n-ways-addressing-burkina-faso-fr.pdf) and [PDF (en)](docs/n-ways-addressing-burkina-faso-en.pdf) |
| [docs/paper/](docs/paper/), [docs/figures/](docs/figures/) | the LaTeX typesetting of the report (template, style, bibliography with every reference) and its figures as TikZ/pgfplots sources with their data |
| [docs/api.md](docs/api.md) | the registry server's API: every endpoint with a real request and response |
| [docs/existing-systems.md](docs/existing-systems.md) | verification: La Poste's postcodes, the communes' street codes and door numbers, secteurs, parcels, data protection; verdict and sources |
| [docs/model.md](docs/model.md) | the design notes behind every choice |
| [engine/SPEC.md](engine/SPEC.md) | the engine specification (normative) |
| [engine/reference/bf_engine.py](engine/reference/bf_engine.py), [plate_names.py](engine/reference/plate_names.py), [test_bf.py](engine/reference/test_bf.py), [test_vectors.json](engine/reference/test_vectors.json), [vectors.json](engine/reference/vectors.json) | the reference engine (standard library only), its tests and the conformance vectors every port must reproduce |
| [engine/data/register.json](engine/data/register.json), [units.json](engine/data/units.json), [border.json](engine/data/border.json) | what a decoder ships: communes with their spot frames, every area with its plate and official names, name index, blocks and frame; the aliases; the commune outlines; the national border (simplified to within 3 m), beyond which no Burkina Faso code is issued |
| [registry/](registry/) | every issued code: one `<postcode>.csv.gz` per commune (351), the frozen area table `areas.csv.gz` (every area, its blocks and its count of compounds at issue) and `MANIFEST.json` (counts and SHA-256 of every file) |
| [server/](server/) | the registry server: import, JSON API, issuing by the issuer's rules, export, Docker ([server/README.md](server/README.md), [openapi.yaml](server/openapi.yaml)) |
| [model/](model/) | `areas/` (the code areas, the national name ranges), `units/` (commune outlines, La Poste's postcode table and its matches, spot frames), `stats/` (`register.json`, `building-stats.json`, `name-stats.json`: the figures of the paper), `design.json` |
| [tools/](tools/) | the scripts that built the inputs, the areas, the compounds, the names and the registry ([tools/README.md](tools/README.md)) |
| [GOVERNANCE.md](GOVERNANCE.md), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) | who decides, the one-issuer rule, how to propose a change, how to report a problem |
| [SOURCES.md](SOURCES.md), [LICENSING.md](LICENSING.md), [NOTICE](NOTICE), [CITATION.cff](CITATION.cff) | sources, licences, how to credit and how to cite |

## Run the reference engine

```sh
cd engine/reference
python3 test_bf.py                                   # tests
python3 bf_engine.py resolve Koulouba 17 76          # remembered form: one area in the whole country
python3 bf_engine.py resolve Natenga 10 286
python3 bf_engine.py resolve "Secteur 15 Ouaga 48217"   # refused: secteurs are not codes
python3 bf_engine.py verify BF-10000-V064-1776-9     # validate a machine code
python3 bf_engine.py spot 12.3641615 -1.5166371      # spot code: BF-10000 E1885 N1262
python3 bf_engine.py unspot "BF-10000 E1885 N1262"
```

Python 3.9 or newer, no packages (see [requirements.txt](requirements.txt)).

## Run the server

```sh
cd server && docker compose up -d          # imports the bundled registry on first start, then serves
curl -s 'localhost:8080/v1/find?q=Koulouba%2017%2076'
```

Or without Docker, from the repository root:

```sh
python3 -m server import --registry registry --db data/addresses.sqlite
python3 -m server serve --db data/addresses.sqlite --port 8080
python3 -m unittest discover -s server/tests -t .   # the server's tests
```

A deployment is read-only unless the State or N-WAYS LIMITED has designated it as the issuer: two issuers would hand out the same number twice ([server/README.md](server/README.md), [GOVERNANCE.md](GOVERNANCE.md)). Every endpoint, with real responses: [docs/api.md](docs/api.md).

## Build the paper

The report is pandoc Markdown with TeX mathematics ([docs/paper.md](docs/paper.md), [docs/paper.fr.md](docs/paper.fr.md)); the references are in [docs/paper/references.bib](docs/paper/references.bib) and the figures are TikZ/pgfplots sources in [docs/figures/](docs/figures/), each with the data file it plots. With pandoc 3, tectonic and pdftocairo installed:

```sh
python3 tools/paper-figures.py       # figure data from the registry and register (docs/figures/*.dat)
python3 tools/paper-evaluation.py    # the measurements of the evaluation chapter (model/stats/evaluation.json)
sh docs/paper/build.sh               # figures to PDF and SVG, then docs/n-ways-addressing-burkina-faso-{en,fr}.pdf
```

## How the registry was made

```sh
python3 tools/prepare-inputs.py <work>              # enclosures, estates, gates, places, communes, the two cities' streets
python3 tools/build-areas.py <work> <BF.txt>        # the code areas, from OpenStreetMap and GeoNames
python3 tools/extract-buildings.py <work>           # every footprint inside Burkina Faso (DuckDB, 3 GB cap), with its commune and street
python3 tools/assign-areas.py <work>                # each footprint's code area and every area's frame
python3 tools/sort-buildings.py <work>              # sorted by area
python3 tools/issue_registry.py group <work>        # compounds and profiles, one area at a time
python3 tools/build-register.py <work> --freeze     # plate names, national ranges and blocks on the real compounds
python3 tools/issue_registry.py number <work> <work>/lotes.jsonl.gz
python3 tools/vectors.py                            # engine/reference/vectors.json
python3 tools/paper-stats.py <work> <work>/lotes.jsonl.gz
python3 tools/paper-figures.py && python3 tools/paper-evaluation.py
```

The N-Ways issuer then issues the codes, checking every number against the reference's, and exports `registry/`. Since 20 October 2026 the register is frozen: a new run adds codes for new compounds and never renumbers an issued one.

## Licence and credit

Code (engine, tools): Apache License 2.0, with [NOTICE](NOTICE). Data (registry, model, engine data): ODbL 1.0. Documents: CC BY 4.0. Credit every use: **"N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"**, with a link to this repository ([LICENSING.md](LICENSING.md)). Derived from OpenStreetMap (© OpenStreetMap contributors, ODbL), GeoNames (CC BY 4.0), Google Open Buildings (CC BY 4.0), Microsoft building footprints (ODbL) and OCHA's commune boundaries (CC BY-IGO); the commune numbers are La Poste Burkina Faso's postcodes.
