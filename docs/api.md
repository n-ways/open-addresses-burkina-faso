# The registry server API

Every endpoint of [`server/`](../server/README.md), with a real request and the response the server gave on the complete registry of Burkina Faso (8,369,987 codes, export of 2026-10-21T20:22:57Z). Long lists are shortened to their first three items. The machine-readable description is [`server/openapi.yaml`](../server/openapi.yaml).

Every response is JSON (`application/json; charset=utf-8`) with stable field names. An error is always

```json
{"error": {"code": "check_digit", "message": "The check digit does not match: a digit is wrong or two are swapped."}}
```

with the HTTP status that fits: 400 for a request that cannot be right (a bad parameter, a wrong check digit), 401 for a missing or wrong key, 403 on a read-only deployment, 404 for something that does not exist, 405 for a wrong method, 409 for a conflict (the building already has a code, the code is retired), 410 for a retired code looked up, 413 for a body over 64 kB, 422 for a valid request the rules refuse, 429 for the daily limit, 500 for a fault of the server. Error codes:

| Code | Status | Meaning |
|---|---|---|
| `bad_request` | 400 | a parameter or the body is missing or malformed |
| `bad_code` | 400 | not a machine code or spot code of Burkina Faso |
| `bad_query` | 400 | the query is none of the forms /v1/find accepts |
| `check_digit` | 400 | the check digit does not match |
| `unknown_area` | 400 | a machine code names an area that does not exist |
| `not_in_blocks` | 400 / 404 | the number is in none of the area's blocks |
| `secteur` | 400 | a secteur form: not issued |
| `unauthorized` | 401 | no key, or not one of the deployment's keys |
| `read_only` | 403 | the deployment issues nothing |
| `not_found` | 404 | no such endpoint, zone, area, spot or code to add a door to |
| `not_issued` | 404 | a valid code that no compound has |
| `unknown_name` | 404 | no area has that name |
| `wrong_digits` | 404 | the number has the wrong length for that name |
| `outside` | 404 / 422 | the point is outside Burkina Faso: more than 300 m outside the national border (`engine/SPEC.md` §1b), or in no commune outline and no commune within 10 km gives it a spot code |
| `method_not_allowed` | 405 | wrong method for the path |
| `exists` | 409 | the building already has a code (`existing` holds its card) |
| `area_full` | 409 | the name's range is used up |
| `retired` | 409 / 410 | the code is retired |
| `too_large` | 413 | the body is over 64 kB |
| `bad_outline` | 422 | the outline is under 6 m² or over 2 ha |
| `too_far` | 422 | a door or a new entrance more than 80 m away |
| `rate_limited` | 429 | the key's daily limit is reached |
| `internal` | 500 | a fault of the server (logged) |

Reads need no key. `POST` and `PATCH` need `Authorization: Bearer <key>`, one of the deployment's `ISSUE_KEYS`.

## GET /v1/health

Liveness and the registry this deployment serves. Used by the container health check.

```sh
curl -s 'http://localhost:8080/v1/health'
```

HTTP 200

```json
{
  "status": "ok",
  "country": "BF",
  "codes": 8369987,
  "registryExported": "2026-10-21T20:22:57Z",
  "changedSinceImport": false,
  "issuing": true
}
```

## GET /v1/info

The country, the counts, the licences and credit line, the engine and the example forms.

```sh
curl -s 'http://localhost:8080/v1/info'
```

HTTP 200

```json
{
  "country": "BF",
  "name": "Burkina Faso",
  "api": "1",
  "engine": "internal/addressing/bf (SPEC v1.0)",
  "spec": "SPEC v1.0",
  "registryExported": "2026-10-21T20:22:57Z",
  "importedAt": "2026-10-21T20:49:57Z",
  "counts": {
    "codes": 8369987,
    "byStatus": {
      "provisional": 8369987
    },
    "zones": 351,
    "communes": 351,
    "areas": 17518,
    "numberedAreas": 17319,
    "names": 12344
  },
  "zones": [
    {
      "key": "10000",
      "name": "Ouagadougou",
      "codes": 755775
    },
    {
      "key": "10200",
      "name": "Saaba",
      "codes": 125626
    },
    {
      "key": "10250",
      "name": "Tanguen-Dassouri",
      "codes": 48387
    },
    "… 348 more"
  ],
  "licences": {
    "data": "ODbL-1.0",
    "code": "Apache-2.0",
    "documents": "CC-BY-4.0"
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)",
  "creditUrl": "https://github.com/n-ways/open-addresses-burkina-faso",
  "issuing": true,
  "issuePerDay": 5,
  "forms": {
    "remembered": "Koulouba 17 76",
    "machine": "BF-10000-V064-1776-9",
    "spot": "BF-10000 E1809 N1351",
    "official": "Rue du Baobab, Bobo-Dioulasso"
  }
}
```

## GET /v1/codes/{machine}

The full card of an issued code: every registry column by name (`registry`), the remembered, home and spoken forms, the spot code and Plus Code, the area and the commune. A wrong check digit is refused, never corrected; a valid code nobody has yet is 404 `not_issued`.

```sh
curl -s 'http://localhost:8080/v1/codes/BF-10000-V064-1776-9'
```

HTTP 200

```json
{
  "machine": "BF-10000-V064-1776-9",
  "remembered": "Koulouba 17 76",
  "home": "Koulouba 1776",
  "spoken": "Koulouba, 17 76",
  "spokenFr": "Koulouba, dix-sept soixante-seize",
  "plateName": "Koulouba",
  "officialName": "Koulouba",
  "number": 1776,
  "check": 9,
  "status": "provisional",
  "issued": "bulk",
  "issuedAt": "2026-10-20T22:50:53Z",
  "officialAddress": "Avenue Uemoa, Ouagadougou",
  "place": "Ouagadougou",
  "entrance": {
    "lat": 12.3641615,
    "lng": -1.5166371,
    "kind": "centre"
  },
  "spotCode": "BF-10000 E1885 N1262",
  "plusCode": "7C4W9F7M+M89",
  "area": {
    "key": "10000-064",
    "id": 64,
    "index": "064",
    "plateName": "Koulouba",
    "officialName": "Koulouba",
    "nameProvisional": false,
    "commune": {
      "postcode": "10000",
      "name": "Ouagadougou"
    },
    "nameKey": "KULUBA",
    "nameId": 5572,
    "digits": 4,
    "blocks": [
      [
        1000,
        6369
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 2683,
    "travelAdvisory": true,
    "point": {
      "lat": 12.36702,
      "lng": -1.51111
    },
    "frame": [
      -1.519638,
      12.357614,
      -1.502982,
      12.379197
    ]
  },
  "zone": {
    "key": "10000",
    "name": "Ouagadougou"
  },
  "building": {
    "class": "hospitality",
    "use": "mixed",
    "kind": "compound",
    "structures": 3,
    "floorAreaM2": 1216.9,
    "rule": "annex",
    "estate": null
  },
  "registry": {
    "machine": "BF-10000-V064-1776-9",
    "home": "Koulouba 1776",
    "written": "Koulouba 17 76",
    "zone": "10000-064",
    "official_name": "Koulouba",
    "number": "1776",
    "check": "9",
    "status": "provisional",
    "issued": "bulk",
    "issued_at": "2026-10-20T22:50:53Z",
    "entrance_lat": "12.3641615",
    "entrance_lng": "-1.5166371",
    "entrance_kind": "centre",
    "spot_code": "BF-10000 E1885 N1262",
    "official_address": "Avenue Uemoa, Ouagadougou",
    "class": "hospitality",
    "use": "mixed",
    "kind": "compound",
    "structures": "3",
    "floor_area_m2": "1216.9",
    "rule": "annex",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s 'http://localhost:8080/v1/codes/BF-10000-V064-1776-8'
```

