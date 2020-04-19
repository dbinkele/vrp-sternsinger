import json
import os
from functools import reduce

import requests
from numpy.distutils.system_info import lapack_opt_info

OSRM_QUERY = 'http://127.0.0.1:5000/table/v1/walking/{}'
DISTANCE_MATRIX_QUERY = OSRM_QUERY  # MAPBOX_QUERY
MAPBOX_QUERY = 'https://' + 'api.mapbox.com' + '/directions-matrix/v1/mapbox/walking/{' \
                                               '}?access_token=pk' \
                                               '.eyJ1IjoiZGFuZGVsaW4iLCJhIjoiY2s0NzFybHJqMGFpYTNrcWxmanp2b2tzcyJ9.XQN' \
                                               '-K3gC4ON6D75A361b1g'


def request_dist_matrix(adresses_json):
    # return request_local(adresses_json)
    return request_remote(adresses_json)


def request_remote(adresses_json):
    api_key = os.getenv("MAP_API_KEY")

    endpoint = "https://api.openrouteservice.org/v2/matrix/foot-walking"
    lon_lat = [[item['lon'], item['lat']] for item in adresses_json]
    data = json.dumps(
        {"locations": lon_lat})
    headers = {"Authorization": "Bearer " + api_key, 'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json',
               'Accept': '*/*'}
    return requests.post(endpoint, data=data, headers=headers).json()


def request_local(adresses_json):
    url = make_url(adresses_json)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise ConnectionError("Bad request " + str(response.status_code))


def make_url(addresses):
    lat_lon_str = [str(item['lon'] + ',' + str(item['lat'])) for item in addresses]
    lat_lon_query = reduce(lambda x, y: x + ';' + y, lat_lon_str)
    url = DISTANCE_MATRIX_QUERY.format(lat_lon_query)
    return url
