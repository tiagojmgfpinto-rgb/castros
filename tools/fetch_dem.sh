#!/bin/sh
# Terrarium elevation tiles used by tools/maquette.py (NW Iberia relief model): z10 (with bathymetry) and z11 (land detail)
mkdir -p dem10 dem11
for x in $(seq 481 497); do for y in $(seq 368 389); do [ -f dem10/10_${x}_${y}.png ] || echo "curl -s --retry 3 -o dem10/10_${x}_${y}.png https://s3.amazonaws.com/elevation-tiles-prod/terrarium/10/$x/$y.png"; done; done > /tmp/_j.txt
for x in $(seq 962 995); do for y in $(seq 736 779); do [ -f dem11/11_${x}_${y}.png ] || echo "curl -s --retry 3 -o dem11/11_${x}_${y}.png https://s3.amazonaws.com/elevation-tiles-prod/terrarium/11/$x/$y.png"; done; done >> /tmp/_j.txt
xargs -P 16 -I{} sh -c '{}' < /tmp/_j.txt