HTTP 400

```json
{
  "error": {
    "code": "check_digit",
    "message": "The check digit does not match: a digit is wrong or two are swapped."
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/codes/BF-10000-V064-3683-5'
```

HTTP 404

```json
{
  "error": {
    "code": "not_issued",
    "message": "No compound has Koulouba 36 83 yet (BF-10000-V064-3683-5): the number is in the range of Koulouba, Ouagadougou."
  }
}
```

## GET /v1/find?q=

Decodes whatever a person or a system typed: a remembered form in any spacing, case or accents ("koulouba 17 76", "Koulouba 1776", "Diourmanko 100" for Diurmanko), an official name that is an alias of a plate name, a machine form (with or without its check digit), a spot code, or an official address. `kind` says which one matched. A wrong check digit is refused (400 `check_digit`); a secteur form is refused (400 `secteur`): no secteur map is public.

```sh
curl -s 'http://localhost:8080/v1/find?q=koulouba%2017%2076'
```

HTTP 200

```json
{
  "query": "koulouba 17 76",
  "kind": "remembered",
  "count": 1,
  "results": [
    {
      "machine": "BF-10000-V064-1776-9",
      "remembered": "Koulouba 17 76",
      "home": "Koulouba 1776",
      "spoken": "Koulouba, 17 76",
      "spokenFr": "Koulouba, dix-sept soixante-seize",
      "plateName": "Koulouba",
      "officialName": "Koulouba",
      "number": 1776,
      "check": 9,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T22:50:53Z",
      "officialAddress": "Avenue Uemoa, Ouagadougou",
      "place": "Ouagadougou",
      "entrance": {
        "lat": 12.3641615,
        "lng": -1.5166371,
        "kind": "centre"
      },
      "spotCode": "BF-10000 E1885 N1262",
      "plusCode": "7C4W9F7M+M89",
      "area": {
        "key": "10000-064",
        "id": 64,
        "index": "064",
        "plateName": "Koulouba",
        "officialName": "Koulouba",
        "nameProvisional": false,
        "commune": {
          "postcode": "10000",
          "name": "Ouagadougou"
        },
        "nameKey": "KULUBA",
        "nameId": 5572,
        "digits": 4,
        "blocks": [
          [
            1000,
            6369
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 2683,
        "travelAdvisory": true,
        "point": {
          "lat": 12.36702,
          "lng": -1.51111
        },
        "frame": [
          -1.519638,
          12.357614,
          -1.502982,
          12.379197
        ]
      },
      "zone": {
        "key": "10000",
        "name": "Ouagadougou"
      },
      "building": {
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": 3,
        "floorAreaM2": 1216.9,
        "rule": "annex",
        "estate": null
      },
      "registry": {
        "machine": "BF-10000-V064-1776-9",
        "home": "Koulouba 1776",
        "written": "Koulouba 17 76",
        "zone": "10000-064",
        "official_name": "Koulouba",
        "number": "1776",
        "check": "9",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T22:50:53Z",
        "entrance_lat": "12.3641615",
        "entrance_lng": "-1.5166371",
        "entrance_kind": "centre",
        "spot_code": "BF-10000 E1885 N1262",
        "official_address": "Avenue Uemoa, Ouagadougou",
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": "3",
        "floor_area_m2": "1216.9",
        "rule": "annex",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Bobo%2026%20206'
```

HTTP 200

```json
{
  "query": "Bobo 26 206",
  "kind": "remembered",
  "count": 1,
  "results": [
    {
      "machine": "BF-90000-V006-26206-1",
      "remembered": "Bobo 26 206",
      "home": "Bobo 26206",
      "spoken": "Bobo, 26 206",
      "spokenFr": "Bobo, vingt-six deux cent six",
      "plateName": "Bobo",
      "officialName": "Bobo-Dioulasso",
      "number": 26206,
      "check": 1,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T23:59:45Z",
      "officialAddress": null,
      "place": "Bobo-Dioulasso",
      "entrance": {
        "lat": 11.1773575,
        "lng": -4.300137,
        "kind": "centre"
      },
      "spotCode": "BF-90000 E3164 N2624",
      "plusCode": "7C3Q5MGX+WWX",
      "area": {
        "key": "90000-006",
        "id": 14517,
        "index": "006",
        "plateName": "Bobo",
        "officialName": "Bobo-Dioulasso",
        "nameProvisional": false,
        "commune": {
          "postcode": "90000",
          "name": "Bobo-Dioulasso"
        },
        "nameKey": "BOBO",
        "nameId": 1093,
        "digits": 5,
        "blocks": [
          [
            10000,
            50019
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 20007,
        "travelAdvisory": true,
        "point": {
          "lat": 11.17658,
          "lng": -4.296144
        },
        "frame": [
          -4.350085,
          11.153252,
          -4.287155,
          11.185857
        ]
      },
      "zone": {
        "key": "90000",
        "name": "Bobo-Dioulasso"
      },
      "building": {
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 434.7,
        "rule": "single",
        "estate": null
      },
      "registry": {
        "machine": "BF-90000-V006-26206-1",
        "home": "Bobo 26206",
        "written": "Bobo 26 206",
        "zone": "90000-006",
        "official_name": "Bobo-Dioulasso",
        "number": "26206",
        "check": "1",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T23:59:45Z",
        "entrance_lat": "11.1773575",
        "entrance_lng": "-4.3001370",
        "entrance_kind": "centre",
        "spot_code": "BF-90000 E3164 N2624",
        "official_address": "",
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "434.7",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=BF-90000-V006-26206-1'
```

HTTP 200

```json
{
  "query": "BF-90000-V006-26206-1",
  "kind": "machine",
  "count": 1,
  "results": [
    {
      "machine": "BF-90000-V006-26206-1",
      "remembered": "Bobo 26 206",
      "home": "Bobo 26206",
      "spoken": "Bobo, 26 206",
      "spokenFr": "Bobo, vingt-six deux cent six",
      "plateName": "Bobo",
      "officialName": "Bobo-Dioulasso",
      "number": 26206,
      "check": 1,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T23:59:45Z",
      "officialAddress": null,
      "place": "Bobo-Dioulasso",
      "entrance": {
        "lat": 11.1773575,
        "lng": -4.300137,
        "kind": "centre"
      },
      "spotCode": "BF-90000 E3164 N2624",
      "plusCode": "7C3Q5MGX+WWX",
      "area": {
        "key": "90000-006",
        "id": 14517,
        "index": "006",
        "plateName": "Bobo",
        "officialName": "Bobo-Dioulasso",
        "nameProvisional": false,
        "commune": {
          "postcode": "90000",
          "name": "Bobo-Dioulasso"
        },
        "nameKey": "BOBO",
        "nameId": 1093,
        "digits": 5,
        "blocks": [
          [
            10000,
            50019
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 20007,
        "travelAdvisory": true,
        "point": {
          "lat": 11.17658,
          "lng": -4.296144
        },
        "frame": [
          -4.350085,
          11.153252,
          -4.287155,
          11.185857
        ]
      },
      "zone": {
        "key": "90000",
        "name": "Bobo-Dioulasso"
      },
      "building": {
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 434.7,
        "rule": "single",
        "estate": null
      },
      "registry": {
        "machine": "BF-90000-V006-26206-1",
        "home": "Bobo 26206",
        "written": "Bobo 26 206",
        "zone": "90000-006",
        "official_name": "Bobo-Dioulasso",
        "number": "26206",
        "check": "1",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T23:59:45Z",
        "entrance_lat": "11.1773575",
        "entrance_lng": "-4.3001370",
        "entrance_kind": "centre",
        "spot_code": "BF-90000 E3164 N2624",
        "official_address": "",
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "434.7",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=BF-10000%20E1885%20N1262'
```

