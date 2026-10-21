#!/bin/bash
# A 10% sample of building centres (OpenStreetMap and footprints), for the design statistics.
#   NWAYS_ROOT=<N-Ways data folder> tools/sample.sh BF burkina-faso
cc="$1"; slug="$2"; lc=$(echo "$cc" | tr A-Z a-z)
root="${NWAYS_ROOT:?set NWAYS_ROOT to the N-Ways data folder}"
duckdb -csv > "out/$lc/sample.csv" <<SQL
SET memory_limit='3GB'; SET threads=4; LOAD spatial;
SELECT round(ST_X(c),6) x, round(ST_Y(c),6) y FROM (
 SELECT ST_Centroid(ST_GeomFromGeoJSON(json_extract(ltrim(line, chr(30)), '\$.geometry'))) c
   FROM read_csv('$root/data/detail/countries/$slug/buildings-src.geojsonseq', columns={'line':'VARCHAR'}, header=false, delim=chr(1), quote='', escape='', max_line_size=16000000) WHERE length(line)>2 AND hash(line) % 10 = 0
 UNION ALL SELECT ST_Centroid(geometry) FROM '$root/data/detail/ml/$cc.parquet' WHERE hash(ST_AsWKB(geometry)) % 10 = 0);
SQL
wc -l "out/$lc/sample.csv"
