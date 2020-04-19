ADDRESS_CSV = './data/address.csv'

COORDINATES_QUERY = "https://nominatim.openstreetmap.org/search?format=json&country={}&postalcode={}&street={}+{}"

DIST_MATRIX_FILE = './data/dist_matrix.json'

LOCAL_LINK_URL = 'http://127.0.0.1:9966'
OPENSTREETMAP_LINK_URL = 'https://routing.openstreetmap.de'

LINK_URL_TEMPLATE = LOCAL_LINK_URL + "/?z=15&center={}&{}&hl=de&alt=0&srv=2"

INITIAL_SOLUTION = [
    [20,   19,   57,   77,   48,   61,   67,   10,   76,   28,   8,   43,   72,   26],
    [73,   12,   50,   14,   42,   55,   66,   1,   52,   38,   35,   22],
    [82,   70,   41,   78,   17,   18,   16,   3,   2,   7,   4,   32],
    [71,   37,   75,   51,   21,   13,   45,   27,   74,   58,   49],
    [63,   62,   54,   69,   6,   64,   53,   56,   81,   40,   15,   39],
    [68,   80,   24,   36,   44,   46,   59,   34,   23,   11,   5],
    [60,   30,   33,   65,   25,   31,   79,   29,   9,   47],
]