HTTP 200

```json
{
  "query": "BF-10000 E1885 N1262",
  "kind": "spot",
  "point": {
    "lat": 12.3641769,
    "lng": -1.5165912
  },
  "count": 1,
  "results": [
    {
      "machine": "BF-10000-V064-1776-9",
      "remembered": "Koulouba 17 76",
      "home": "Koulouba 1776",
      "spoken": "Koulouba, 17 76",
      "spokenFr": "Koulouba, dix-sept soixante-seize",
      "plateName": "Koulouba",
      "officialName": "Koulouba",
      "number": 1776,
      "check": 9,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T22:50:53Z",
      "officialAddress": "Avenue Uemoa, Ouagadougou",
      "place": "Ouagadougou",
      "entrance": {
        "lat": 12.3641615,
        "lng": -1.5166371,
        "kind": "centre"
      },
      "spotCode": "BF-10000 E1885 N1262",
      "plusCode": "7C4W9F7M+M89",
      "area": {
        "key": "10000-064",
        "id": 64,
        "index": "064",
        "plateName": "Koulouba",
        "officialName": "Koulouba",
        "nameProvisional": false,
        "commune": {
          "postcode": "10000",
          "name": "Ouagadougou"
        },
        "nameKey": "KULUBA",
        "nameId": 5572,
        "digits": 4,
        "blocks": [
          [
            1000,
            6369
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 2683,
        "travelAdvisory": true,
        "point": {
          "lat": 12.36702,
          "lng": -1.51111
        },
        "frame": [
          -1.519638,
          12.357614,
          -1.502982,
          12.379197
        ]
      },
      "zone": {
        "key": "10000",
        "name": "Ouagadougou"
      },
      "building": {
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": 3,
        "floorAreaM2": 1216.9,
        "rule": "annex",
        "estate": null
      },
      "registry": {
        "machine": "BF-10000-V064-1776-9",
        "home": "Koulouba 1776",
        "written": "Koulouba 17 76",
        "zone": "10000-064",
        "official_name": "Koulouba",
        "number": "1776",
        "check": "9",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T22:50:53Z",
        "entrance_lat": "12.3641615",
        "entrance_lng": "-1.5166371",
        "entrance_kind": "centre",
        "spot_code": "BF-10000 E1885 N1262",
        "official_address": "Avenue Uemoa, Ouagadougou",
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": "3",
        "floor_area_m2": "1216.9",
        "rule": "annex",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)",
      "distanceM": 5.3
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Rue%20du%20Baobab%2C%20Bobo-Dioulasso'
```

HTTP 200

```json
{
  "query": "Rue du Baobab, Bobo-Dioulasso",
  "kind": "official",
  "count": 189,
  "more": true,
  "results": [
    {
      "machine": "BF-90000-V004-10846-6",
      "remembered": "Bendougousso 10 846",
      "home": "Bendougousso 10846",
      "spoken": "Bendougousso, 10 846",
      "spokenFr": "Bendougousso, dix huit cent quarante-six",
      "plateName": "Bendougousso",
      "officialName": "Bendougousso",
      "number": 10846,
      "check": 6,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T23:59:24Z",
      "officialAddress": "Rue du Baobab, Bobo-Dioulasso",
      "place": "Bobo-Dioulasso",
      "entrance": {
        "lat": 11.1846871,
        "lng": -4.3220128,
        "kind": "centre"
      },
      "spotCode": "BF-90000 E2926 N2705",
      "plusCode": "7C3Q5MMH+V5H",
      "area": {
        "key": "90000-004",
        "id": 14515,
        "index": "004",
        "plateName": "Bendougousso",
        "officialName": "Bendougousso",
        "nameProvisional": false,
        "commune": {
          "postcode": "90000",
          "name": "Bobo-Dioulasso"
        },
        "nameKey": "BENDUGUSO",
        "nameId": 851,
        "digits": 5,
        "blocks": [
          [
            10000,
            53829
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 21911,
        "travelAdvisory": true,
        "point": {
          "lat": 11.193875,
          "lng": -4.296526
        },
        "frame": [
          -4.355734,
          11.183659,
          -4.28301,
          11.221174
        ]
      },
      "zone": {
        "key": "90000",
        "name": "Bobo-Dioulasso"
      },
      "building": {
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 41.0,
        "rule": "single",
        "estate": null
      },
      "registry": {
        "machine": "BF-90000-V004-10846-6",
        "home": "Bendougousso 10846",
        "written": "Bendougousso 10 846",
        "zone": "90000-004",
        "official_name": "Bendougousso",
        "number": "10846",
        "check": "6",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T23:59:24Z",
        "entrance_lat": "11.1846871",
        "entrance_lng": "-4.3220128",
        "entrance_kind": "centre",
        "spot_code": "BF-90000 E2926 N2705",
        "official_address": "Rue du Baobab, Bobo-Dioulasso",
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "41.0",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    },
    {
      "machine": "BF-90000-V004-10847-7",
      "remembered": "Bendougousso 10 847",
      "home": "Bendougousso 10847",
      "spoken": "Bendougousso, 10 847",
      "spokenFr": "Bendougousso, dix huit cent quarante-sept",
      "plateName": "Bendougousso",
      "officialName": "Bendougousso",
      "number": 10847,
      "check": 7,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T23:59:24Z",
      "officialAddress": "Rue du Baobab, Bobo-Dioulasso",
      "place": "Bobo-Dioulasso",
      "entrance": {
        "lat": 11.1847586,
        "lng": -4.3218117,
        "kind": "centre"
      },
      "spotCode": "BF-90000 E2928 N2706",
      "plusCode": "7C3Q5MMH+W74",
      "area": {
        "key": "90000-004",
        "id": 14515,
        "index": "004",
        "plateName": "Bendougousso",
        "officialName": "Bendougousso",
        "nameProvisional": false,
        "commune": {
          "postcode": "90000",
          "name": "Bobo-Dioulasso"
        },
        "nameKey": "BENDUGUSO",
        "nameId": 851,
        "digits": 5,
        "blocks": [
          [
            10000,
            53829
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 21911,
        "travelAdvisory": true,
        "point": {
          "lat": 11.193875,
          "lng": -4.296526
        },
        "frame": [
          -4.355734,
          11.183659,
          -4.28301,
          11.221174
        ]
      },
      "zone": {
        "key": "90000",
        "name": "Bobo-Dioulasso"
      },
      "building": {
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 30.9,
        "rule": "single",
        "estate": null
      },
      "registry": {
        "machine": "BF-90000-V004-10847-7",
        "home": "Bendougousso 10847",
        "written": "Bendougousso 10 847",
        "zone": "90000-004",
        "official_name": "Bendougousso",
        "number": "10847",
        "check": "7",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T23:59:24Z",
        "entrance_lat": "11.1847586",
        "entrance_lng": "-4.3218117",
        "entrance_kind": "centre",
        "spot_code": "BF-90000 E2928 N2706",
        "official_address": "Rue du Baobab, Bobo-Dioulasso",
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "30.9",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    },
    {
      "machine": "BF-90000-V004-10848-9",
      "remembered": "Bendougousso 10 848",
      "home": "Bendougousso 10848",
      "spoken": "Bendougousso, 10 848",
      "spokenFr": "Bendougousso, dix huit cent quarante-huit",
      "plateName": "Bendougousso",
      "officialName": "Bendougousso",
      "number": 10848,
      "check": 9,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T23:59:24Z",
      "officialAddress": "Rue du Baobab, Bobo-Dioulasso",
      "place": "Bobo-Dioulasso",
      "entrance": {
        "lat": 11.1848213,
        "lng": -4.3216628,
        "kind": "centre"
      },
      "spotCode": "BF-90000 E2929 N2707",
      "plusCode": "7C3Q5MMH+W8G",
      "area": {
        "key": "90000-004",
        "id": 14515,
        "index": "004",
        "plateName": "Bendougousso",
        "officialName": "Bendougousso",
        "nameProvisional": false,
        "commune": {
          "postcode": "90000",
          "name": "Bobo-Dioulasso"
        },
        "nameKey": "BENDUGUSO",
        "nameId": 851,
        "digits": 5,
        "blocks": [
          [
            10000,
            53829
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 21911,
        "travelAdvisory": true,
        "point": {
          "lat": 11.193875,
          "lng": -4.296526
        },
        "frame": [
          -4.355734,
          11.183659,
          -4.28301,
          11.221174
        ]
      },
      "zone": {
        "key": "90000",
        "name": "Bobo-Dioulasso"
      },
      "building": {
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 32.2,
        "rule": "single",
        "estate": null
      },
      "registry": {
        "machine": "BF-90000-V004-10848-9",
        "home": "Bendougousso 10848",
        "written": "Bendougousso 10 848",
        "zone": "90000-004",
        "official_name": "Bendougousso",
        "number": "10848",
        "check": "9",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T23:59:24Z",
        "entrance_lat": "11.1848213",
        "entrance_lng": "-4.3216628",
        "entrance_kind": "centre",
        "spot_code": "BF-90000 E2929 N2707",
        "official_address": "Rue du Baobab, Bobo-Dioulasso",
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "32.2",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    },
    "… 97 more"
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=BF-10000-V064-1776-8'
```

