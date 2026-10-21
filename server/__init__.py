"""N-Ways Addressing for Burkina Faso: the registry server.

A self-contained HTTP service (Python standard library only). It serves the published registry
(registry/) as a JSON API and, on the one deployment designated as the issuer, issues new codes by
the rules of the N-Ways issuer. See server/README.md.

    python3 -m server import --registry registry --db data/addresses.sqlite
    python3 -m server serve  --db data/addresses.sqlite --port 8080
    python3 -m server export --db data/addresses.sqlite --out out/registry
"""

COUNTRY = 'BF'
COUNTRY_NAME = 'Burkina Faso'
API_VERSION = '1'
CREDIT = 'N-Ways Addressing for Burkina Faso, © N-WAYS LIMITED (nways.ng)'
CREDIT_URL = 'https://github.com/n-ways/open-addresses-burkina-faso'
