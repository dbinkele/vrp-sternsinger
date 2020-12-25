# <iframe src="https://www.google.com/maps/embed?pb=!1m31!1m8!1m3!1d10705.673273926313!2d9.017564647069243!3d48.92799870223893!3m2!1i1024!2i768!4f13.1!4m20!3e2!4m4!2s48.93174%2C9.020655!3m2!1d48.93174!2d9.020655!4m4!2s48.924651%2C9.027033!3m2!1d48.924651!2d9.027033!4m4!2s48.9292215%2C9.0293626!3m2!1d48.9292215!2d9.029362599999999!4m3!3m2!1d48.930242!2d9.031668!5e0!3m2!1sde!2sde!4v1576564363135!5m2!1sde!2sde" width="600" height="450" frameborder="0" style="border:0;" allowfullscreen=""></iframe>
from functools import reduce

from jinja2 import Template

from main.constants import LINK_URL_TEMPLATE
from main.util import restrict_to_keys


def to_address_line(json_address):
    address_slices = restrict_to_keys(json_address, ['code', 'city', 'street', 'number', 'name', 'hint']).values()
    return ' '.join([str(slice) for slice in  address_slices])


def make_loc(json_address):
    lat_lons = restrict_to_keys(json_address, ['lat', 'lon'])
    return 'loc=' + str(lat_lons['lat']) + ',' + str(lat_lons['lon'])


def make_center(json_addresses):
    no_entries = len(json_addresses)
    avg_lat = average_of_key('lat', json_addresses, no_entries)
    avg_lon = average_of_key('lat', json_addresses, no_entries)
    return str(avg_lat) + ',' + str(avg_lon)


def average_of_key(key, json_addresses, no_entries):
    avg_lat = reduce(lambda x, y: x + float(y[key]), json_addresses, 0) / no_entries
    return avg_lat


def render(json_addresses, template_html):
    map_link = make_map_link(json_addresses)
    addresses = [to_address_line(json_address) for json_address in json_addresses]

    with open(template_html) as file_:
        template = Template(file_.read())
    return template.render(addresses=addresses, map_link=map_link)


def make_map_link(json_addresses):
    loc = '&'.join([make_loc(json_address) for json_address in json_addresses])
    center = make_center(json_addresses)
    map_link = LINK_URL_TEMPLATE.format(center, loc)
    return map_link