HTTP 400

```json
{
  "error": {
    "code": "check_digit",
    "message": "The check digit does not match: a digit is wrong or two are swapped."
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Nowhereville%20100'
```

HTTP 404

```json
{
  "error": {
    "code": "unknown_name",
    "message": "No N-Ways area of Burkina Faso is called \"Nowhereville\". Check the place name and the number on the plate."
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Koulouba%20177'
```

HTTP 404

```json
{
  "error": {
    "code": "wrong_digits",
    "message": "Numbers of Koulouba have 4 digits. Check the place name and the number on the plate."
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Secteur%2015%20Ouaga%2048%20217'
```

HTTP 400

```json
{
  "error": {
    "code": "secteur",
    "message": "Secteur codes are not issued: say the quarter or village and its number."
  }
}
```

## GET /v1/at?lat=&lng=

The code of the compound at a point: `found` when a live code's entrance is within 12 m (the issuer's rule; the published registry carries entrances, not building outlines), else `none` with the code area the point falls in, its commune, the area a new code there would take (`newCodeArea`) and the point's spot code.

A point in no commune outline (a gap between two outlines, or just over a border line) is in Burkina Faso when it has a spot code (see `/v1/spot`): its codes are found here like any other, and its `area` is the area a new code there would take (the area of the nearest live code within 250 m, else the nearest numbered area), with that area's commune as `zone`. A point with no commune within 10 km is refused (404 `outside`), and so is a point more than 300 m outside Burkina Faso's national border (OpenStreetMap `admin_level=2`, `engine/SPEC.md` §1b), whatever commune outline or spot frame holds it: the border decides. A published code is always found at its entrance.

```sh
curl -s 'http://localhost:8080/v1/at?lat=12.3641615&lng=-1.5166371'
```

HTTP 200

```json
{
  "status": "found",
  "distanceM": 0.0,
  "code": {
    "machine": "BF-10000-V064-1776-9",
    "remembered": "Koulouba 17 76",
    "home": "Koulouba 1776",
    "spoken": "Koulouba, 17 76",
    "spokenFr": "Koulouba, dix-sept soixante-seize",
    "plateName": "Koulouba",
    "officialName": "Koulouba",
    "number": 1776,
    "check": 9,
    "status": "provisional",
    "issued": "bulk",
    "issuedAt": "2026-10-20T22:50:53Z",
    "officialAddress": "Avenue Uemoa, Ouagadougou",
    "place": "Ouagadougou",
    "entrance": {
      "lat": 12.3641615,
      "lng": -1.5166371,
      "kind": "centre"
    },
    "spotCode": "BF-10000 E1885 N1262",
    "plusCode": "7C4W9F7M+M89",
    "area": {
      "key": "10000-064",
      "id": 64,
      "index": "064",
      "plateName": "Koulouba",
      "officialName": "Koulouba",
      "nameProvisional": false,
      "commune": {
        "postcode": "10000",
        "name": "Ouagadougou"
      },
      "nameKey": "KULUBA",
      "nameId": 5572,
      "digits": 4,
      "blocks": [
        [
          1000,
          6369
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 2683,
      "travelAdvisory": true,
      "point": {
        "lat": 12.36702,
        "lng": -1.51111
      },
      "frame": [
        -1.519638,
        12.357614,
        -1.502982,
        12.379197
      ]
    },
    "zone": {
      "key": "10000",
      "name": "Ouagadougou"
    },
    "building": {
      "class": "hospitality",
      "use": "mixed",
      "kind": "compound",
      "structures": 3,
      "floorAreaM2": 1216.9,
      "rule": "annex",
      "estate": null
    },
    "registry": {
      "machine": "BF-10000-V064-1776-9",
      "home": "Koulouba 1776",
      "written": "Koulouba 17 76",
      "zone": "10000-064",
      "official_name": "Koulouba",
      "number": "1776",
      "check": "9",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-20T22:50:53Z",
      "entrance_lat": "12.3641615",
      "entrance_lng": "-1.5166371",
      "entrance_kind": "centre",
      "spot_code": "BF-10000 E1885 N1262",
      "official_address": "Avenue Uemoa, Ouagadougou",
      "class": "hospitality",
      "use": "mixed",
      "kind": "compound",
      "structures": "3",
      "floor_area_m2": "1216.9",
      "rule": "annex",
      "estate": ""
    },
    "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
  },
  "area": {
    "key": "10000-064",
    "id": 64,
    "index": "064",
    "plateName": "Koulouba",
    "officialName": "Koulouba",
    "nameProvisional": false,
    "commune": {
      "postcode": "10000",
      "name": "Ouagadougou"
    },
    "nameKey": "KULUBA",
    "nameId": 5572,
    "digits": 4,
    "blocks": [
      [
        1000,
        6369
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 2683,
    "travelAdvisory": true,
    "point": {
      "lat": 12.36702,
      "lng": -1.51111
    },
    "frame": [
      -1.519638,
      12.357614,
      -1.502982,
      12.379197
    ]
  },
  "zone": {
    "key": "10000",
    "name": "Ouagadougou"
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/at?lat=12.2&lng=-1.2'
```

HTTP 200

```json
{
  "status": "none",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "newCodeArea": "10400-001",
  "spotCode": "BF-10400 E3155 N1105"
}
```

```sh
curl -s 'http://localhost:8080/v1/at?lat=5.35&lng=-4.0'
```

HTTP 404

```json
{
  "error": {
    "code": "outside",
    "message": "The point 5.350000, -4.000000 is outside Burkina Faso."
  }
}
```

A point 330 m across the national border, inside a commune outline that reaches over it into a neighbouring country: the border decides.

```sh
curl -s 'http://localhost:8080/v1/at?lat=13.460253&lng=1.044921'
```

HTTP 404

```json
{
  "error": {
    "code": "outside",
    "message": "The point 13.460253, 1.044921 is outside Burkina Faso."
  }
}
```

## GET /v1/near?lat=&lng=&radius=&limit=

Codes whose entrance lies within `radius` metres (default 100, at most 500), nearest first, at most `limit` (default and maximum 100).

```sh
curl -s 'http://localhost:8080/v1/near?lat=12.3641615&lng=-1.5166371&radius=30&limit=3'
```

