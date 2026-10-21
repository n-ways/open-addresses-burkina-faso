# Contributing

N-Ways Addressing for Burkina Faso is maintained by the N-Ways addressing team for Burkina Faso. Corrections, ports of the engine, translations and reports from the field are welcome.

## What you can propose

- **A correction to an address.** A wrong gate, two homes under one code, a building that is not a home: say so in the N-Ways app at the gate. People's confirmations settle these by the rules of engine/SPEC.md §9, faster than any change to this repository.
- **A correction to the data or the documents.** Open an issue or a pull request on GitHub (https://github.com/n-ways/open-addresses-burkina-faso), or write to hello@nways.ng. Give the code or the area key (`10000-064`), what is wrong, and your source.
- **A plate name.** A commune may choose once the short name of an area that carries a provisional one (SPEC §2.5). The choice reaches the registry through `model/areas/renames.json` and `tools/rename-areas.py`; the old name stays an alias and no number moves.
- **A port of the engine** to another language: it conforms when it reproduces every vector in `engine/reference/test_vectors.json` and `engine/reference/vectors.json` (SPEC §13).

## Rules for a change

1. **An issued code never changes.** No change may move, renumber or reuse a code, or change a check digit. A format change needs published vectors and a migration in which every old code still resolves.
2. **One issuer.** New codes are issued by the designated issuer only (GOVERNANCE.md, "One issuer"). A pull request never adds codes to `registry/` by hand: the registry is the issuer's export, checked by its manifest.
3. **Tests pass.** Run both test suites before you propose a change:

   ```sh
   (cd engine/reference && python3 test_bf.py)
   python3 -m unittest discover -s server/tests -t .
   ```

4. **Explain changed vectors.** Any change to `test_vectors.json` or `vectors.json` says why, in the pull request.
5. **Standard library only.** The engine, the tools that rebuild the published files and the server use Python's standard library, so that anyone can run them.
6. Two maintainers approve a change to the engine, the formats or the server's issuing rules.

By contributing you agree that your contribution is licensed under the licence of the part you change (LICENSING.md).
