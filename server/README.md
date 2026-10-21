# The registry server

A ready-made HTTP service for N-Ways Addressing for Burkina Faso. It loads the published registry ([`registry/`](../registry/): every issued code of Burkina Faso, 8,369,987 at the export of 21 October 2026), serves it as a JSON API, and, on the one deployment designated as the issuer, issues new codes by exactly the rules the N-Ways issuer applies. A ministry, La Poste, a commune, a courier or a developer can run it without touching the code, and two deployments on the same registry give the same answers.

- Python 3.9 or newer, standard library only (`http.server`, `sqlite3`, `json`, `gzip`, `hashlib`). No packages to install.
- Name keys, check digits, machine and remembered forms, spot codes, plate names and the Hilbert curve come from the reference engine ([`engine/reference/bf_engine.py`](../engine/reference/bf_engine.py)), not from a second implementation.
- One SQLite file (WAL mode) holds the registry, its indexes and a spatial index (R*Tree, or an integer grid where SQLite was built without R*Tree).
- The API: [docs/api.md](../docs/api.md) (every endpoint with a real request and response) and [openapi.yaml](openapi.yaml) (OpenAPI 3.1).

## Run it

### With Docker

```sh
cd server
docker compose up -d
curl -s http://localhost:8080/v1/health
```