HTTP 200

```json
{
  "point": {
    "lat": 12.3641615,
    "lng": -1.5166371
  },
  "radiusM": 30.0,
  "count": 1,
  "more": false,
  "results": [
    {
      "machine": "BF-10000-V064-1776-9",
      "remembered": "Koulouba 17 76",
      "status": "provisional",
      "entrance": {
        "lat": 12.3641615,
        "lng": -1.5166371,
        "kind": "centre"
      },
      "spotCode": "BF-10000 E1885 N1262",
      "officialAddress": "Avenue Uemoa, Ouagadougou",
      "area": "10000-064",
      "distanceM": 0.0
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/near?lat=12.3641615&lng=-1.5166371&radius=900'
```

HTTP 400

```json
{
  "error": {
    "code": "bad_request",
    "message": "radius must be between 1 and 500."
  }
}
```

## GET /v1/verify?code=

Checks a machine code without decoding a card: syntax, check digit, whether the number is in the area's blocks, whether it is issued and its status. Always 200; `reason` explains a failure.

```sh
curl -s 'http://localhost:8080/v1/verify?code=BF-10000-V064-1776-9'
```

HTTP 200

```json
{
  "code": "BF-10000-V064-1776-9",
  "syntax": true,
  "checkDigit": true,
  "inBlocks": true,
  "issued": true,
  "status": "provisional",
  "machine": "BF-10000-V064-1776-9",
  "remembered": "Koulouba 17 76"
}
```

```sh
curl -s 'http://localhost:8080/v1/verify?code=BF-10000-V064-1767-9'
```

HTTP 200

```json
{
  "code": "BF-10000-V064-1767-9",
  "syntax": true,
  "checkDigit": false,
  "inBlocks": true,
  "issued": false,
  "status": null,
  "machine": null,
  "reason": "the check digit does not match: a digit is wrong or two are swapped"
}
```

## GET /v1/spot?lat=&lng=

The spot code of any point: a 10 m cell of its commune's frame. A point in no commune outline (a gap between two outlines, or just over a border line) is coded in the frame of the commune with the nearest outline within 10 km whose frame holds it; if no frame holds it, in the frame of the nearest such commune whose frame lies within 3,000 m, at the frame's nearest edge cell (SPEC 5.1). `zone` is the commune whose frame the code uses. A point with no commune within 10 km is refused (404 `outside`). A spot code is a grid reference: a point just beyond the national border may have one, but that never makes it Burkina Faso's for a code (`engine/SPEC.md` §1b).

```sh
curl -s 'http://localhost:8080/v1/spot?lat=12.3641615&lng=-1.5166371'
```

HTTP 200

```json
{
  "spotCode": "BF-10000 E1885 N1262",
  "point": {
    "lat": 12.3641615,
    "lng": -1.5166371
  },
  "centre": {
    "lat": 12.3641769,
    "lng": -1.5165912
  },
  "cellM": 10,
  "zone": {
    "key": "10000",
    "name": "Ouagadougou"
  }
}
```

