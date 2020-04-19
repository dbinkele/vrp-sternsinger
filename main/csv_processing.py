# Function to convert a csv file to a list of dictionaries.  Takes in one variable called &quot;variables_file&quot;
from functools import reduce

import requests
import json

from main.constants import COORDINATES_QUERY, DIST_MATRIX_FILE
from main.requests_util import request_dist_matrix, make_url
from main.util import restrict_to_keys, json_file_name_from_csv, resolve_address_file


def csv_dict_list(csv_file):
    with open(csv_file) as f:
        csv_list = [[val.strip() for val in r.split(",")] for r in f.readlines()]

    header, *data = csv_list

    rows_with_header = [zip(header, row) for row in data]
    return [{key: value for key, value in row_with_header}
            for row_with_header in rows_with_header]


def fetch_coordinates(location):
    url = COORDINATES_QUERY.format(
        'de', location['code'], location['number'], location['street'])
    print("Url " + url)
    response = requests.get(url)
    keys = ['lat', 'lon']
    if response.status_code == 200:
        first_hit = response.json()[0]
        return restrict_to_keys(first_hit, keys)


def to_json_with_coordinates(file_name):
    addresses_dict = csv_dict_list(file_name)
    coor_out = []
    for address in addresses_dict:
        coordinates = fetch_coordinates(address)
        coord_str = "[" + coordinates['lon'] + ',' + coordinates['lat'] + "]"
        coor_out.append(coord_str)
        address.update(coordinates)

    with open(json_file_name_from_csv(file_name), 'w') as outfile:
        json.dump(addresses_dict, outfile)

    return addresses_dict


def dump_to_dist_matrix_file(json_dict):
    keys = ['durations']
    dist_matrix_dict = dict(zip(keys, [json_dict[k] for k in keys]))
    with open(json_file_name_from_csv(DIST_MATRIX_FILE), 'w') as outfile:
        json.dump(dist_matrix_dict, outfile)


def make_formatted_routes(routes, json_addresses):
    return [route_to_adress(route, json_addresses) for route in routes]


def route_to_adress(route, addresses):
    return [addresses[elem] for elem in route]


if __name__ == '__main__':
    address_file = resolve_address_file()
    adresses_json = to_json_with_coordinates(address_file)

    response_json = request_dist_matrix(adresses_json)
    print("-------> " + str(response_json))
    if response_json:
        dump_to_dist_matrix_file(response_json)
