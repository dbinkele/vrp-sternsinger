from main.requests_util import request_dist_matrix
from main.run_algorithm import mainrunner
from main.template import render


def run_job(address_json, constrains_json):
    dist_matrix_json = request_dist_matrix(address_json)
    json_routes = mainrunner(dist_matrix_json, constrains_json, address_json)
    routes_html = [render(json_route) for json_route in json_routes]
    return routes_html
