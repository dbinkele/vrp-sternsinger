#!/usr/bin/env bash

docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/map.osm
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/map.osrm
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/map.osrm