A point in the gap between the Ouagadougou and Komsilga outlines (the entrance of Ouagadougou's code BF-10000-V076-11657-0) takes the frame of Komsilga, whose outline is nearest:

```sh
curl -s 'http://localhost:8080/v1/spot?lat=12.2781536&lng=-1.5450458'
```

HTTP 200

```json
{
  "spotCode": "BF-10990 E2012 N2633",
  "point": {
    "lat": 12.2781536,
    "lng": -1.5450458
  },
  "centre": {
    "lat": 12.2781663,
    "lng": -1.5450655
  },
  "cellM": 10,
  "zone": {
    "key": "10990",
    "name": "Komsilga"
  }
}
```

The entrance of Tangassoko 23 02 (BF-32250-V024-2302-1), south of every frame within 10 km, takes the nearest edge cell of Tiebele's frame, 140 m north of it; the registry keeps the exact entrance beside the code:

```sh
curl -s 'http://localhost:8080/v1/spot?lat=10.9987819&lng=-0.9736617'
```

HTTP 200

```json
{
  "spotCode": "BF-32250 E1052 N0000",
  "point": {
    "lat": 10.9987819,
    "lng": -0.9736617
  },
  "centre": {
    "lat": 11.0000452,
    "lng": -0.9736503
  },
  "cellM": 10,
  "zone": {
    "key": "32250",
    "name": "Tiebele"
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/spot?lat=16.0&lng=-1.0'
```

HTTP 404

```json
{
  "error": {
    "code": "outside",
    "message": "The point 16.000000, -1.000000 is outside Burkina Faso."
  }
}
```

## GET /v1/spot/decode?code=

The centre of a spot code's cell and the commune frame it belongs to.

```sh
curl -s 'http://localhost:8080/v1/spot/decode?code=BF-10000%20E1885%20N1262'
```

HTTP 200

```json
{
  "spotCode": "BF-10000 E1885 N1262",
  "centre": {
    "lat": 12.3641769,
    "lng": -1.5165912
  },
  "cellM": 10,
  "zone": {
    "key": "10000",
    "name": "Ouagadougou"
  },
  "frame": {
    "lon0": -1.69,
    "lat0": 12.25,
    "latc": 12.38,
    "digitsEast": 4,
    "digitsNorth": 4
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/spot/decode?code=BF-10000%20E188%20N1262'
```

HTTP 400

```json
{
  "error": {
    "code": "bad_code",
    "message": "Not a spot code of Burkina Faso (BF-<postcode> E<east> N<north>)."
  }
}
```

## GET /v1/zones

The 351 communes, keyed by La Poste postcode: codes, areas, numbered areas.

```sh
curl -s 'http://localhost:8080/v1/zones'
```

HTTP 200

```json
{
  "count": 351,
  "zones": [
    {
      "key": "10000",
      "name": "Ouagadougou",
      "pcode": "BF130004",
      "codes": 755775,
      "areas": 159,
      "numberedAreas": 159,
      "travelAdvisory": true
    },
    {
      "key": "10200",
      "name": "Saaba",
      "pcode": "BF130006",
      "codes": 125626,
      "areas": 93,
      "numberedAreas": 93,
      "travelAdvisory": true
    },
    {
      "key": "10250",
      "name": "Tanguen-Dassouri",
      "pcode": "BF130007",
      "codes": 48387,
      "areas": 123,
      "numberedAreas": 123,
      "travelAdvisory": true
    },
    "… 348 more"
  ]
}
```

## GET /v1/zones/{key}

One commune with every code area in it and its codes.

```sh
curl -s 'http://localhost:8080/v1/zones/95500'
```

HTTP 200

```json
{
  "key": "95500",
  "name": "Wolonkoto",
  "pcode": "BF470208",
  "codes": 2931,
  "areas": [
    {
      "key": "95500-001",
      "id": 16027,
      "index": "001",
      "plateName": "Diurmanko",
      "officialName": "Diurmanko",
      "nameProvisional": false,
      "commune": {
        "postcode": "95500",
        "name": "Wolonkoto"
      },
      "nameKey": "DIURMANKO",
      "nameId": 2427,
      "digits": 3,
      "blocks": [
        [
          100,
          229
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 63,
      "travelAdvisory": true,
      "point": {
        "lat": 10.698236,
        "lng": -5.042939
      },
      "frame": [
        -5.057709,
        10.644554,
        -5.008311,
        10.708247
      ],
      "codes": 63
    },
    {
      "key": "95500-002",
      "id": 16028,
      "index": "002",
      "plateName": "Kokora",
      "officialName": "Kokora",
      "nameProvisional": false,
      "commune": {
        "postcode": "95500",
        "name": "Wolonkoto"
      },
      "nameKey": "KOKORA",
      "nameId": 4880,
      "digits": 4,
      "blocks": [
        [
          1890,
          2019
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 64,
      "travelAdvisory": true,
      "point": {
        "lat": 10.793387,
        "lng": -4.988651
      },
      "frame": [
        -5.007497,
        10.788911,
        -4.969787,
        10.803858
      ],
      "codes": 64
    },
    {
      "key": "95500-003",
      "id": 16029,
      "index": "003",
      "plateName": "Kolana",
      "officialName": "Kolana",
      "nameProvisional": false,
      "commune": {
        "postcode": "95500",
        "name": "Wolonkoto"
      },
      "nameKey": "KOLANA",
      "nameId": 4895,
      "digits": 3,
      "blocks": [
        [
          100,
          179
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 36,
      "travelAdvisory": true,
      "point": {
        "lat": 10.715493,
        "lng": -5.047016
      },
      "frame": [
        -5.068935,
        10.708446,
        -5.037638,
        10.724534
      ],
      "codes": 36
    },
    "… 7 more"
  ],
  "numberedAreas": 10,
  "travelAdvisory": true
}
```

```sh
curl -s 'http://localhost:8080/v1/zones/99999'
```

HTTP 404

```json
{
  "error": {
    "code": "not_found",
    "message": "No zone 99999: a zone is a commune, keyed by its 5-digit postcode. /v1/zones lists them."
  }
}
```

## GET /v1/zones/{key}/codes?after=&limit=

Every code of a commune, as registry rows, in machine-form order. Pass `next` as `after` to get the following page; `next` is null on the last page. `limit` is at most 1,000.

```sh
curl -s 'http://localhost:8080/v1/zones/95500/codes?limit=2'
```

HTTP 200

```json
{
  "zone": "95500",
  "after": null,
  "limit": 2,
  "count": 2,
  "next": "BF-95500-V001-101-2",
  "results": [
    {
      "machine": "BF-95500-V001-100-4",
      "home": "Diurmanko 100",
      "written": "Diurmanko 100",
      "zone": "95500-001",
      "official_name": "Diurmanko",
      "number": "100",
      "check": "4",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T00:13:29Z",
      "entrance_lat": "10.6495898",
      "entrance_lng": "-5.0373371",
      "entrance_kind": "centre",
      "spot_code": "BF-95500 E0466 N0769",
      "official_address": "",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "71.7",
      "rule": "single",
      "estate": ""
    },
    {
      "machine": "BF-95500-V001-101-2",
      "home": "Diurmanko 101",
      "written": "Diurmanko 101",
      "zone": "95500-001",
      "official_name": "Diurmanko",
      "number": "101",
      "check": "2",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T00:13:29Z",
      "entrance_lat": "10.6493824",
      "entrance_lng": "-5.0379134",
      "entrance_kind": "centre",
      "spot_code": "BF-95500 E0460 N0767",
      "official_address": "",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "60.5",
      "rule": "single",
      "estate": ""
    }
  ]
}
```

```sh
curl -s 'http://localhost:8080/v1/zones/95500/codes?limit=2&after=BF-95500-V001-101-2'
```

HTTP 200

```json
{
  "zone": "95500",
  "after": "BF-95500-V001-101-2",
  "limit": 2,
  "count": 2,
  "next": "BF-95500-V001-103-6",
  "results": [
    {
      "machine": "BF-95500-V001-102-0",
      "home": "Diurmanko 102",
      "written": "Diurmanko 102",
      "zone": "95500-001",
      "official_name": "Diurmanko",
      "number": "102",
      "check": "0",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T00:13:29Z",
      "entrance_lat": "10.6536638",
      "entrance_lng": "-5.0376502",
      "entrance_kind": "centre",
      "spot_code": "BF-95500 E0463 N0814",
      "official_address": "",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "22.2",
      "rule": "single",
      "estate": ""
    },
    {
      "machine": "BF-95500-V001-103-6",
      "home": "Diurmanko 103",
      "written": "Diurmanko 103",
      "zone": "95500-001",
      "official_name": "Diurmanko",
      "number": "103",
      "check": "6",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T00:13:29Z",
      "entrance_lat": "10.6761245",
      "entrance_lng": "-5.0386563",
      "entrance_kind": "centre",
      "spot_code": "BF-95500 E0452 N1062",
      "official_address": "",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "15.4",
      "rule": "single",
      "estate": ""
    }
  ]
}
```

## GET /v1/areas/{key}

One code area, by key (`10000-064`) or numeric id: names, name range, blocks, frame, codes by status, the lowest and highest number, the start of the tail reserve and the free numbers, and the other areas of the same plate name.

```sh
curl -s 'http://localhost:8080/v1/areas/10000-064'
```

HTTP 200

```json
{
  "key": "10000-064",
  "id": 64,
  "index": "064",
  "plateName": "Koulouba",
  "officialName": "Koulouba",
  "nameProvisional": false,
  "commune": {
    "postcode": "10000",
    "name": "Ouagadougou"
  },
  "nameKey": "KULUBA",
  "nameId": 5572,
  "digits": 4,
  "blocks": [
    [
      1000,
      6369
    ]
  ],
  "numbered": true,
  "compoundsAtIssue": 2683,
  "travelAdvisory": true,
  "point": {
    "lat": 12.36702,
    "lng": -1.51111
  },
  "frame": [
    -1.519638,
    12.357614,
    -1.502982,
    12.379197
  ],
  "byStatus": {
    "provisional": 2683
  },
  "codes": 2683,
  "numbers": {
    "lowest": 1000,
    "highest": 3682,
    "tailReserveFrom": 4580,
    "free": 2687
  },
  "sameName": []
}
```

```sh
curl -s 'http://localhost:8080/v1/areas/10000-999'
```

HTTP 404

```json
{
  "error": {
    "code": "not_found",
    "message": "No code area 10000-999 (a key such as 10000-064, or a numeric id). Search by name with /v1/areas?name=."
  }
}
```

## GET /v1/areas?name=

Areas by plate name or official name (alias-aware, folded as the engine folds names); else by official name; else by prefix (`match` says which).

```sh
curl -s 'http://localhost:8080/v1/areas?name=Natenga'
```

HTTP 200

```json
{
  "name": "Natenga",
  "nameKey": "NATENGA",
  "match": "name",
  "count": 74,
  "results": [
    {
      "key": "10300-030",
      "id": 405,
      "index": "030",
      "plateName": "Natenga",
      "officialName": "Q Natenga",
      "nameProvisional": false,
      "commune": {
        "postcode": "10300",
        "name": "Pabre"
      },
      "nameKey": "NATENGA",
      "nameId": 7169,
      "digits": 5,
      "blocks": [
        [
          10000,
          10269
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 131,
      "travelAdvisory": true,
      "point": {
        "lat": 12.530683,
        "lng": -1.509091
      },
      "frame": [
        -1.510468,
        12.526233,
        -1.497977,
        12.540024
      ],
      "codes": 131
    },
    {
      "key": "20250-034",
      "id": 871,
      "index": "034",
      "plateName": "Natenga",
      "officialName": "Q-Natenga",
      "nameProvisional": false,
      "commune": {
        "postcode": "20250",
        "name": "Dapeolgo"
      },
      "nameKey": "NATENGA",
      "nameId": 7169,
      "digits": 5,
      "blocks": [
        [
          10270,
          11319
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 525,
      "travelAdvisory": true,
      "point": {
        "lat": 12.667951,
        "lng": -1.537651
      },
      "frame": [
        -1.545805,
        12.663668,
        -1.534606,
        12.673338
      ],
      "codes": 525
    },
    {
      "key": "22250-024",
      "id": 1690,
      "index": "024",
      "plateName": "Natenga",
      "officialName": "Natenga",
      "nameProvisional": false,
      "commune": {
        "postcode": "22250",
        "name": "Niou"
      },
      "nameKey": "NATENGA",
      "nameId": 7169,
      "digits": 5,
      "blocks": [
        [
          11320,
          12359
        ]
      ],
      "numbered": true,
      "compoundsAtIssue": 520,
      "travelAdvisory": true,
      "point": {
        "lat": 12.772976,
        "lng": -1.934783
      },
      "frame": [
        -1.943763,
        12.770097,
        -1.927807,
        12.782948
      ],
      "codes": 520
    },
    "… 71 more"
  ]
}
```

## POST /v1/codes

Issues a code for a new compound (`lat`, `lng`, optional `outline` as `[[lng, lat], ...]`) or for another door of an issued code (`of`). Needs a bearer key from `ISSUE_KEYS`; a deployment without keys refuses with 403 `read_only`. The rules are the issuer's (server/README.md, "Issuing"): no code within 3 m of a live one, outlines from 6 m² to 2 ha that cover no live code, doors within 80 m of their code, the area of the nearest live code within 250 m, numbering between Hilbert neighbours, then the tail reserve, later blocks and a new block of the name. A point in no commune outline that has a spot code (a gap between two outlines) is in Burkina Faso and is issued like any other; a point with no commune within 10 km is refused (422 `outside`), and so is a point more than 300 m outside the national border, whatever commune outline or spot frame holds it (`engine/SPEC.md` §1b). 201 with the new card. Responses below are from a test copy of the registry.

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 12.2, "lng": -1.2}' 'http://localhost:8080/v1/codes'
```

HTTP 201

```json
{
  "machine": "BF-10400-V001-406-3",
  "remembered": "Bangressen 406",
  "home": "Bangressen 406",
  "spoken": "Bangressen, 406",
  "spokenFr": "Bangressen, quatre cent six",
  "plateName": "Bangressen",
  "officialName": "Bangressen",
  "number": 406,
  "check": 3,
  "status": "provisional",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Koubri",
  "entrance": {
    "lat": 12.2,
    "lng": -1.2,
    "kind": "centre"
  },
  "spotCode": "BF-10400 E3155 N1105",
  "plusCode": "7C4W6R22+222",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "building",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10400-V001-406-3",
    "home": "Bangressen 406",
    "written": "Bangressen 406",
    "zone": "10400-001",
    "official_name": "Bangressen",
    "number": "406",
    "check": "3",
    "status": "provisional",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.2000000",
    "entrance_lng": "-1.2000000",
    "entrance_kind": "centre",
    "spot_code": "BF-10400 E3155 N1105",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "building",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 12.36425, "lng": -1.5166, "of": "BF-10000-V064-1776-9"}' 'http://localhost:8080/v1/codes'
