# Security and safety

## Reporting a problem

Write to **hello@nways.ng** with the subject "Security: open-addresses-burkina-faso". Say what you found and how to reproduce it. Please do not open a public issue for a vulnerability or for a record that could put someone at risk.

We acknowledge a report within three working days and tell you what we will do and when.

## What to report

- A flaw in the registry server (`server/`): a way to issue or change a code without a valid key, to read what the API should not return, to corrupt the database, or to deny service with a small request.
- A flaw in the engine that decodes one code to two places, or accepts a wrong check digit.
- A published record that could put a person at risk, such as a site for displaced people or a home that should not be on the map. We review it at once and, where needed, publish a corrected registry.

## Running a deployment safely

- Keep `ISSUE_KEYS` empty unless the deployment is the designated issuer (GOVERNANCE.md). A read-only deployment refuses every write.
- Serve the API behind a reverse proxy with TLS (server/README.md); issuing keys travel in the `Authorization` header.
- Never commit keys or `.env` files. Rotate a key that may have been exposed: restart the server with the new list.
- Back up the database with `python3 -m server backup` before every update of the registry.
