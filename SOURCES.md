# Sources — open-addresses-burkina-faso

All accessed 18 October 2026 unless stated. "Opened" = read on that date; "snippet" = seen only in a search result (not verified).

## Postal codes and postal addressing

| Source | Publisher | Date | Status |
|---|---|---|---|
| https://www.upu.int/UPU/media/upu/PostalEntitiesFiles/addressingUnit/bfaEn.pdf — Burkina Faso addressing sheet | UPU | 12/2021 | opened (scanned image, rendered) |
| https://codespostaux.laposte.bf — postcode lookup, structure diagram `images/structureCP.png` | La Poste Burkina Faso | n.d. | opened |
| https://codespostaux.laposte.bf/admin/search_ville.php?Loc=<1..99> and /admin/search_cdpt.php?Loc=<A..Z> — full table harvest (125 requests, 1.5 s apart, generic User-Agent) → `model/units/laposte-postcodes.json` | La Poste Burkina Faso | 18 Oct 2026 | opened |
| https://datahub.io/logistics/postal-codes-bf | DataHub | n.d. | opened ("No data is currently available") |
| UBA Burkina branch list (01 BP 362 Ouagadougou 01) | UBA | 2021 | snippet |

## Street and door addressing

| Source | Publisher | Date | Status |
|---|---|---|---|
| https://burkina24.com/2021/11/22/burkina-faso-la-campagne-dadressage-urbain-de-ouaga-et-de-bobo-lancee/ | Burkina24 | 22 Nov 2021 | opened |
| https://burkina24.com/2025/04/02/ouagadougou-modernise-son-adressage-pour-faciliter-la-localisation/ | Burkina24 | 2 Apr 2025 | opened |
| https://burkina24.com/2021/06/12/burkina-faso-la-rue-54-160-rebaptisee-rue-pape-benoit-xvi/ | Burkina24 | 12 Jun 2021 | snippet |
| https://www.sidwaya.info/communes-urbaines-des-acteurs-sapproprient-le-nouveau-plan-dadressage/ | Sidwaya | 24 Oct 2023 | opened |
| https://www.sidwaya.info/bobo-dioulasso-bientot-de-nouveaux-numeros-pour-les-rues-domiciles-et-institutions/ | Sidwaya | 12 Apr 2022 | opened |
| World Bank, *Street Addressing and the Management of Cities* (Farvacque-Vitkovic et al.), openknowledge.worldbank.org | World Bank | 2005 | snippet (PDF 403) |
| Urban Addressing Practices and Geocoding (IJACSA paper) | SAI | n.d. | snippet (DNS failure) |
| OpenStreetMap street refs "NN.NNN" in Ouagadougou (1,556 ways, secteurs 1–30) | OSM via N-Ways extract | Oct 2026 | computed |

## Short place names (plate names)

Every short form used as a plate name or town word in place of an official name (docs/model.md §3.6; `KNOWN_TOWNS` in `tools/name-ranges.py`):

| Short form | Official name | Source | Status |
|---|---|---|---|
| Ouaga | Ouagadougou (10000) | https://en.wikipedia.org/wiki/Ouagadougou — "The city's name is often shortened to Ouaga"; also the subtitle of https://fr.wikipedia.org/wiki/Ouagadougou | opened |
| Bobo | Bobo-Dioulasso (90000) | https://en.wikipedia.org/wiki/Bobo_people — "Bobo is also a shortened name of the second-largest city in Burkina Faso, Bobo-Dioulasso" | opened |
| Fada | Fada N'Gourma (75000) | https://fr.wikipedia.org/wiki/Fada_N%27Gourma — "les colonisateurs l'appelèrent « Fada »" | opened |

The two place nodes named after the cities take the same short forms: the area "Bobo-Dioulasso" is **Bobo**, the area "Fada N'Gourma" is **Fada** (same sources). No other short form of a place name is documented; the others are shortened by rule or flagged for the commune. Thyou (Boulkiemdé): https://en.wikipedia.org/wiki/Thyou_Department spells the commune "Thyou" and "Thyrou" (opened); not used, the commune chooses.

## Parcels, land law, geodesy

| Source | Publisher | Date | Status |
|---|---|---|---|
| https://dgi.bf/wp-content/uploads/2023/10/ — brochure Loi 034-2012 RAF + Décret 2014-481 | DGI | 2012/2014 | opened |
| Décret 2012-1006 (entités du plan cadastral), dgi.bf PDF | DGI | 20 Dec 2012 | opened (OCR) |
| Décret 2012-444 (normes des travaux topographiques et cadastraux), dgi.bf PDF | DGI | 24 May 2012 | opened (OCR) |
| Dossier titre foncier checklist, dgi.bf PDF | DGI | 2023 | opened |
| https://dgi.bf/digitalisation-de-la-gestion-fonciere-la-plateforme-sycd-en-marche/ | DGI | Mar 2025 | opened |
| https://dgi.bf/informatisation-du-cadastre-national-…/ (434,274 parcels) | DGI | 4 Mar 2023 | opened |
| https://igb.bf/presentation-du-reseau-gnss-cors/ | IGB | n.d. | opened |
| https://igb.bf | IGB | — | opened |
| https://mhu.gov.bf | MUAFH | 2026 | opened |
| https://epsg.io/4620 (Point 58) | epsg.io | — | opened |
| juriburkina.justice.gov.bf, Arrêt 04/2010-2011 du 14 juin 2011 ("parcelle n°1 du lot 26 de la section VN du secteur 28") | Justice BF | 2011 | snippet |
| lists.openstreetmap.org/pipermail/talk-bf/2014-May/000069.html ("parcelle 05, lot 11, section 474") | OSM talk-bf | 2014 | snippet |
| AFD note DPP29, inégalités quartiers informels Ouagadougou (>30% in non-loti) | AFD | Feb 2021 | snippet |

