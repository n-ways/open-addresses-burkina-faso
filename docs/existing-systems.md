# Existing address and postcode systems in Burkina Faso

Checked 18 October 2026. "Opened" means the page or file was read on that date; "snippet" means it was seen only in a search result and is not verified. Full list in [SOURCES.md](../SOURCES.md).

**Re-checked 20 October 2026,** before the first issue. The communes' readdressing goes on (Ouagadougou launched arrondissements 5 and 12 in April 2025: about 2,277 streets and 43,000 doors, with the European Union; the PASIU pilot had covered three arrondissements, more than 93,000 doors and 16,000 streets), but its data is still not open. **No secteur map is public**: none in OpenStreetMap, none on HDX or geoBoundaries (communes only), none on the communes' or INSD's sites (INSD publishes secteur lists and populations, not boundaries). So towns are coded by their named quarters, from OpenStreetMap and GeoNames, like the villages, and every number stays at 5 digits or fewer; secteur codes become aliases once a commune shares its map. 1,571 named streets of Ouagadougou and Bobo-Dioulasso carry the communes' street codes in OpenStreetMap ("Rue 15.123"); they are shown first. Komsilga still has no La Poste code. Data protection: Loi 001-2021/AN, CIL. The UK FCDO advises against all travel to Burkina Faso, Ouagadougou included (advice of 10 December 2025).

## Verdict

**Burkina Faso has official postal codes, but they are coarse: commune level everywhere, quartier-group level in Ouagadougou and Bobo-Dioulasso. They are not door-level.** Door-level street addressing exists in parts of Ouagadougou and Bobo-Dioulasso and is being renewed arrondissement by arrondissement; it has no public lookup or open data.

A common assumption that Burkina Faso has no postcode in practical use is therefore wrong: La Poste's codes exist and are reused here.

So the N-Ways model in Burkina does not invent an area code: it **reuses the La Poste postcode** as the first part of every machine code and adds the compound (concession) level the postcode lacks.

## 1. La Poste Burkina Faso postcodes

| Item | Finding | Source |
|---|---|---|
| Format | 5 digits, written before the locality: "10010 OUAGADOUGOU" | UPU addressing sheet for Burkina Faso, dated 12/2021 (opened; a scanned image, read after rendering) |
| Structure | 1st digit: region; 1st+2nd: province; 3rd+4th: quartier, commune, town, agency or large customer; 5th: type (0 = commune or quartier, 1–8 = agency) | codespostaux.laposte.bf, structure diagram (opened) |
| Coverage | all 351 communes have a code (every commune code ends in 0) | full public table harvested 18 Oct 2026 in 125 polite requests (see below) |
| Big towns | Ouagadougou 6 zones 10000, 10010, 10020, 10030, 10040, 10050 (66 quartier names); Bobo-Dioulasso 4 zones 90000–90030 (56 quartier names); no other commune has quartier codes | same |
| Agencies | 109 agency codes (e.g. Bama 90201, Koudougou 40001) | same |
| Region digit | still follows the 13 regions and 45 provinces in force before 2025 (e.g. province names Sanmatenga, Soum, Kossi) | same |
| Address types | "BP / Boîte postale / Poste restante / BV + number" then the agency postcode + locality; or a 7-line geographic address (identity, flat/letterbox, building, number + street, lieu-dit or landmark, postcode + locality, country) | codespostaux.laposte.bf (opened); UPU sheet (opened) |
| UPU examples | "Domicile 1114 / 566 Avenue de la Nation / BV 31000 OUAGA CNT / 10010 OUAGADOUGOU"; "BP 56 / 91001 BAMA" | UPU sheet (opened) |
| Open data | no bulk download, API or licence found; DataHub's Burkina page: "No data is currently available" | datahub.io (opened) |

