# The N-Ways address model for Burkina Faso

These are the design notes behind the model: the options weighed, the measurements behind each choice, and the reasons. The codes were issued on 20 October 2026: 8,369,987, one for every compound, the official address shown first wherever one exists. Two findings shaped the issued model more than any other: **no secteur map is public**, so towns are coded by their named quarters (OpenStreetMap and GeoNames) and secteur forms are refused; and every number has **at most 5 digits**, the length people repeat reliably after one hearing. The figures marked *design register* were measured on the OpenStreetMap villages before the GeoNames quarters were added; [engine/SPEC.md](../engine/SPEC.md) (normative) and [paper.md](paper.md) give the issued figures. Machine-readable form: [`model/design.json`](../model/design.json).

This model is made for Burkina Faso: its engine, format and code are its own.

## 1. What Burkina already has, and what is missing

- **An official postcode** (La Poste Burkina Faso): 5 digits, one per commune (351), six zones in Ouagadougou and four in Bobo-Dioulasso. It says which commune or zone; it does not say which house. See [existing-systems.md](existing-systems.md).
- **Street codes and door numbers** in parts of Ouagadougou and Bobo-Dioulasso ("Rue 54.160": secteur 54, street 160; metric door numbers), being renewed since 2021 by the AMB and the European Union, arrondissement by arrondissement.
- **Parcel numbers** (section / îlot / parcelle, all digits since Décret 2012-1006) on lotissement plots, about 434,000 digitised by the DGI out of about 1.26 million.
- **Nothing** for the non-loti zones (more than 30% of Ouagadougou residents), for villages, for compounds without a painted number, or for anyone who wants to share an exact gate.

The N-Ways address fills that last gap and points to the other three.

### 1.1 Official addresses first

Where the State or a commune has already given an address, that address is the one people, the post and public services use. The model therefore never competes with it: it is imported and shown first, exactly as written, and the N-Ways code sits beside it.

| Area | Official system | Data obtainable? | What N-Ways does |
|---|---|---|---|
| Readdressed arrondissements of Ouagadougou (1, 2, 5, 12 and the 2023 pilot arrondissements) | Commune street codes "Rue <secteur>.<order>" + door numbers (AMB/EU, PASIU) | Communal platforms "Easy Geo", "Webmapping grand Ouaga data"; not open; request from the Commune and AMB (data-sharing agreement, terms to agree) | Imports and shows the official address exactly as written, first; adds gate position, building profile, spot code; the compound keeps its N-Ways code beside it |
| Readdressed parts of Bobo-Dioulasso | Same scheme (PASIU, from Apr 2022) | Same, from the Commune de Bobo-Dioulasso | Same |
| Older 1985 / pre-2009 street codes still signed (e.g. in OSM: secteurs 1–30) | Legacy commune codes | OSM (ODbL) partly; commune archives | Stored as an alias on the street; not issued as an address |
| Non-loti zones, secteurs not yet readdressed, other towns, all villages | none at door level | — | **N-Ways address** (this model) |
| Everywhere | La Poste postcode (commune / zone, not an address) | public lookup, table harvested | Pointer: machine prefix of N-Ways codes, attribute of official addresses |
| Lotissement plots | section / îlot / parcelle (DGI) | SyC@D / eCadastre, not open | Cross-reference only |

When a secteur is readdressed by its commune after N-Ways codes were issued there, the official address becomes the address shown first for each compound and the N-Ways code still resolves (plates are the commune's, not N-Ways').

## 2. Design criteria, in order

1. **Easy to remember, easy to get.** A code nobody remembers is not used, so this criterion comes first.
2. **The compound is the unit**, the gate is the entrance.
3. **Stable**: a code never changes or moves once given.
4. **Official addresses first**: where the commune has given a door address, use the commune's data and create nothing; reuse the postcode as a pointer; parcel numbers as cross-references; never call the N-Ways address a postcode or an official address.
5. **Works offline**, open method, open data (Apache 2.0, ODbL 1.0, CC BY 4.0: [LICENSING.md](../LICENSING.md)).
6. **Privacy and safety**: codes describe places, never people; extra care in zones under security alert.

## 3. Criterion 1: remembering

### 3.1 What people in Burkina already remember

