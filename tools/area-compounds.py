#!/usr/bin/env python3
"""Compounds per code area at first issue, for the national name ranges (model/areas/name-ranges.json).

  python3 tools/area-compounds.py <work folder> > model/stats/area-compounds.csv

Every area of the register (model/areas/register.json) with the compounds actually grouped in it
(<work>/area-counts.json, written by `tools/issue_registry.py group`). All areas are named places (kind
V): towns are no longer cut into secteurs (tools/build-areas.py).
"""
import csv, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
counts = json.load(open(os.path.join(os.path.abspath(sys.argv[1]), 'area-counts.json')))
reg = json.load(open(os.path.join(REPO, 'model', 'areas', 'register.json'), encoding='utf-8'))
w = csv.writer(sys.stdout, lineterminator='\n')
w.writerow(['kind', 'postcode', 'index', 'officialName', 'place', 'lon', 'lat', 'sample', 'compounds'])
for pc in sorted(reg):
    for v in reg[pc]['villages']:
        w.writerow(['V', pc, v['index'], v['officialName'], v['kind'], v['lon'], v['lat'], '', counts.get(f"{pc}-{v['index']}", 0)])