The harvested table is in [`model/units/laposte-postcodes.json`](../model/units/laposte-postcodes.json) (582 codes: 351 commune, 122 quartier, 109 agency). It was matched to the 2025 HDX commune boundaries in [`model/units/communes.csv`](../model/units/communes.csv): 294 exact name matches, 55 spelling matches marked `(verify)` (for example Goursi = GOURCY, Koala = COALLA), one manual match (Thiou in Boulkiemdé = THYOU 40850) and one gap: **Komsilga (Kadiogo) has no row in La Poste's table**, while La Poste lists CINKANSE 70550, which has no polygon in the HDX file. Both need to be resolved with La Poste.

Discrepancy noted: the UPU sheet pairs 91001 with Bama; La Poste's live lookup gives 91001 = Orodara agency and Bama = 90200/90201. We follow La Poste's live table.

The older box form "01 BP 617 Ouagadougou 01" is still widely used (the two-digit prefix appears to name the post office holding the box). Its rule is not documented in any primary source we found (unverified).

## 2. Street and door addressing in towns

| Item | Finding | Source |
|---|---|---|
| History | Ouagadougou and Bobo-Dioulasso first addressed in 1985 | Sidwaya, 12 Apr 2022 (opened) |
| 2009 redistricting | Ouagadougou from 5 to 12 arrondissements and 30 to 55 secteurs; Bobo from 3 to 7 arrondissements and 25 to 33 secteurs; old street numbers broken | Sidwaya 2022 and 24 Oct 2023 (opened) |
| Street code | "Rue 54.160" = secteur number + street order number ("un numéro en fonction du secteur"); door numbers reported metric and alternating | Sidwaya 2023 (opened); World Bank *Street Addressing and the Management of Cities* summary (snippet; PDF returned 403) |
| Renewal campaign | AMB (Association des municipalités du Burkina) with the European Union, launched 22 Nov 2021: more than 16,000 streets, every dwelling numbered, free | Burkina24, 22 Nov 2021 (opened) |
| Progress | PASIU (Projet d'appui au système d'information urbaine, EU, about EUR 1M pilot): by Oct 2023 more than 16,000 streets and more than 93,000 doors in Ouagadougou (3 pilot arrondissements) and Bobo; platforms "Easy Geo" and "Webmapping grand Ouaga data"; Koudougou, Dédougou, Banfora mentioned next | Sidwaya, 24 Oct 2023 (opened) |
| 2025 | Ouagadougou arrondissements 5 and 12 from 2 Apr 2025, after arrondissements 1 and 2: more than 2,277 streets, 43,000 doors, about 240,000 people, municipal address database planned | Burkina24, 2 Apr 2025 (opened) |
| In OpenStreetMap | 1,556 street ways in central Ouagadougou carry an "NN.NNN" code, all with secteur numbers 1–30: the **pre-2009** numbering | N-Ways OSM extract, Oct 2026 |
| Open data, lookup | none found; no 2025–2026 completion report found | — |

**Consequence for the model:** secteur numbers changed once (2009), street codes in the wild still show the old ones, and no secteur map is public. Secteurs are therefore not code areas: the towns are coded by their named quarters, and a secteur becomes an alias once its commune shares the map. Where the commune has given a street code or a door number, that official address is shown first and the N-Ways code sits beside it (below).

## 3. Parcels and cadastre (who already numbers plots)