```

HTTP 201

```json
{
  "machine": "BF-10000-V064-4580-8",
  "remembered": "Koulouba 45 80",
  "home": "Koulouba 4580",
  "spoken": "Koulouba, 45 80",
  "spokenFr": "Koulouba, quarante-cinq quatre-vingts",
  "plateName": "Koulouba",
  "officialName": "Koulouba",
  "number": 4580,
  "check": 8,
  "status": "provisional",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Ouagadougou",
  "entrance": {
    "lat": 12.36425,
    "lng": -1.5166,
    "kind": "door"
  },
  "spotCode": "BF-10000 E1885 N1263",
  "plusCode": "7C4W9F7M+P92",
  "area": {
    "key": "10000-064",
    "id": 64,
    "index": "064",
    "plateName": "Koulouba",
    "officialName": "Koulouba",
    "nameProvisional": false,
    "commune": {
      "postcode": "10000",
      "name": "Ouagadougou"
    },
    "nameKey": "KULUBA",
    "nameId": 5572,
    "digits": 4,
    "blocks": [
      [
        1000,
        6369
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 2683,
    "travelAdvisory": true,
    "point": {
      "lat": 12.36702,
      "lng": -1.51111
    },
    "frame": [
      -1.519638,
      12.357614,
      -1.502982,
      12.379197
    ]
  },
  "zone": {
    "key": "10000",
    "name": "Ouagadougou"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "door",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10000-V064-4580-8",
    "home": "Koulouba 4580",
    "written": "Koulouba 45 80",
    "zone": "10000-064",
    "official_name": "Koulouba",
    "number": "4580",
    "check": "8",
    "status": "provisional",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.3642500",
    "entrance_lng": "-1.5166000",
    "entrance_kind": "door",
    "spot_code": "BF-10000 E1885 N1263",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "door",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s -X POST -H 'Content-Type: application/json' -d '{"lat": 12.2, "lng": -1.2}' 'http://localhost:8080/v1/codes'
```

HTTP 401

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Send the issuing key as \"Authorization: Bearer <key>\"."
  }
}
```

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 12.2, "lng": -1.2}' 'http://localhost:8080/v1/codes'
```

HTTP 403

```json
{
  "error": {
    "code": "read_only",
    "message": "This deployment is read-only: it does not issue or change codes. Only the issuer designated by the State or N-WAYS LIMITED does."
  }
}
```

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 12.3641615, "lng": -1.5166371}' 'http://localhost:8080/v1/codes'
```

HTTP 409

```json
{
  "error": {
    "code": "exists",
    "message": "This building already has its code: Koulouba 17 76.",
    "existing": {
      "machine": "BF-10000-V064-1776-9",
      "remembered": "Koulouba 17 76",
      "home": "Koulouba 1776",
      "spoken": "Koulouba, 17 76",
      "spokenFr": "Koulouba, dix-sept soixante-seize",
      "plateName": "Koulouba",
      "officialName": "Koulouba",
      "number": 1776,
      "check": 9,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-20T22:50:53Z",
      "officialAddress": "Avenue Uemoa, Ouagadougou",
      "place": "Ouagadougou",
      "entrance": {
        "lat": 12.3641615,
        "lng": -1.5166371,
        "kind": "centre"
      },
      "spotCode": "BF-10000 E1885 N1262",
      "plusCode": "7C4W9F7M+M89",
      "area": {
        "key": "10000-064",
        "id": 64,
        "index": "064",
        "plateName": "Koulouba",
        "officialName": "Koulouba",
        "nameProvisional": false,
        "commune": {
          "postcode": "10000",
          "name": "Ouagadougou"
        },
        "nameKey": "KULUBA",
        "nameId": 5572,
        "digits": 4,
        "blocks": [
          [
            1000,
            6369
          ]
        ],
        "numbered": true,
        "compoundsAtIssue": 2683,
        "travelAdvisory": true,
        "point": {
          "lat": 12.36702,
          "lng": -1.51111
        },
        "frame": [
          -1.519638,
          12.357614,
          -1.502982,
          12.379197
        ]
      },
      "zone": {
        "key": "10000",
        "name": "Ouagadougou"
      },
      "building": {
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": 3,
        "floorAreaM2": 1216.9,
        "rule": "annex",
        "estate": null
      },
      "registry": {
        "machine": "BF-10000-V064-1776-9",
        "home": "Koulouba 1776",
        "written": "Koulouba 17 76",
        "zone": "10000-064",
        "official_name": "Koulouba",
        "number": "1776",
        "check": "9",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-20T22:50:53Z",
        "entrance_lat": "12.3641615",
        "entrance_lng": "-1.5166371",
        "entrance_kind": "centre",
        "spot_code": "BF-10000 E1885 N1262",
        "official_address": "Avenue Uemoa, Ouagadougou",
        "class": "hospitality",
        "use": "mixed",
        "kind": "compound",
        "structures": "3",
        "floor_area_m2": "1216.9",
        "rule": "annex",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
    }
  }
}
```

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 12.21, "lng": -1.21, "outline": [[-1.21, 12.21], [-1.20999, 12.21], [-1.20999, 12.21001]]}' 'http://localhost:8080/v1/codes'
```

HTTP 422

```json
{
  "error": {
    "code": "bad_outline",
    "message": "That outline is 1 m², but a home's is between 6 m² and 2 ha. Draw the building again."
  }
}
```

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 5.35, "lng": -4.0}' 'http://localhost:8080/v1/codes'
```

HTTP 422

```json
{
  "error": {
    "code": "outside",
    "message": "That point is outside Burkina Faso, so it cannot have an N-Ways Burkina Faso code."
  }
}
```

The same refusal for a point 330 m across the national border, although a commune outline holds it:

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 13.460253, "lng": 1.044921}' 'http://localhost:8080/v1/codes'
```

HTTP 422

```json
{
  "error": {
    "code": "outside",
    "message": "That point is outside Burkina Faso, so it cannot have an N-Ways Burkina Faso code."
  }
}
```

## PATCH /v1/codes/{machine}

Sets the status (`provisional`, `confirmed`, `retired`) or moves the entrance (at most 80 m, to a point in Burkina Faso as for issuing, a gap between commune outlines included, and never more than 300 m outside the national border: 422 `outside`; the entrance kind becomes `gate` and the spot code follows). A retired code is never changed again and its number is never given again. Same key as issuing.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "confirmed"}' 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 200

```json
{
  "machine": "BF-10400-V001-406-3",
  "remembered": "Bangressen 406",
  "home": "Bangressen 406",
  "spoken": "Bangressen, 406",
  "spokenFr": "Bangressen, quatre cent six",
  "plateName": "Bangressen",
  "officialName": "Bangressen",
  "number": 406,
  "check": 3,
  "status": "confirmed",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Koubri",
  "entrance": {
    "lat": 12.2,
    "lng": -1.2,
    "kind": "centre"
  },
  "spotCode": "BF-10400 E3155 N1105",
  "plusCode": "7C4W6R22+222",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "building",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10400-V001-406-3",
    "home": "Bangressen 406",
    "written": "Bangressen 406",
    "zone": "10400-001",
    "official_name": "Bangressen",
    "number": "406",
    "check": "3",
    "status": "confirmed",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.2000000",
    "entrance_lng": "-1.2000000",
    "entrance_kind": "centre",
    "spot_code": "BF-10400 E3155 N1105",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "building",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"entrance": {"lat": 12.20005, "lng": -1.20003}}' 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 200

```json
{
  "machine": "BF-10400-V001-406-3",
  "remembered": "Bangressen 406",
  "home": "Bangressen 406",
  "spoken": "Bangressen, 406",
  "spokenFr": "Bangressen, quatre cent six",
  "plateName": "Bangressen",
  "officialName": "Bangressen",
  "number": 406,
  "check": 3,
  "status": "confirmed",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Koubri",
  "entrance": {
    "lat": 12.20005,
    "lng": -1.20003,
    "kind": "gate"
  },
  "spotCode": "BF-10400 E3154 N1106",
  "plusCode": "7C4W6Q2X+2XH",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "building",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10400-V001-406-3",
    "home": "Bangressen 406",
    "written": "Bangressen 406",
    "zone": "10400-001",
    "official_name": "Bangressen",
    "number": "406",
    "check": "3",
    "status": "confirmed",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.2000500",
    "entrance_lng": "-1.2000300",
    "entrance_kind": "gate",
    "spot_code": "BF-10400 E3154 N1106",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "building",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"entrance": {"lat": 12.21, "lng": -1.2}}' 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 422

```json
{
  "error": {
    "code": "too_far",
    "message": "The new entrance is 1108 m from the code; an entrance moves at most 80 m. Issue a new code for another building."
  }
}
```

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "retired"}' 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 200

```json
{
  "machine": "BF-10400-V001-406-3",
  "remembered": "Bangressen 406",
  "home": "Bangressen 406",
  "spoken": "Bangressen, 406",
  "spokenFr": "Bangressen, quatre cent six",
  "plateName": "Bangressen",
  "officialName": "Bangressen",
  "number": 406,
  "check": 3,
  "status": "retired",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Koubri",
  "entrance": {
    "lat": 12.20005,
    "lng": -1.20003,
    "kind": "gate"
  },
  "spotCode": "BF-10400 E3154 N1106",
  "plusCode": "7C4W6Q2X+2XH",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "building",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10400-V001-406-3",
    "home": "Bangressen 406",
    "written": "Bangressen 406",
    "zone": "10400-001",
    "official_name": "Bangressen",
    "number": "406",
    "check": "3",
    "status": "retired",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.2000500",
    "entrance_lng": "-1.2000300",
    "entrance_kind": "gate",
    "spot_code": "BF-10400 E3154 N1106",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "building",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "confirmed"}' 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 409

```json
{
  "error": {
    "code": "retired",
    "message": "Bangressen 406 is retired. A retired code is never used again; issue a new one."
  }
}
```

```sh
curl -s 'http://localhost:8080/v1/codes/BF-10400-V001-406-3'
```

HTTP 200

```json
{
  "machine": "BF-10400-V001-406-3",
  "remembered": "Bangressen 406",
  "home": "Bangressen 406",
  "spoken": "Bangressen, 406",
  "spokenFr": "Bangressen, quatre cent six",
  "plateName": "Bangressen",
  "officialName": "Bangressen",
  "number": 406,
  "check": 3,
  "status": "retired",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T20:50:03Z",
  "officialAddress": null,
  "place": "Koubri",
  "entrance": {
    "lat": 12.20005,
    "lng": -1.20003,
    "kind": "gate"
  },
  "spotCode": "BF-10400 E3154 N1106",
  "plusCode": "7C4W6Q2X+2XH",
  "area": {
    "key": "10400-001",
    "id": 497,
    "index": "001",
    "plateName": "Bangressen",
    "officialName": "Bangressen",
    "nameProvisional": false,
    "commune": {
      "postcode": "10400",
      "name": "Koubri"
    },
    "nameKey": "BANGRESEN",
    "nameId": 465,
    "digits": 3,
    "blocks": [
      [
        100,
        559
      ]
    ],
    "numbered": true,
    "compoundsAtIssue": 230,
    "travelAdvisory": true,
    "point": {
      "lat": 12.19993,
      "lng": -1.20965
    },
    "frame": [
      -1.221565,
      12.178721,
      -1.184347,
      12.207041
    ]
  },
  "zone": {
    "key": "10400",
    "name": "Koubri"
  },
  "building": {
    "class": null,
    "use": "residential",
    "kind": "building",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "registry": {
    "machine": "BF-10400-V001-406-3",
    "home": "Bangressen 406",
    "written": "Bangressen 406",
    "zone": "10400-001",
    "official_name": "Bangressen",
    "number": "406",
    "check": "3",
    "status": "retired",
    "issued": "on-demand",
    "issued_at": "2026-10-21T20:50:03Z",
    "entrance_lat": "12.2000500",
    "entrance_lng": "-1.2000300",
    "entrance_kind": "gate",
    "spot_code": "BF-10400 E3154 N1106",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "building",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)"
}
```

```sh
curl -s 'http://localhost:8080/v1/find?q=Bangressen%20406'
```

HTTP 410

```json
{
  "error": {
    "code": "retired",
    "message": "Bangressen 406 was retired: there is no home there any more. A retired code is never given again."
  }
}
```

## Any other path

Unknown paths are 404 `not_found`; a known path with the wrong method is 405 with an `Allow` header.

```sh
curl -s 'http://localhost:8080/v1/nothing'
```

HTTP 404

```json
{
  "error": {
    "code": "not_found",
    "message": "No endpoint /v1/nothing. See /v1/info and docs/api.md."
  }
}
```