- **Secteur numbers.** Townspeople say "secteur 15", "secteur 28". Every urban commune is divided into numbered secteurs; street codes start with the secteur number.
- **Village names.** In rural communes the village (and the hamlet, the quartier of the village) is the place word.
- **Phone numbers**, 8 digits, written and read in pairs in French ("70 12 34 56").
- **Digits rather than letters.** Adult literacy in Burkina Faso is low (INSD's last table we found is from 2014; a current rate was not verified). Arabic numerals are read by people who do not read French, and number words exist in every national language (Mooré, Dioula, Fulfulde, Gulmancema...).

### 3.2 Options compared

The arithmetic was done at design time on N-Ways' building map (OpenStreetMap + Google/Microsoft footprints): 13,309,722 structures in Burkina, grouped into an estimated 7.32 million compounds (ratio 0.546 structures→compounds measured in Ouagadougou, see §4). Capacity rule: today's compounds × 2 must fit the number range (room for growth and infill).

| Option | Example | Length people must remember | Fits? | Verdict |
|---|---|---|---|---|
| A. Alphanumeric code per commune (Plus-Code-like alphabet) | `10000-7HQ2X` | 5 letters/digits | Ouagadougou 616,565 compounds × 2 = 1.23 M ≤ 20⁵ = 3.2 M | Rejected: letters must be learnt, spelled and heard right; poor for low literacy |
| B. Digits only, per commune | `10000 · 4 821 734` | 7 digits | 1.23 M needs 7 digits in Ouagadougou | Rejected: too long; no place word |
| C. Digits only, per La Poste zone | `10040 · 482 173` | 6 digits + a zone code nobody knows by heart | Ouagadougou zones average ~103,000 compounds → 6 digits | Rejected: zone codes are not the words people use |
| D. Parcel number | `Section 12 / Îlot 045 / Parcelle 07` | 3 numbers | only lotissement plots (about 434,000 digitised of 1.26 M); none in non-loti zones; changes on re-lotissement | Kept as a cross-reference |
| E. Official street + door | `Rue 15.123, porte 45` | 2 numbers | readdressed arrondissements only | **Used as the address there**, shown first; the N-Ways code sits beside it |
| **F. Place word + short number (chosen)** | **`Nabadogo 35 30`**, **`Bissiga 16 870`**, **`Koulouba 17 76`** | **3–5 digits after words people already say** | see below | **Chosen**; secteur variant (`Secteur 15 Ouaga · 48 217`) not issued: no secteur map is public |

Option F, the arithmetic (the secteur variant was measured first; the issued model codes towns by their named quarters):

- **Ouagadougou**: 616,565 compounds over 55 secteurs = 11,210 per secteur on average; × 2 = 22,420 ≤ 90,000 → **5 digits** (10000–99999). Four digits (capacity 9,000, so at most 4,500 compounds) would need about 137 areas, which means splitting every secteur in two or three by sub-quartier names people do not all use. Five digits after "Secteur 15 Ouaga" is the better trade: words people know, then a number the length of half a phone number.
- **Bobo-Dioulasso**: 322,928 structures × 0.546 = 176,300 compounds over 33 secteurs = 5,343 each → 5 digits for most, 4 digits for small secteurs.
- **Villages**: with the 11,053 named places in OpenStreetMap as area centres, 10,893 areas hold buildings; **7,264 fit 3 digits, 3,447 fit 4 digits, 177 need 5 digits and 5 are larger** (the large ones are town quarters with one name point for a whole town, such as Tampouy, Tabtenga, Pouytenga). By compounds: 16.8% in 3-digit areas, 53.8% in 4-digit, 25.4% in 5-digit, 4.0% in larger areas that must be split before issue ([`model/stats/national-areas.json`](../model/stats/national-areas.json)). The median village area holds 257 compounds.
- **Villages under the national-name rule** (§3.5) and the plate-name rule (§3.6): counted on the issuing units themselves, the 7,952 villages and hamlets of the design register with the town nodes taking their own compounds ([`model/stats/name-stats.json`](../model/stats/name-stats.json)), **3,386 villages get 3 digits, 4,137 get 4 digits, 265 get 5 digits** (on the full official names: 3,442 / 4,114 / 232; with each village its own range: 4,274 / 3,426 / 88). By compounds: 12.0% / 70.3% / 17.7%. 1,012 villages get one digit more than their own size needs, 783 of them because their plate name is shared.

So most rural households get **3 or 4 digits** (4 for seven in ten). Townspeople get the code of their named quarter, with at most 5 digits.

### 3.3 The forms

| Form | Example | Who uses it |
|---|---|---|
| Remembered (town) | **Koulouba 17 76**: the named quarter, like a village (a secteur form is refused) | residents, by voice and on paper |
| Remembered (village) | **Nabadogo 35 30**; **Bissiga 14 980** (the Bissiga of Sabou) and **Bissiga 16 870** (the Bissiga of La-Toden): the number says which Bissiga; the name is the short plate name (§3.6): **Yamako 100** for Soussougou Yamako | residents |
| Written with its check | **Bissiga 16 870-9** (accepted from systems that send it; never shown to people) | systems |
| Plate | `KOULOUBA 17 76` large; the official name small; QR code to nways.ng (the machine form is in the QR code, never on the plate) | gate, courier |
| Machine | `BF-10000-V064-1776-9` = postcode + area + number + Damm check digit (the check also covers the area's national name) | apps, partners, systems |
| Spot (any point) | `BF-10000 E1809 N1351` (metres east/north in 10 m units) | sharing a spot, rural fields, markets |

No letter and no check digit are in the remembered form; the machine form adds them and maps 1:1 to it. "V" is a letter for software only; people say the quarter or village name. **Every remembered form names exactly one compound in the whole of Burkina on its own** (§3.5): nothing is taken from the phone's position or from a town said after a comma.

Spoken: numbers in pairs from the left, as phone numbers are read: 41 17 "quarante-et-un dix-sept"; 48 217 "quarante-huit deux cent dix-sept"; 217 "deux cent dix-sept". In Mooré and Dioula the app's voice says the number in the user's language; number words in those languages are decimal (for example Mooré *ye, yiibu, tãabo...*, Dioula *kelen, fila, saba...*: to be checked with native speakers in the memorability study, §11).

Secteur numbers have changed before (2009): a secteur form, once a commune shares its map, is an alias, and the machine code stays (§6).

### 3.4 Getting the code: steps

| Situation | Steps |
|---|---|
| Home already saved in the N-Ways app | 0: "Mon adresse" shows it on opening (the official street address where one exists, else the N-Ways address) |
| At home, not saved | 1: stand at the gate, tap "Je suis à mon portail" |
| Share it | 1 tap: WhatsApp or SMS link (nways.ng link that opens the gate in any phone browser) |
| No smartphone | the plate on the gate; a relative or courier looks it up for them |
| New home not on the map | "Ajouter ma maison", 5 steps (§8) |
| Courier or company | looks up the customer's code from a description or a shared spot (partner API) |

There is no USSD or SMS lookup service.

### 3.5 One name, one national number range

Burkina repeats village names all the time: Mossi names describe a place ("Bissiga", "Douré", "Goghin", "Tanghin", "Yargo") and are given again in every province. Letting the phone's position or a commune said after a comma ("Bissiga 217, Sabou") tell them apart was considered and rejected: a code said on the telephone to a courier in another town, or written on a form, carries no position, and a commune after a comma is the first thing people leave out. **The remembered code alone must be unique in the whole country.**

**Villages.** Every village or hamlet whose name normalises to the same key draws its numbers from **one national range for that name**, cut into **one block per village**:

- **Normalisation** (Burkina French spelling of Mooré, Dioula, Fulfulde, Gulmancema names): accents and case folded; a leading "Q"/"Quartier"/"Hameau"/"Village de" and the articles le/la/les/l' dropped; spaces, hyphens, apostrophes and dots dropped; the spelling pairs folded: *tch = c, dj = j, gh = g, ph = f, ou = w = u, gu before i/e = g*; doubled letters single. So Douré = Doure, Ouatinoma = Watinoma = Wattinooma, Goghin = Gogin = Goguin, Tanguin = Tanghin, Sanga = Sangha. A qualifier that is part of the official name stays ("Bissiga-Peulh" is its own name). Folding errs on the side of merging: two names wrongly folded together still decode apart (different blocks); two spellings left apart would not.
- **Blocks**: each village's block is twice its compounds today, rounded up to a multiple of 10 (at least 20): room for infill and growth inside the block. Blocks are laid one after the other from the bottom of the name's range, in register order (postcode, then village index) at first issue.
- **Length**: all villages of one name have the same number of digits: the smallest of 3, 4, 5 whose range holds all blocks **with the top tenth left spare** for villages that will carry the name later. Bissiga (16 areas) needs 8,510 numbers, more than the 8,100 a four-digit name may use, so it has 5 digits: the Bissiga of Bissiga commune 10000–13559, the Bissiga of Sabou 14980–15539, the Bissiga of La-Toden 16870–17469, and so on to 18509; 18510–99999 are spare.
- **Decoding**: "Bissiga 16 870" → the Bissiga key → the block 16870–17469 → the Bissiga of La-Toden (Passoré). "Bissiga 14 980" → the Bissiga of Sabou. No position, no commune is asked. The app still shows the village and commune it found before guiding there.
- **Generic labels** in the map ("village", "Campement d'éleveurs", "Site de recasement": 98 points) are not names; they get their real name with the commune before issue.

**At issue** (paper §4.5–4.6, [`model/stats/register.json`](../model/stats/register.json)): 17,518 areas carry 12,344 name keys; 2,755 names are shared by 7,929 areas; the fullest shared range is Kaya's (69,550 of 81,000 numbers) and no name needs a qualifier. **Design register counts** ([`model/areas/name-ranges.json`](../model/areas/name-ranges.json), [`model/stats/name-stats.json`](../model/stats/name-stats.json)), measured on the OpenStreetMap villages alone: 7,854 named villages and hamlets carry **6,862 normalised plate names; 707 names repeat, carried by 1,695 villages** (on the full official names: 6,954 names, 646 repeated over 1,542 villages, 491 of them with the very same spelling). The most repeated: Douré and Goghin, 10 villages each (5 digits), Rapadama 9 (its numbered "Rapadama village 1…9", provisionally, §3.6), Tanguin/Tanghin 9 (5 digits), Yargo 7 (4 digits), Watinoma 7 (5 digits). By length, the repeated names are 96 at 3 digits, 563 at 4, 48 at 5. **The largest shared range is still Barogo**: two villages (Saaba 17,090 compounds, Loumbila 415) take 35,010 numbers of a 5-digit range (10000–45009). **No name needs more than 5 digits**, so no name needs a qualifier. Four single villages are too large for 5 digits on their own (Boassa 83,860 compounds, Tabtenga 62,310, Kamboincé 49,970, Yagma 43,931, all non-loti or attached villages of Ouagadougou) and are split by named quartiers or secteurs before issue, as before.

**Qualifiers, when a name does not fit.** If the villages of one name ever need more than 5 digits together, the name keeps its bare form for the blocks that fit in register order, and each other village takes **its commune as the qualifier**, written with a hyphen the way official names already are (Tanghin-Dassouri, Ramongo-Tanguin, Karangasso-Vigué): "Yargo-Kaya". The choice is made once per name and listed in `name-ranges.json`; the qualified name is a name of its own with its own range. List today: **none** for villages. A quartier area made by splitting a large village whose name is a common quarter word (Natenga, Nayiri, Tanghin, Zongo...) takes the village as qualifier ("Boassa-Zongo"); a qualified name keeps to the plate limit of §3.6, and where it cannot, the commune chooses.

**Secteurs (considered, not issued): the town word would be part of the code.** Every urban commune numbers its secteurs from 1, so "Secteur 15 · 48 217" is in Ouagadougou, Bobo-Dioulasso, Ouahigouya and more. A shared "Secteur 1" range cannot fit 5 digits: an average Ouagadougou secteur alone needs 22,420 numbers, and outside Ouagadougou and Bobo-Dioulasso another 183 communes hold about 1.25 million compounds around their town nodes, each town with its own secteur 1. So the **town word is part of the code by rule**: "Secteur 15 Ouaga · 48 217", "Secteur 15 Bobo · 48 217" (two different compounds). "Secteur" is the generic word the secteur number already carries; the town word is the plate name of the secteur code and follows the same limit (§3.6). It is the commune name, with three documented short forms people use everywhere: **Ouaga** (Ouagadougou: "the city's name is often shortened to Ouaga", Wikipedia), **Bobo** (Bobo-Dioulasso: "Bobo is also a shortened name of … Bobo-Dioulasso", Wikipedia, *Bobo people*), **Fada** (Fada N'Gourma: "les colonisateurs l'appelèrent « Fada »", Wikipédia); the full names are aliases ([SOURCES.md](../SOURCES.md)). Three names are carried by two communes each and take the province: Boussouma-Boulgou, Boussouma-Sanmatenga, Namissiguima-Sanmatenga, Namissiguima-Yatenga, Thiou-Boulkiemdé, Thiou-Yatenga; all six are over the plate limit and go to the communes (§3.6). Within a secteur, numbers keep the secteur's own range (5 digits in Ouagadougou).

**The check digit binds name, number and area.** For a village the Damm digit is computed over the name's frozen national id (5 digits), the postcode, the kind, the village index and the number; for a secteur over the postcode (the town word), the secteur and the number. A machine code whose number is not in that village's block is invalid, and a remembered code written with its check ("Bissiga 16 870-9") is refused if the name or the number was mistyped, so a typo cannot land silently in another Bissiga.

**Stability.** Block allocation is **frozen at issue**: a name's blocks are never renumbered or moved. A new village with an existing name gets a new block from the name's spare space (upward from the end of the last block); a village whose block fills gets an extension block the same way; when the spare is used up, the new village takes the commune qualifier. A renamed village keeps its block under its old key, and the new name becomes an alias.

### 3.6 Short plate names

Names taken straight from the map can be too long to remember, say or paint: "Bamguel Palol Tchoukoungol 41 17". Every code area therefore has two names:

- the **official name** (map or INSD list, later the commune's), printed in small type on cards and plates for context, never required;
- the **plate name**, the one in the code: **at most 12 characters** (an accented letter, a space, a hyphen or an apostrophe count one) and **at most 2 words** (de, du, des, la, le, l', and Tamasheq *n* in "Ti-n-Bassata" do not count; a hyphen separates words: "Douré-Centre" is 2 words). No digit.

The plate name is derived by one rule ([`engine/reference/plate_names.py`](../engine/reference/plate_names.py), configured for Burkina in [`tools/name-ranges.py`](../tools/name-ranges.py)), in this order:

1. a **documented short form** people already say, with its source (the town words Ouaga, Bobo, Fada; no village short form is documented);
2. **cleaning**: text in brackets ("Poessé (Kwessé)", "Gambo (moulin)"), text after a slash ("Koalou/Kourou"), and generic words are dropped: "Q" (quartier) and "Quartier", "Lieu-dit", "Village de", "Cité", "Lotissement", "Zone", "Secteur", "Hameau", "Campement";
3. if the cleaned name fits, it is the plate name;
4. otherwise the **most distinctive run of whole words** that fits, preferring the specific end of the name: "Soussougou Yamako" → **Yamako**, "Ouro Tambella" → **Tambella** (Fulfuldé *wuro*, camp), "Debere Boulga" → **Boulga**; "Saint" may become "St" ("Saint-Camille" → **St-Camille**; typing the full form still decodes). A word is never cut.

Burkina Faso's own word lists add three rules:

- **Qualifiers are never dropped automatically.** Ethnic and status words that tell a hamlet from its parent village (Peulh, Foulbé, Mossi, Silmi-Mossi, Rimaïbé, Yarcé, Gourmantché, Bella, Traditionnel, Nouveau, Centre, Mooré *Yiri*, *Tenga*, *Naba*), numbers ("Rapadama village 4", "Daribiti n°1") and the second part of a hyphenated name ("Bayandi-Nabyiri", "Baskoudré-Peulh") go to the commune: dropping them would give the hamlet its parent's name.
- **No short form equal to a well-known place**: a commune, province or region name, or a big city of the region (Ouagadougou, Bamako, Niamey, Abidjan, Accra, Lomé…); a short form equal to the area's own commune ("Base de Vie Mine de Kalsaka" → "Kalsaka") or to another place of the same commune ("Gambo (moulin)" next to "Gambo") also goes to the commune.
- Where the rule is not clear, the area is flagged **`needsCouncilChoice`** with up to three candidates; the first is used **provisionally** and the codes are issued under it, so that no home waits for a naming decision. The commune may choose once; the provisional name stays an alias. A name with no fitting candidate (one word over 12 letters such as "Diakoumafindougou", or a name with digits such as the "VK6" and "b16" plots of the irrigated valleys) takes its commune's name provisionally (SPEC 2.5).

Plate names, not official names, carry the national ranges (§3.5): names that become equal only after shortening ("Debere Boulga" in Arbinda and "Boulga" in Pensa) share one range and decode to different places by their blocks. An official name that maps to one plate name only is an **alias**: "Soussougou Yamako 100" decodes as "Yamako 100". An alias that two plate names would claim, or that is itself another area's plate name, is dropped and listed (`droppedAliases` in `name-ranges.json`; one, "Dougoumato-II").

**Counts (design register, [`model/stats/name-stats.json`](../model/stats/name-stats.json))**, out of 7,854 named villages and hamlets:

| | Villages |
|---|---|
| Official name over 12 characters | 474 |
| Official name over 2 words | 58 |
| Plate name = official name | 7,277 |
| Shortened automatically: cleaned / abbreviated / distinctive | 19 / 1 / 144 |
| Flagged `needsCouncilChoice` (provisional plate name) | 413 |
| of which still over the limit provisionally | 189 (78 of them names with digits) |
| Official names kept as aliases | 377 |

| Code length (villages) | 3 digits | 4 digits | 5 digits |
|---|---|---|---|
| Full official names | 3,442 | 4,114 | 232 |
| Plate names | 3,386 | 4,137 | 265 |

Repeated names: 646 names over 1,542 villages before, 707 over 1,695 after; the largest shared range is still Barogo (35,010 numbers). The longest remembered village code among names not flagged is 19 characters ("Dayagrétenga 20 799"); with the provisional names of flagged areas it is 23 ("Diakoumafindougou 19 29"), until the commune chooses a shorter name.

**Town words** (kept for secteur aliases). 329 commune names fit as they are; Ouaga, Bobo and Fada are the documented short forms. 18 are flagged for the commune: Tanguen-Dassouri (provisionally "Dassouri"), Ourgou-Manega ("Manega"), Karangasso-Vigué ("Vigue"), Karangasso-Sambla ("Sambla"), Boussou-Koula ("Koula"); and 13 with no candidate, kept provisionally: the six province-qualified names (Boussouma, Namissiguima, Thiou: the bare name is shared and the province alone would name a province), Bouroum-Bouroum (Bouroum is another commune), and six single words over 12 letters (Gomboussougou, Nebielianayou, Niankorodougou, Soubakaniedougou, Tankougounadie, Tensobentenga). The longest secteur form with a town word that fits would be "Secteur 55 Bartiebougou · 99 999".

## 4. Criterion 2: the compound, not the footprint

In Burkina the place you find is the **cour**: a concession, walled or not, with one entrance. Measured in Ouagadougou (commune, 550.7 km²):

| Measure | Value |
|---|---|
| Structures (footprints) | 1,129,524 (OpenStreetMap 319,329; Google/Microsoft 810,195) |
| Compounds after grouping (design rules) | **616,565** (0.546 per structure) |
| Structures per compound | 1: 405,817 · 2: 115,027 · 3–5: 70,788 · 6–10: 18,220 · 11+: 6,713 |
| Footprint m² (p25 / median / p75 / p90) | 17.5 / 28.0 / 52.4 / 105.1 |
| Size bands | <10 m²: 19,676 · 10–30: 586,578 · 30–80: 356,493 · 80–200: 139,088 · 200–1000: 26,869 · >1000: 820 |
| Mapped enclosures (OSM walls/fences) | 4,449 from 8,947 barrier ways; median 428 m² (p25 274, p75 1,165): the size of a lotissement plot |
| Mapped gates / entrances | 969 / 220 |

Half the structures are under 28 m²: rooms, kitchens, round huts, latrines, shops. Coding each of them would give a family five codes and no gate. So the registry **groups structures into compounds first**, then numbers compounds.

### 4.1 Grouping rules (parameters for Burkina Faso)

In order, each with a confidence:

1. **Mapped enclosure** (0.85): structures whose centre is inside one closed OSM wall, fence or hedge of at most 6,000 m² belong together. Larger walled areas with many compounds are estates, schools or camps: an outer level (estate gate → compound gate).
2. **Annex** (0.60): a structure under 25 m² joins the nearest structure of 25 m² or more within 8 m (kitchens, stores, latrines, the guardian's room). 8 m, more than the 5–6 m used in coastal capitals, because Burkinabè yards are wider.
3. **Hut cluster** (0.50): structures under 40 m² within 3 m of each other chain into one compound, at most 25 structures. This is the Mossi *yiri*/*zaka* rule: round huts around a yard, often without a wall, in villages and in non-loti zones.
4. **Single** (0.40): what is left is a compound of one structure until people say otherwise.

In Ouagadougou this gave: compounds formed by enclosure 768, by annex 96,733 (+92,205 hosts), by hut cluster 21,253, single 405,606. Wall mapping is the weakest input (768 compounds); the biggest gains will come from people confirming "these buildings are one home" and "this is the gate".

Reverse cases:

- **Cours communes and célibatoriums** (rows of rented rooms around one yard): one compound, one gate, many households. The compound is marked *multi-household*; households are never listed.
- **Immeubles** (R+n): one compound; flats are not coded or published (an occupant may add "appartement 4" as free text in their own shares).
- **Shops in the front wall** (boutiques facing the street with their own doors): extra **entrances** of the compound (`/2`, `/3`), or their own compound if held separately (a business can claim it).
- **Cités and lotissements behind one gate** (e.g. "1200 Logements", Ouaga 2000 compounds, camps): estate gate → compound gate; navigation ends at the estate gate when the inside roads are private.

Regrouping never changes an issued code: if two compounds turn out to be one home, the older code survives and the other becomes an alias; if one splits, the larger part keeps the code.

### 4.2 Compound profile

Use class (one-household, multi-household, mixed, commercial, institutional, industrial), plot area (enclosure or outline), structure count, total floor area, gates and entrances, cross-references (La Poste zone, street address, section/îlot/parcelle), confidence and last-confirmed date. Ouagadougou (design rules): one-household 416,901; multi-household 104,692; small structures only, unclassified 83,078; commercial 5,429; industrial 3,705; institutional 2,307; mixed 375; multi-storey residential 78. Compound floor area: median 73 m² (p90 217.5).

## 5. Building profile (each structure)

| Attribute | How it is set | Source recorded |
|---|---|---|
| Use class | taxonomy below, from evidence in this order: OSM `building=*` tag (0.85), OSM amenity/shop/office on the building (0.75), N-Ways places inside the footprint (0.65), OSM landuse (0.50), size (0.30–0.40), default residential (0.45–0.55); +0.05 per agreeing source | per attribute |
| Footprint, perimeter | geodesic area and perimeter of the polygon | OSM / Google / Microsoft |
| Height | OSM `height` where mapped; the Google/Microsoft height is a rendering filler and is never used | per attribute |
| Floors | OSM `building:levels`, else max(1, round(OSM height / 3)); otherwise unknown | 523 buildings nationally have a known floor count |
| Floor area | footprint × floors where floors are known, else the footprint | derived |
| Entrances, name, status | people and businesses; names only for businesses and public buildings | door confirmations, residents, businesses |

**Taxonomy for Burkina** (classes → local forms):

- *residential*: cour/concession urbaine; **yiri/zaka** (rural family compound of round huts, case ronde); cour commune and **célibatorium** (rows of rental rooms); villa; immeuble R+n; habitat spontané (non-loti); *annex*: cuisine, douche/latrine, magasin, **grenier** (granary), poulailler.
- *commercial*: boutique, kiosque, marché (yaar), magasin/entrepôt, station-service, maquis.
- *government*: mairie, préfecture, poste, commissariat, gendarmerie, caserne.
- *education*: école, CEG, lycée, université, école coranique.
- *health*: CSPS, CMA, CHR/CHU, pharmacie, clinique.
- *religious*: mosquée, église, temple.
- *industrial*: usine, atelier, entrepôt industriel.
- *hospitality*: hôtel, auberge.
- *transport*: gare routière, parking, garage.
- *agricultural*: grenier, parc à bétail, hangar agricole.
- *under construction* (chantier), *ruin*, *unknown*.

In practice, **97.7% of Ouagadougou's structures are "residential" by default** (1,103,290 of 1,129,524 had no other evidence); mean class confidence 0.53. OSM tags, POIs and landuse moved only about 2%. The profile therefore shows its confidence and its source, and improves as people and partners confirm (a shop owner claiming the shop, couriers marking "delivered to the boutique", schools and health centres from the ministries' lists).

Privacy: residential structures never carry occupant data (no names, no household size published; "multi-household" is shown only as a class).

## 6. Code areas and numbering

- **Code area** = a named place people use: a **village, hamlet or locality**, and in towns a **named quarter** (V001–V999 per commune), from OpenStreetMap and GeoNames ([`model/areas/register.json`](../model/areas/register.json): 17,518 areas in 351 communes). A home takes the nearest named place of its commune. Secteur codes (S01–S99) are reserved: the secteur maps of the communes (2009) and the PASIU database are not public. INSD's village list, once obtained, adds official names as aliases.
- An area too large for its range (compounds × 2 > range) was **split by named quarters before issue**; with the GeoNames quarters none was.
- **Numbers**: fixed length per **name** (3, 4 or 5 digits, no leading zero); an area uses its frozen block in its name's national range (§3.5). Compounds are ordered along a Hilbert curve over the area, so neighbours have close numbers; numbers are spread with a step so free numbers remain between neighbours for infill; the top third of the range (or of the block) is a reserve for growth at the edges.
- **Never reused**: demolished → retired; split → larger part keeps it; merged → oldest survives.
- **Renames and renumbering** (secteurs in 2009, regions in 2025) change only the alias table; a renamed village keeps its block in its old name's range.

The machine prefix is the commune's La Poste postcode (10000 for Ouagadougou), so every N-Ways code also carries the official postal code; the La Poste delivery zone (10010, 10040...) and the agency code are stored as attributes for mail.

## 7. Spot codes (anywhere, without a building)

Burkina spans UTM zones 30 and 31, so no single UTM zone fits. Each commune gets a frozen **local metric frame**: origin at the commune's south-west corner floored to 0.01°, reference latitude at its centre; a point is coded by metres east and north in 10 m units, 4 digits each (`E1809 N1351`): a grid reference that can be read on a paper map with a printed commune grid. 346 communes fit in 99.99 km both ways; four need 5 digits on one axis (Matiakoali 128.8 km north–south, Tin-Akoff 125.7 km east–west, Ouo 116.0 km, Pama 115.7 km). The frames are in [`model/units/frames.json`](../model/units/frames.json) and are computed once, then frozen.

10 m is enough: a spot code marks a field, a market stall row or a point on a track; the compound code takes over once there is a compound.

The commune outlines are simplified (about 40 m) and do not tile the country exactly, so 9,235 issued entrances (0.11 %, in 110 communes) fall in no outline: in a gap between two outlines, or just over a border line (never more than 300 m outside the national border, which decides: SPEC 1b). Each still gets a spot code, without moving any frame ([SPEC 5.1](../engine/SPEC.md)): the commune with the nearest outline within 10 km whose frame holds the point gives it its cell (9,227 entrances, decoded within 7.07 m); if no frame holds it, the commune with the nearest outline within 10 km whose frame lies within 3,000 m gives it the frame's nearest edge cell (8 entrances, at most 140 m from the cell centre; the registry keeps the exact entrance). The 10 km covers the farthest issued entrance (8.57 km from an outline) and the 3,000 m the farthest edge cell (140 m). Distances to an outline scale longitude by a fixed polynomial cosine of the latitude, so every port chooses the same commune; ties go to the lower postcode. Preferring a frame that holds the point over a nearer outline keeps the code exact to its cell; the commune it names is then a frame, which can differ from the compound code's commune. Decoding uses the frame of the commune the code names.

## 8. "Ajouter ma maison" (new homes)

1. **Stand at the gate**: GPS averaged over a few seconds, one photo of the gate → the gate's spot and entrance.
2. **Outline the plot**, one of:
   - tap the corners on satellite imagery;
   - **walk the boundary inside the wall** with the camera: ARKit/ARCore world tracking gives the shape to centimetres relative to the start, anchored by GPS averaged along the walk and checked against imagery and nearby footprints (plain phone GPS, 3–10 m, is too rough for a plot of 15 × 20 m);
   - **import the survey plan or lotissement parcel**: type or photograph the beacon coordinates of the plan (bornage). Plans are in the "référentiel national" (Décret 2012-444); the datum is not named in the text and must be confirmed with IGB before imports are accepted automatically (until then, imports must state WGS84 / UTM 30N or 31N and are checked against imagery).
3. **Describe it**: households (count only, never names), structures, floors, use.
4. **Provisional code at once**: the next reserved number in that area's numbering, between its Hilbert neighbours, so it can be painted on the gate today.
5. **Confirmed** when deliveries or arrivals reach the gate, no neighbour disputes it, or new imagery shows the buildings.

Safeguards: **an N-Ways address is not a land title** (said in the flow and on the certificate page: rights come only from the PUH, the attestation d'attribution or the titre foncier, and plans only from the cadastre or a géomètre-expert; Décret 2012-444 sets 7 cm for boundary markers); overlaps with existing compounds or parcels are flagged, not issued; checks: gate on the outline, plausible size, closed loop, GPS and AR agree; privacy: only the outline and the gate photo are kept; offline: the spot code appears at once, the compound code comes from the registry at the next connection.

## 9. Safety and privacy in Burkina

- Codes describe places, never people. No resident names, no household size, no ID numbers.
- **Security.** The UK FCDO advises against all travel to Burkina Faso (10 December 2025); about 2 million people were displaced by 2023. The registry publishes places, never people: every code with its entrance and building profile, and no names, household sizes, gate photos or outlines drawn by residents. Sites for displaced people are never published.
- CIL: declaration of the registry processing under Loi 001-2021; the CIL's deliberation on geolocation is to be read and followed (its text could not be obtained).

## 10. Governance

N-Ways runs the Burkina registry as an open public good that it can hand over. First partners: **La Poste Burkina Faso** (owner of the postcode: confirm the table, Komsilga and Cinkansé, reuse terms), **Commune de Ouagadougou** and **Commune de Bobo-Dioulasso** and the **AMB**/PASIU (secteur maps, painted addresses), **IGB** (datum, CORS), **DGI cadastre** (section/îlot/parcelle cross-references), **INSD** (village list and codes), **ANPTIC**, **CIL**, the **Brigade nationale des sapeurs-pompiers** (18) and police (17), couriers. See [GOVERNANCE.md](../GOVERNANCE.md).

## 11. Field validation and memorability study

1. Request the communal address data (Ouagadougou, Bobo-Dioulasso, AMB/PASIU) and the readdressed-area boundaries; obtain secteur maps and INSD's village list as aliases; confirm the postcode table with La Poste.
2. Pilot in two Ouagadougou secteurs that the commune has not readdressed (one loti, one non-loti) and three villages of one rural commune near Ouagadougou; in one readdressed arrondissement, test the import and display of official addresses.
3. **Memorability study**: 300 residents per site, half shown the code once on a plate, half on the app; recall asked after 1 day, 1 week, 1 month; measure exact recall, digit errors, transpositions; by language (French, Mooré, Dioula), age and reading ability; compare 3, 4 and 5 digits. Targets: ≥ 80% exact recall after one week for 4 digits, ≥ 70% for 5.
4. Couriers measure first-time arrival with a code against without.
5. Confirm codes commune by commune as residents, couriers and services use them (§9).

## 12. Limits

- Compound grouping is heuristic (confidence 0.4–0.85); walls are poorly mapped.
- Use classes are mostly defaults today.
- Secteur polygons are not public; secteur forms are refused until a commune shares its map.
- Name ranges were frozen at first issue, with their name ids; new places with an existing name take blocks from the name's spare.
- 945 areas carry a provisional plate name until their commune chooses (§3.6); their codes are issued and their numbers never change.
- The extent of the readdressed arrondissements and access to the communal address data are not yet known; meanwhile the official street within 30 m is shown first in Ouagadougou and Bobo-Dioulasso.
- 55 commune–postcode matches are by spelling and must be checked with La Poste; Komsilga has no code in the table.
- Floor counts are known for few buildings (523 nationally); imagery-derived heights are not used.