| Item | Finding | Source |
|---|---|---|
| Law | Loi 034-2012/AN (Réorganisation agraire et foncière, RAF), Décret 2014-481; rural land Loi 034-2009 | DGI brochure (opened) |
| Titles | PUH (permis urbain d'habiter), attestation d'attribution, permis d'exploiter/d'occuper; titre foncier | DGI (opened) |
| Numbering | Décret 2012-1006: "numéro de section / numéro d'îlot / numéro de parcelle", numbers from 01, letters forbidden (art. 11), old letter references kept in brackets (art. 25), lotissement numbering issued by the cadastre (art. 26) | DGI, OCR of the decree (opened) |
| Older example | "parcelle n°1 du lot 26 de la section VN du secteur 28" (court decision, 2011) | juriburkina.justice.gov.bf (snippet) |
| Data | DGI eCadastre: 434,274 parcels digitised by end 2022 of about 1.26 million; SyC@D at sif.bf since 21 Mar 2025 (Bobo-Dioulasso from Apr 2026); not open data | dgi.bf (opened) |
| Geodesy | IGB GNSS-CORS network, 13 stations; Décret 2012-444: boundary markers within 7 cm, sketches in non-developed zones within 3 m, coordinates in the "référentiel national" (datum not named in the text; Point 58 / Clarke 1880 exists in EPSG; whether WGS84/UTM 30N is now used is unverified) | igb.bf, dgi.bf (opened); epsg.io (opened) |
| Surveyors | plans by the cadastre or a géomètre-expert under its control (art. 266); Ordre des Géomètres-Experts du Burkina | DGI (opened) |
| Informal land | non-loti (spontaneous) zones have no parcel numbers; more than 30% of Ouagadougou residents live there | MUAFH (opened); AFD 2021 note (snippet) |

## 4. Digital address products

None national. No what3words or Plus Codes programme by the government, La Poste, ANPTIC or IGB was found. The only digital address tools are La Poste's postcode lookup and PASIU's municipal platforms.

## 5. Administrative frame (for code areas)

- 2 Jul 2025 Council of Ministers: 17 regions (Bankui, Djôrô, Goulmou, Guiriko, Kadiogo, Kuilsé, Liptako, Nakambé, Nando, Nazinon, Oubri, Sirba, Soum, Sourou, Tannounyan, Tapoa, Yaadga) and 47 provinces (Burkina24, KOACI, opened). ISO 3166-2 still shows BF-01..13 (PCGN factfile, May 2026, opened; ISO page 403).
- 351 communes (49 urban, 302 rural; snippet); HDX COD-AB boundaries dated 2025-08-01 with 17/47/351 units (downloaded, CC BY-IGO).
- Ouagadougou 12 arrondissements / 55 secteurs; Bobo-Dioulasso 7 / 33 (Sidwaya, opened).
- Population RGPH 2019: 20,505,155; Ouagadougou 2,415,266; Bobo-Dioulasso 904,920 (INSD, snippet).

## 6. Data protection

Loi n° 001-2021/AN du 30 mars 2021 (personal data; adopted 30 Mar 2021, Sidwaya, opened); authority: Commission de l'Informatique et des Libertés (CIL, cil.bf, opened): prior declaration, public register; it has a deliberation on "géolocalisation" whose text we could not read (unverified).

## What the model takes from this

Two principles follow from the verification: where the State has given an address, it is used as it is and nothing competes with it; and every home still gets a code, so that one form of address works in every commune.

1. **Where the commune has given an address** (the coded streets of Ouagadougou and Bobo-Dioulasso, "Rue 15.123", and the door numbers of the readdressed arrondissements), that official address is shown first, exactly as officially written: the official street within 30 m of a compound today, a door number once the commune shares its data (PASIU platforms "Easy Geo" and "Webmapping grand Ouaga data"; access to be requested from the communes and the AMB) or residents read it from the plate. The N-Ways code sits beside it.
2. **Every compound has an N-Ways code**, official address or not: the name of a quarter or village people already say and a number of at most 5 digits.
3. The La Poste postcode is not an address (it names a commune or zone), but it is the first part of every machine code. Komsilga, which has no La Poste code, uses 10990, outside La Poste's series, until La Poste gives it one.
4. **No secteur map is public**, so secteurs are not code areas: the towns are coded by their named quarters, like the villages. A secteur form ("Secteur 15 Ouaga") is refused, never guessed; secteur names become aliases once a commune shares its map. In the code, the name is a plate name of at most 12 characters and 2 words; the town short forms people already say are documented (Ouaga, Bobo, Fada: [SOURCES.md](../SOURCES.md), "Short place names").
5. Cadastral section, îlot and parcelle are cross-references on the compound, never a replacement.
6. No region or province name in the code (renamed in 2025).
7. **Safety.** The registry publishes places, never people: every code with its entrance and profile, and no names, telephone numbers, gate photos or sites for displaced people (engine/SPEC.md §12).
