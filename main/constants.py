ADDRESS_CSV = './data/address.csv'

MAPBOX_QUERY = 'https://' + 'api.mapbox.com' + '/directions-matrix/v1/mapbox/walking/{' \
                                               '}?access_token=pk' \
                                               '.eyJ1IjoiZGFuZGVsaW4iLCJhIjoiY2s0NzFybHJqMGFpYTNrcWxmanp2b2tzcyJ9.XQN' \
                                               '-K3gC4ON6D75A361b1g'

OSRM_QUERY = 'http://127.0.0.1:5000/table/v1/walking/{}'

DISTANCE_MATRIX_QUERY = OSRM_QUERY  # MAPBOX_QUERY
COORDINATES_QUERY = "https://nominatim.openstreetmap.org/search?format=json&country={}&postalcode={}&street={}+{}"

DIST_MATRIX_FILE = './data/dist_matrix.json'

LOCAL_LINK_URL = 'http://127.0.0.1:9966'
OPENSTREETMAP_LINK_URL = 'https://routing.openstreetmap.de'

LINK_URL_TEMPLATE = LOCAL_LINK_URL + "/?z=15&center={}&{}&hl=de&alt=0&srv=2"
