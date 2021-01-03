ADDRESS_CSV = './data/address.csv'

COORDINATES_QUERY = "https://nominatim.openstreetmap.org/search?format=json&country={}&postalcode={}&street={}+{}"

DIST_MATRIX_FILE = './data/dist_matrix.json'

OPENSTREETMAP_LINK_URL = 'https://routing.openstreetmap.de'

LINK_URL_TEMPLATE = OPENSTREETMAP_LINK_URL + "/?z=15&center={}&{}&hl=de&alt=0&"  # srv=0 todo driving-car


def openstreetmap_url(planning_type):
    if planning_type == 'foot':
        return LINK_URL_TEMPLATE + 'srv=2'
    if planning_type == 'car':
        return LINK_URL_TEMPLATE + 'srv=0'
    raise ValueError("Planning Type unsupported " + planning_type)
