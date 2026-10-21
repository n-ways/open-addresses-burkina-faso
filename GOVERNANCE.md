# Governance — N-Ways addresses, Burkina Faso

Status: issued on 20 October 2026 (8,369,987 codes); the repository and the registry are public.

## Who decides

- **Maintainers.** The N-Ways addressing team for Burkina Faso keeps this repository. Changes to the engine, the format or the keys need two maintainers' approval and a green test run. Any change to `engine/reference/test_vectors.json` or `vectors.json` must be explained.
- **Codes are never decided by hand.** Compounds, numbers, profiles and gates are settled by the engine's rules and by consensus from residents, couriers and visitors, the same way N-Ways settles map corrections (SPEC §9). No item waits in a queue for a person to approve it: rules that people can check replace decisions nobody can.
- **Official data first.** Where a Burkinabè authority publishes addresses, they are imported and shown first, exactly as written: the street codes and door numbers of the communes of Ouagadougou and Bobo-Dioulasso (AMB, PASIU) and any successor. Every home also keeps its N-Ways code, shown beside the official address, so that one form of address works in every commune and the official one always comes first. N-Ways never edits official records; it reports a mismatch seen on the ground to the commune.
- **La Poste's postcode** is the first part of every machine code; changes to the postcode table follow La Poste. Komsilga uses 10990, outside La Poste's series, until La Poste gives it a code.

## Stability promises

1. An issued code never moves and is never reused.
2. Renames, secteur maps and re-districting change only the alias table.
3. Engine changes may not change an issued code; a format change needs published vectors and a migration in which every old code still resolves.
4. Retired codes stay listed forever.

## One issuer

Codes are issued by one issuer for the whole country: N-WAYS LIMITED today, or the body the State designates. The registry server in `server/` can issue, but a deployment issues only when the State or N-WAYS LIMITED has designated it; every other deployment runs read-only (no `ISSUE_KEYS`). Numbers are drawn from shared national ranges, so two issuers working from the same registry would hand the same number to two different homes. A designated issuer publishes its new codes and blocks in this registry, and every other deployment imports them (server/README.md).

## Safety

The registry publishes every code. It carries places, never people: no names, telephone numbers, household sizes, gate photos or outlines drawn by residents, and no sites for displaced people. The UK FCDO advises against all travel to Burkina Faso, Ouagadougou included (advice of 10 December 2025); the area table marks the communes it covers (`alert_zone`) as context for services that plan visits there. Anyone who believes a published record puts a person at risk can ask for it to be reviewed (SECURITY.md); such a request is answered within days.

## Disputes

- **Grouping or gate.** A neighbour's dispute over a grouping or a gate suspends confirmation of that compound until the evidence agrees. It does not delete the code.
- **Land.** A code is an address, not a land title or a PUH. Land disputes belong to the courts and the DGI, never to this registry. A disputed outline is hidden from the public map until resolved.

## Hand-over

The repository is built to be handed over, if the State designates a body: for example La Poste Burkina Faso, the ministry in charge of urbanism, the communes, the IGB or ANPTIC. A hand-over includes the registry, the alias table, the engine, the registry server, the issuing keys and the mapping to the official system. N-Ways would then follow that body's rules.

## Partners to approach first

1. The communes of Ouagadougou and Bobo-Dioulasso, the AMB and PASIU: street codes, door numbers, readdressed areas and secteur maps, through a data-sharing agreement.
2. La Poste Burkina Faso: the postcode table (55 spelling matches, Komsilga, Cinkansé) and its reuse terms.
3. IGB: national datum, GNSS-CORS, base maps.
4. DGI, Direction du cadastre (SyC@D): section, îlot and parcelle cross-references.
5. INSD: the official village list and secteur boundaries.
6. ANPTIC: government digital services.
7. CIL: prior declaration under Loi 001-2021/AN; its rules on geolocation.
8. Emergency services: police 17, sapeurs-pompiers 18, health services.

## Privacy duties

- Declare the processing to the CIL (Loi 001-2021/AN).
- Never store residents' names, phone numbers or identity numbers.
- Honour private-gate requests.

## Naming

Always "N-Ways address" / "adresse N-Ways". Never "code postal", "official address" or "adresse officielle".