## Administration, population, languages, security

| Source | Publisher | Date | Status |
|---|---|---|---|
| https://burkina24.com/?p=408700 — Conseil des ministres 2 Jul 2025 | Burkina24 | 2 Jul 2025 | opened |
| https://www.koaci.com/article/2025/07/02/burkina-faso/politique/burkina-faso-nouveau-decoupage-administratif-du-territoire-les-regions-rebaptises_188249.html | KOACI | 2 Jul 2025 | opened |
| https://fr.wikipedia.org/wiki/Régions_du_Burkina_Faso | Wikipedia | — | opened |
| Burkina Faso Toponymic Factfile, assets.publishing.service.gov.uk | UK PCGN | May 2026 | opened |
| https://www.iso.org/obp/ui/#iso:code:3166:BF | ISO | — | not opened (403) |
| https://data.humdata.org/dataset/cod-ab-bfa — admin boundaries 2025-08-01 (17/47/351), CC BY-IGO | OCHA/HDX | 2025 | downloaded |
| geoBoundaries BFA ADM3 (gbOpen) | geoBoundaries | 2007 data | downloaded (not used for keys) |
| INSD RGPH 2019 key figures (insd.bf/fr/file-download/download/public/2075) | INSD | 2022 | opened (no literacy figure) |
| INSD "Alphabétisation et scolarisation" (2014 table) | INSD | 2014 | snippet |
| sng-wofi.org country profile (351 communes: 49 urban, 302 rural) | SNG-WOFI | n.d. | snippet |
| Constitution revision 2023/24 (national languages official) — Le360 / Burkina24 | press | Dec 2023 / 25 Jan 2024 | snippet |
| fr.allafrica.com/stories/202506110148.html (displacement 2025) | AllAfrica | Jun 2025 | snippet |
| voyage.gc.ca — emergency numbers (17 police, 18 fire) | Government of Canada | — | snippet |
| https://www.gov.uk/foreign-travel-advice/burkina-faso — advice against all travel to Burkina Faso, no area excepted | UK FCDO | 10 Dec 2025 (checked 20 Oct 2026) | opened |

## Data protection

| Source | Publisher | Date | Status |
|---|---|---|---|
| https://www.sidwaya.info/protection-des-donnees-a-caractere-personnel-une-nouvelle-loi-pour-renforcer-le-cadre-legal/ | Sidwaya | 30 Mar 2021 | opened |
| https://www.cil.bf | CIL | — | opened (geolocation deliberation text not readable) |

## Data used for the statistics

| Data | Licence | Notes |
|---|---|---|
| OpenStreetMap buildings, places, barriers, gates (Geofabrik extract via N-Ways, 17 Oct 2026) | ODbL | `data/detail/countries/burkina-faso/`, `data/osm/burkina-faso-latest.osm.pbf` |
| OpenStreetMap national border of Burkina Faso (relation 192783, `boundary=administrative`, `admin_level=2`), from N-Ways' West African boundaries | ODbL | `data/osm/westafrica-admin.osm.pbf`; decides where a code can exist (engine/SPEC.md 1b); shipped simplified as `engine/data/border.json` |
| Google Open Buildings + Microsoft footprints (Overture), with ML height `h` | CC BY 4.0 / ODbL | `data/detail/ml/BF.parquet` |
| GeoNames `BF.txt` (populated places, feature class P), downloaded 20 Oct 2026 from https://download.geonames.org/export/dump/ | CC BY 4.0 | 7,117 of the 17,518 code areas are seeded from it (`tools/build-areas.py`); "contains GeoNames data" |
| N-Ways places (places table, read-only) | mixed upstream (OSM, Overture, GRID3, FSQ...) | capital POIs inside footprints |
| N-Ways gates/compounds (`data/valhalla/`) | derived from OSM | detection inputs |

## Algorithms

| Source | Notes |
|---|---|
| H. M. Damm, "Totally anti-symmetric quasigroups for all orders n ≠ 2, 6", *Discrete Mathematics* 307 (2007) | check digit table (standard published table) |
| D. Hilbert, "Über die stetige Abbildung einer Linie auf ein Flächenstück", *Math. Annalen* 38 (1891) | space-filling order |