That is the whole deployment. The image carries the registry of this repository. On the first start, with an empty `addresses` volume, the container imports it (about a minute and a half on a laptop: every file's SHA-256 and every count is checked against `registry/MANIFEST.json`), then serves on port 8080. Later starts reuse the volume and serve at once. The container runs as an unprivileged user and reports its health to Docker from `/v1/health`. The compose file publishes the port on `127.0.0.1` only; set `BIND=0.0.0.0` to expose it directly, or better, put a reverse proxy in front (below).

### With Python

From the repository root:

```sh
python3 -m server import --registry registry --db data/addresses.sqlite
python3 -m server serve --db data/addresses.sqlite --port 8080
```

The import of the full registry takes about a minute and a half on a laptop, with under 1 GB of memory, and makes a database of about 3.8 GB; keep twice that free on the disk, because the new database is built beside the old one and only replaces it once every check has passed. `serve --registry registry` imports first when the database does not exist yet.

Run the tests with `python3 -m unittest discover -s server/tests -t .` (a one-commune fixture in `server/testdata/registry`, and 24 codes whose entrances lie in no commune outline in `server/testdata/registry-gaps`, one of them 297.8 m outside the national border; about twenty seconds).

### Behind a reverse proxy with TLS

The server speaks plain HTTP; put it behind a proxy that terminates TLS. With Caddy, which obtains and renews the certificate itself:

```
adresses.example.bf {
    reverse_proxy 127.0.0.1:8080
}
```

With nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name adresses.example.bf;
    ssl_certificate     /etc/letsencrypt/live/adresses.example.bf/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adresses.example.bf/privkey.pem;
    client_max_body_size 64k;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Bind the server to `127.0.0.1` (`HOST=127.0.0.1`) or keep it on a private Docker network, and publish only the proxy. Issuing keys travel in the `Authorization` header and must only ever cross TLS.

## Configure

| Variable | Default | Meaning |
|---|---|---|
| `ADDRESSES_DB` | `data/addresses.sqlite` (`/data/addresses.sqlite` in the container) | the database file |
| `HOST` | `0.0.0.0` | the address to listen on |
| `PORT` | `8080` | the port |
| `ISSUE_KEYS` | empty | comma-separated bearer keys allowed to issue and change codes; empty means read-only |
| `ISSUE_PER_DAY` | `5` | codes each key may issue in any 24 hours |
| `CORS_ORIGINS` | empty | comma-separated origins allowed to call the API from a browser, or `*` |

The same settings exist as command-line flags (`--db`, `--host`, `--port`). With Docker, put them in `server/.env` (never commit that file) or in the environment of `docker compose up`.

A key is any long random string, for example `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Give one key to each system that issues, so that one can be withdrawn alone. The server never stores a key: it records a short hash of the key beside every code issued with it.

## Issuing: one issuer for the country

**A deployment issues codes only if the State or N-WAYS LIMITED has designated it as the issuer. Every other deployment runs read-only: no `ISSUE_KEYS`.**

The reason is arithmetic, not policy. Every area of a plate name draws its numbers from one national range for that name, and a new compound takes the free number between its neighbours on the area's Hilbert curve. Two issuers working from the same registry would compute the same free number for two different homes, and "Koulouba 17 77" would then name two gates. One issuer, with every other deployment importing its registry, keeps every code unique in the country. Within one deployment, numbers are handed out one at a time (a lock in the process and `BEGIN IMMEDIATE` in SQLite), so two requests at the same moment never share a number.

The issuer's rules, which `POST /v1/codes` applies decision for decision (engine/SPEC.md §6.6):

1. A point outside Burkina Faso gets no code (422 `outside`). The border decides (`engine/SPEC.md` §1b): a point more than 300 m outside Burkina Faso's national border (OpenStreetMap `admin_level=2`, shipped simplified as `engine/data/border.json` and read by `engine/reference/bf_border.py`) is in a neighbouring country and is refused, whatever commune outline or spot frame holds it; an entrance is never moved there either. Within it, a point is in the country when it lies in a commune outline, or in no outline but close enough to one to have a spot code (engine/SPEC.md §5.1): the published outlines do not tile the country exactly, and the compounds in the gaps between them are in Burkina Faso. The same test decides where `PATCH` may move an entrance, and `/v1/at` for a point with no code within 12 m (a published code is always found at its entrance).
2. A new compound gets no code when a live code's entrance lies within 3 m, when the point lies inside an outline issued here, or when its outline (6 m² to 2 ha) covers a live code (409 `exists`, with the existing card). An outline outside 6 m² to 2 ha is refused (422 `bad_outline`).
3. Another door (`of`) must be within 80 m of its code (422 `too_far`) and takes that code's area.
4. Otherwise the area is that of the nearest live code within 250 m, so a new house joins its neighbours; else the code area the point lies in (the nearest named place of its commune; a point in no outline lies in none); else the nearest numbered area.
5. The number lies between the new compound's neighbours on the area's Hilbert curve, nearest their midpoint, below the tail reserve; else the lowest free number of the tail reserve; else of the area's later blocks; else of a new block taken from the name's spare, sized for twice the area's compounds. A new block is stored with the area and exported in `areas.csv.gz`. When the name's range is used up the code is refused (409 `area_full`) until the commune chooses a qualifier.
6. The code is `provisional` and `on-demand`. Each key issues at most `ISSUE_PER_DAY` codes in 24 hours (429 `rate_limited`).

`PATCH /v1/codes/{machine}` confirms or retires a code, or moves its entrance by at most 80 m. A retired code stays in the registry and its number is never given again.

The published registry carries one point per compound, its entrance, and not the building outlines the N-Ways issuer also holds. A deployment therefore measures the 3 m, 12 m and 250 m rules to entrances (and to the outlines it issued itself). For the N-Ways issuer's codes the numbering point is the entrance, so the numbers a deployment gives are the issuer's; [`tests/test_server.py`](tests/test_server.py) replays a 105-step issuing scenario against the numbers the N-Ways issuer computes on the same registry, including a full block, its tail reserve and an extension block. On the complete registry, 50 random codes served by a deployment matched the N-Ways API field by field. Where a point lies between two compounds, `/v1/at` names the compound whose entrance is nearest, while the N-Ways issuer, which holds the building outlines, names the building the point falls in: on 40 points within 8 m of a random entrance the two agreed 33 times, and every other answer was a neighbouring compound. Nine pairs of codes share an entrance point exactly; a new compound numbered on that very point would be ordered against them by machine form here and by the issuer's internal compound key, so on those nine points alone a deployment and the issuer could choose different free numbers.

## Back up

```sh
python3 -m server backup --db data/addresses.sqlite --out backup/addresses-$(date +%F).sqlite
docker compose exec addresses python3 -m server backup --out /data/backup.sqlite   # in the container
```

The backup is consistent while the server runs. An issuing deployment should back up daily and keep its exports: `python3 -m server export --db data/addresses.sqlite --out out/registry` writes the registry in the published format (the same columns, order and gzip, and a new `MANIFEST.json`), ready to publish.

## Update to a newer registry

```sh
git pull                                   # the new registry/
python3 -m server import --registry registry --db data/addresses.sqlite
```

then restart the server. The import builds a new database beside the old one, verifies every SHA-256 and count, and only then replaces it; a registry that does not match its manifest is refused and the old database is left as it was. Codes this deployment issued or changed since its last import, and that the new registry does not hold yet, are carried over; a code whose number the new registry gives to another compound is reported and not carried over. With Docker:

```sh
docker compose build
docker compose run --rm addresses python3 -m server import --registry /app/registry
docker compose up -d
```

## Export and round trip

After an import of the published registry, `export` writes files whose uncompressed bytes are identical to the published ones, and an identical `MANIFEST.json` (the `exported` time changes only once the deployment has issued or changed a code). The tests check this on the fixture, and it was checked on the complete registry.

## What it serves

| Endpoint | |
|---|---|
| `GET /v1/health` | status, country, codes, registry export date |
| `GET /v1/info` | country, counts, communes, licences, credit line, engine and specification |
| `GET /v1/codes/{machine}` | the full card of a code |
| `GET /v1/find?q=` | a remembered form, machine form, spot code or official address |
| `GET /v1/at?lat=&lng=` | the code of the compound at a point |
| `GET /v1/near?lat=&lng=&radius=` | codes within 500 m, at most 100 |
| `GET /v1/verify?code=` | syntax, check digit, blocks, issued |
| `GET /v1/spot?lat=&lng=`, `GET /v1/spot/decode?code=` | spot codes |
| `GET /v1/zones`, `GET /v1/zones/{postcode}` | the communes and their areas |
| `GET /v1/zones/{postcode}/codes?after=&limit=` | every code of a commune, paged |
| `GET /v1/areas/{key}`, `GET /v1/areas?name=` | one area; areas by name |
| `POST /v1/codes` | issue (designated issuer only) |
| `PATCH /v1/codes/{machine}` | confirm, retire, move the entrance (designated issuer only) |

Credit every use: "N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)" (LICENSING.md). The code is Apache 2.0; the registry it serves is ODbL 1.0.
