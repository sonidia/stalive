import sys
import json
import requests
import os

from PySide6.QtCore    import Qt, Signal, QObject, QStringListModel, QThread, QRect, QPoint, QTimer
from PySide6.QtGui     import QColor, QFont, QIcon, QTextCursor, QPainter, QTextDocument, QAbstractTextDocumentLayout
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QFrame, QSizePolicy, QCompleter, QMessageBox,
    QScrollArea, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)

# ─── Data ──────────────────────────────────────────────────────────────────────
COUNTRY_DATA = {
    "US": {
        "states":   [
            "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
            "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
            "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
            "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
            "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
            "New Hampshire", "New Jersey", "New Mexico", "New York",
            "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
            "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
            "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
            "West Virginia", "Wisconsin", "Wyoming",
        ],
        "networks": ["ATT", "Verizon", "T-Mobile", "Sprint", "Comcast", "Charter", "CenturyLink", "Cox"],
        "cities": {
            "Alabama":        ["Birmingham", "Montgomery", "Huntsville", "Mobile", "Tuscaloosa"],
            "Alaska":         ["Anchorage", "Fairbanks", "Juneau", "Sitka", "Ketchikan"],
            "Arizona":        ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale", "Glendale", "Tempe"],
            "Arkansas":       ["Little Rock", "Fort Smith", "Fayetteville", "Springdale", "Jonesboro"],
            "California":     ["Los Angeles", "San Diego", "San Jose", "San Francisco", "Fresno", "Sacramento", "Long Beach", "Oakland"],
            "Colorado":       ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Lakewood", "Boulder"],
            "Connecticut":    ["Bridgeport", "New Haven", "Hartford", "Stamford", "Waterbury"],
            "Delaware":       ["Wilmington", "Dover", "Newark", "Middletown", "Smyrna"],
            "Florida":        ["Jacksonville", "Miami", "Tampa", "Orlando", "St. Petersburg", "Hialeah", "Tallahassee", "Fort Lauderdale"],
            "Georgia":        ["Atlanta", "Augusta", "Columbus", "Macon", "Savannah", "Athens"],
            "Hawaii":         ["Honolulu", "Hilo", "Kailua", "Pearl City", "Waipahu"],
            "Idaho":          ["Boise", "Meridian", "Nampa", "Idaho Falls", "Pocatello"],
            "Illinois":       ["Chicago", "Aurora", "Rockford", "Joliet", "Naperville", "Springfield"],
            "Indiana":        ["Indianapolis", "Fort Wayne", "Evansville", "South Bend", "Carmel"],
            "Iowa":           ["Des Moines", "Cedar Rapids", "Davenport", "Sioux City", "Iowa City"],
            "Kansas":         ["Wichita", "Overland Park", "Kansas City", "Olathe", "Topeka"],
            "Kentucky":       ["Louisville", "Lexington", "Bowling Green", "Owensboro", "Covington"],
            "Louisiana":      ["New Orleans", "Baton Rouge", "Shreveport", "Metairie", "Lafayette"],
            "Maine":          ["Portland", "Lewiston", "Bangor", "South Portland", "Auburn"],
            "Maryland":       ["Baltimore", "Frederick", "Rockville", "Gaithersburg", "Bowie"],
            "Massachusetts":  ["Boston", "Worcester", "Springfield", "Cambridge", "Lowell"],
            "Michigan":       ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Ann Arbor"],
            "Minnesota":      ["Minneapolis", "Saint Paul", "Rochester", "Duluth", "Bloomington"],
            "Mississippi":    ["Jackson", "Gulfport", "Southaven", "Hattiesburg", "Biloxi"],
            "Missouri":       ["Kansas City", "Saint Louis", "Springfield", "Columbia", "Independence"],
            "Montana":        ["Billings", "Missoula", "Great Falls", "Bozeman", "Butte"],
            "Nebraska":       ["Omaha", "Lincoln", "Bellevue", "Grand Island", "Kearney"],
            "Nevada":         ["Las Vegas", "Henderson", "Reno", "North Las Vegas", "Sparks"],
            "New Hampshire":  ["Manchester", "Nashua", "Concord", "Dover", "Rochester"],
            "New Jersey":     ["Newark", "Jersey City", "Paterson", "Elizabeth", "Trenton"],
            "New Mexico":     ["Albuquerque", "Las Cruces", "Rio Rancho", "Santa Fe", "Roswell"],
            "New York":       ["New York City", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany"],
            "North Carolina": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem"],
            "North Dakota":   ["Fargo", "Bismarck", "Grand Forks", "Minot", "West Fargo"],
            "Ohio":           ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron"],
            "Oklahoma":       ["Oklahoma City", "Tulsa", "Norman", "Broken Arrow", "Edmond"],
            "Oregon":         ["Portland", "Eugene", "Salem", "Gresham", "Hillsboro"],
            "Pennsylvania":   ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading"],
            "Rhode Island":   ["Providence", "Cranston", "Warwick", "Pawtucket", "East Providence"],
            "South Carolina": ["Columbia", "Charleston", "North Charleston", "Mount Pleasant", "Greenville"],
            "South Dakota":   ["Sioux Falls", "Rapid City", "Aberdeen", "Brookings", "Watertown"],
            "Tennessee":      ["Nashville", "Memphis", "Knoxville", "Chattanooga", "Clarksville"],
            "Texas":          ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso", "Arlington"],
            "Utah":           ["Salt Lake City", "West Valley City", "Provo", "West Jordan", "Orem"],
            "Vermont":        ["Burlington", "South Burlington", "Rutland", "Barre", "Montpelier"],
            "Virginia":       ["Virginia Beach", "Norfolk", "Chesapeake", "Richmond", "Newport News"],
            "Washington":     ["Seattle", "Spokane", "Tacoma", "Vancouver", "Bellevue"],
            "West Virginia":  ["Charleston", "Huntington", "Morgantown", "Parkersburg", "Wheeling"],
            "Wisconsin":      ["Milwaukee", "Madison", "Green Bay", "Kenosha", "Racine"],
            "Wyoming":        ["Cheyenne", "Casper", "Laramie", "Gillette", "Rock Springs"],
        },
    },
    "AU": {
        "states":   [
            "New South Wales", "Victoria", "Queensland", "South Australia",
            "Western Australia", "Tasmania", "Northern Territory",
            "Australian Capital Territory",
        ],
        "networks": ["Vodafone", "Telstra", "Optus", "TPG", "Aussie Broadband"],
        "cities": {
            "New South Wales":           ["Sydney", "Newcastle", "Wollongong", "Central Coast", "Maitland"],
            "Victoria":                  ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Shepparton"],
            "Queensland":                ["Brisbane", "Gold Coast", "Sunshine Coast", "Townsville", "Cairns"],
            "South Australia":           ["Adelaide", "Mount Gambier", "Whyalla", "Murray Bridge", "Port Augusta"],
            "Western Australia":         ["Perth", "Bunbury", "Geraldton", "Kalgoorlie", "Albany"],
            "Tasmania":                  ["Hobart", "Launceston", "Devonport", "Burnie", "Queenstown"],
            "Northern Territory":        ["Darwin", "Alice Springs", "Palmerston", "Katherine", "Nhulunbuy"],
            "Australian Capital Territory": ["Canberra", "Belconnen", "Tuggeranong", "Gungahlin", "Woden"],
        },
    },
    "CA": {
        "states":   [
            "Alberta", "British Columbia", "Manitoba", "New Brunswick",
            "Newfoundland and Labrador", "Nova Scotia", "Northwest Territories",
            "Nunavut", "Ontario", "Prince Edward Island", "Quebec",
            "Saskatchewan", "Yukon",
        ],
        "networks": ["Rogers", "Bell", "Telus", "Freedom Mobile", "Shaw", "Videotron"],
        "cities": {
            "Alberta":                  ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "St. Albert"],
            "British Columbia":          ["Vancouver", "Surrey", "Burnaby", "Richmond", "Kelowna", "Abbotsford"],
            "Manitoba":                  ["Winnipeg", "Brandon", "Steinbach", "Thompson", "Portage la Prairie"],
            "New Brunswick":             ["Moncton", "Saint John", "Fredericton", "Miramichi", "Edmundston"],
            "Newfoundland and Labrador": ["St. John's", "Corner Brook", "Gander", "Grand Falls-Windsor"],
            "Nova Scotia":               ["Halifax", "Dartmouth", "Sydney", "Truro", "New Glasgow"],
            "Northwest Territories":     ["Yellowknife", "Hay River", "Inuvik", "Fort Smith"],
            "Nunavut":                   ["Iqaluit", "Rankin Inlet", "Arviat", "Baker Lake"],
            "Ontario":                   ["Toronto", "Ottawa", "Mississauga", "Brampton", "Hamilton", "London"],
            "Prince Edward Island":      ["Charlottetown", "Summerside", "Stratford", "Cornwall"],
            "Quebec":                    ["Montreal", "Quebec City", "Laval", "Gatineau", "Longueuil"],
            "Saskatchewan":              ["Saskatoon", "Regina", "Prince Albert", "Moose Jaw", "Swift Current"],
            "Yukon":                     ["Whitehorse", "Dawson City", "Watson Lake", "Haines Junction"],
        },
    },
    "GB": {
        "states":   ["England", "Scotland", "Wales", "Northern Ireland"],
        "networks": ["BT", "EE", "O2", "Vodafone", "Three", "Sky", "Virgin Media"],
        "cities": {
            "England":          ["London", "Birmingham", "Manchester", "Leeds", "Liverpool", "Sheffield", "Bristol", "Leicester"],
            "Scotland":         ["Glasgow", "Edinburgh", "Aberdeen", "Dundee", "Inverness", "Stirling"],
            "Wales":            ["Cardiff", "Swansea", "Newport", "Bangor", "Wrexham"],
            "Northern Ireland": ["Belfast", "Derry", "Lisburn", "Newry", "Armagh"],
        },
    },
    "DE": {
        "states":   [
            "Bavaria", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hesse",
            "Mecklenburg-Vorpommern", "Lower Saxony", "North Rhine-Westphalia",
            "Rhineland-Palatinate", "Saarland", "Saxony", "Saxony-Anhalt",
            "Schleswig-Holstein", "Thuringia",
        ],
        "networks": ["Deutsche Telekom", "Vodafone", "O2", "1&1", "Freenet"],
        "cities": {
            "Bavaria":                ["Munich", "Nuremberg", "Augsburg", "Regensburg", "Ingolstadt"],
            "Berlin":                 ["Berlin"],
            "Brandenburg":            ["Potsdam", "Cottbus", "Brandenburg an der Havel", "Frankfurt (Oder)"],
            "Bremen":                 ["Bremen", "Bremerhaven"],
            "Hamburg":                ["Hamburg"],
            "Hesse":                  ["Frankfurt", "Wiesbaden", "Kassel", "Darmstadt", "Offenbach"],
            "Mecklenburg-Vorpommern": ["Rostock", "Schwerin", "Neubrandenburg", "Stralsund"],
            "Lower Saxony":           ["Hanover", "Braunschweig", "Osnabrück", "Oldenburg"],
            "North Rhine-Westphalia": ["Cologne", "Düsseldorf", "Dortmund", "Essen", "Duisburg", "Bochum"],
            "Rhineland-Palatinate":   ["Mainz", "Ludwigshafen", "Koblenz", "Trier", "Kaiserslautern"],
            "Saarland":               ["Saarbrücken", "Neunkirchen", "Homburg", "Saarlouis"],
            "Saxony":                 ["Dresden", "Leipzig", "Chemnitz", "Zwickau", "Erfurt"],
            "Saxony-Anhalt":          ["Magdeburg", "Halle", "Dessau-Roßlau", "Lutherstadt Wittenberg"],
            "Schleswig-Holstein":     ["Kiel", "Lübeck", "Flensburg", "Neumünster"],
            "Thuringia":              ["Erfurt", "Jena", "Gera", "Weimar", "Gotha"],
        },
    },
    "FR": {
        "states":   [
            "Ile-de-France", "Auvergne-Rhone-Alpes", "Bourgogne-Franche-Comte",
            "Bretagne", "Centre-Val de Loire", "Grand Est",
            "Hauts-de-France", "Normandie", "Nouvelle-Aquitaine",
            "Occitanie", "Pays de la Loire", "Provence-Alpes-Cote d'Azur",
        ],
        "networks": ["Orange", "SFR", "Bouygues Telecom", "Free Mobile"],
        "cities": {
            "Ile-de-France":              ["Paris", "Boulogne-Billancourt", "Saint-Denis", "Argenteuil", "Versailles"],
            "Auvergne-Rhone-Alpes":       ["Lyon", "Grenoble", "Saint-Etienne", "Clermont-Ferrand", "Annecy"],
            "Bourgogne-Franche-Comte":    ["Dijon", "Besançon", "Chalon-sur-Saône", "Mâcon", "Auxerre"],
            "Bretagne":                   ["Rennes", "Brest", "Quimper", "Lorient", "Vannes"],
            "Centre-Val de Loire":        ["Tours", "Orléans", "Bourges", "Blois", "Chartres"],
            "Grand Est":                  ["Strasbourg", "Reims", "Metz", "Nancy", "Mulhouse"],
            "Hauts-de-France":            ["Lille", "Amiens", "Roubaix", "Tourcoing", "Dunkirk"],
            "Normandie":                  ["Rouen", "Caen", "Le Havre", "Cherbourg", "Alençon"],
            "Nouvelle-Aquitaine":         ["Bordeaux", "Limoges", "Pau", "Bayonne", "La Rochelle"],
            "Occitanie":                  ["Toulouse", "Montpellier", "Nîmes", "Perpignan", "Narbonne"],
            "Pays de la Loire":           ["Nantes", "Le Mans", "Angers", "Saint-Nazaire", "Laval"],
            "Provence-Alpes-Cote d'Azur": ["Marseille", "Nice", "Toulon", "Aix-en-Provence", "Avignon"],
        },
    },
    "JP": {
        "states":   ["Tokyo", "Osaka", "Kyoto", "Aichi", "Fukuoka", "Hokkaido", "Kanagawa", "Okinawa"],
        "networks": ["NTT", "SoftBank", "KDDI", "Rakuten Mobile"],
        "cities": {
            "Tokyo":    ["Shinjuku", "Shibuya", "Chiyoda", "Minato", "Setagaya", "Hachioji"],
            "Osaka":    ["Osaka", "Sakai", "Higashiosaka", "Hirakata", "Toyonaka"],
            "Kyoto":    ["Kyoto", "Uji", "Kameoka", "Maizuru", "Fukuchiyama"],
            "Aichi":    ["Nagoya", "Toyota", "Okazaki", "Ichinomiya", "Toyohashi"],
            "Fukuoka":  ["Fukuoka", "Kitakyushu", "Kurume", "Omuta", "Iizuka"],
            "Hokkaido": ["Sapporo", "Asahikawa", "Hakodate", "Kushiro", "Tomakomai"],
            "Kanagawa": ["Yokohama", "Kawasaki", "Sagamihara", "Fujisawa", "Yokosuka"],
            "Okinawa":  ["Naha", "Okinawa City", "Uruma", "Ginowan", "Urasoe"],
        },
    },
    "SG": {
        "states":   ["Central", "North", "South", "East", "West"],
        "networks": ["Singtel", "StarHub", "M1", "TPG Telecom"],
        "cities": {
            "Central": ["Orchard", "Marina Bay", "Toa Payoh", "Bishan", "Ang Mo Kio"],
            "North":   ["Woodlands", "Yishun", "Sembawang", "Canberra"],
            "South":   ["Buona Vista", "Queenstown", "Telok Blangah", "Harbourfront"],
            "East":    ["Tampines", "Bedok", "Pasir Ris", "Changi", "Geylang"],
            "West":    ["Jurong", "Bukit Batok", "Clementi", "Choa Chu Kang", "Boon Lay"],
        },
    },
    "IN": {
        "states":   [
            "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Uttar Pradesh",
            "West Bengal", "Gujarat", "Rajasthan", "Madhya Pradesh",
            "Andhra Pradesh",
        ],
        "networks": ["Jio", "Airtel", "Vi", "BSNL", "MTNL"],
        "cities": {
            "Maharashtra":   ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane"],
            "Delhi":         ["New Delhi", "Delhi", "Noida", "Gurgaon", "Faridabad"],
            "Karnataka":     ["Bengaluru", "Mysuru", "Mangaluru", "Hubli", "Belagavi"],
            "Tamil Nadu":    ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
            "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Ghaziabad"],
            "West Bengal":   ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"],
            "Gujarat":       ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
            "Rajasthan":     ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
            "Madhya Pradesh":["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"],
            "Andhra Pradesh":["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Tirupati"],
        },
    },
    "BR": {
        "states":   [
            "Sao Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia", "Parana",
            "Rio Grande do Sul", "Pernambuco", "Ceara", "Para", "Maranhao",
        ],
        "networks": ["Claro", "Vivo", "TIM", "Oi", "Nextel"],
        "cities": {
            "Sao Paulo":       ["São Paulo", "Guarulhos", "Campinas", "São Bernardo do Campo", "Santo André"],
            "Rio de Janeiro":  ["Rio de Janeiro", "São Gonçalo", "Duque de Caxias", "Nova Iguaçu", "Niterói"],
            "Minas Gerais":    ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora", "Montes Claros"],
            "Bahia":           ["Salvador", "Feira de Santana", "Vitória da Conquista", "Camaçari", "Itabuna"],
            "Parana":          ["Curitiba", "Londrina", "Maringá", "Ponta Grossa", "Cascavel"],
            "Rio Grande do Sul":["Porto Alegre", "Caxias do Sul", "Canoas", "Pelotas", "Santa Maria"],
            "Pernambuco":      ["Recife", "Caruaru", "Petrolina", "Olinda", "Paulista"],
            "Ceara":           ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Maracanaú", "Sobral"],
            "Para":            ["Belém", "Ananindeua", "Santarém", "Marabá", "Castanhal"],
            "Maranhao":        ["São Luís", "Imperatriz", "São José de Ribamar", "Timon", "Caxias"],
        },
    },
}

ALL_NETWORKS = sorted({n for d in COUNTRY_DATA.values() for n in d["networks"]})
API_BASE     = "http://192.168.1.29"
API_SUFFIX = ":1998/api"

if getattr(sys, 'frozen', False):
    # _BUNDLE_DIR: read-only bundled assets (icon, etc.) live in _MEIPASS temp folder.
    _BUNDLE_DIR = sys._MEIPASS
    # _DATA_DIR: writable persistent data (data.json) lives next to the EXE,
    # NOT in _MEIPASS which is deleted when the app exits.
    _DATA_DIR = os.path.dirname(sys.executable)
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR   = os.path.dirname(os.path.abspath(__file__))

APP_DATA_FILE = os.path.join(_DATA_DIR, "data.json")

# If running as frozen EXE and data.json doesn't exist next to EXE yet,
# seed it from the bundled copy inside _MEIPASS (first-run bootstrap).
if getattr(sys, 'frozen', False) and not os.path.exists(APP_DATA_FILE):
    _bundled = os.path.join(sys._MEIPASS, "data.json")
    if os.path.exists(_bundled):
        import shutil
        try:
            shutil.copy2(_bundled, APP_DATA_FILE)
        except Exception:
            pass  # will fall back to empty dict

def _load_app_data() -> dict:
    """Load the unified data file. Returns dict with keys: api_base, proxies."""
    try:
        if os.path.exists(APP_DATA_FILE):
            with open(APP_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print(f"Error loading app data: {e}")
    return {}

def _save_app_data(data: dict):
    """Overwrite the unified data file."""
    try:
        with open(APP_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving app data: {e}")

def load_api_base() -> str:
    """Load saved API base URL from unified data file."""
    url = _load_app_data().get("api_base", f"{API_BASE}{API_SUFFIX}")
    # Remove /api suffix for display in input field
    if url.endswith('/api'):
        url = url[:-4]  # Remove '/api'
    return url

def get_api_base_for_requests() -> str:
    """Get the full API base URL for making HTTP requests."""
    url = _load_app_data().get("api_base", f"{API_BASE}{API_SUFFIX}")
    # Ensure URL ends with /api for API calls
    if not url.endswith('/api'):
        url += '/api'
    return url

def normalize_api_base_for_requests(url: str) -> str:
    """Normalize a URL string to ensure it ends with /api for API requests."""
    if not url:
        return get_api_base_for_requests()
    # Ensure URL ends with /api
    if not url.endswith('/api'):
        url += '/api'
    return url

def save_api_base(url: str):
    """Save API base URL into unified data file (preserves proxies)."""
    # Ensure URL ends with /api for API calls
    if not url.endswith('/api'):
        url += '/api'
    data = _load_app_data()
    data["api_base"] = url
    _save_app_data(data)

def load_proxies_from_file() -> list:
    """Load proxy list from unified data file."""
    try:
        return list(_load_app_data().get("proxies", []))
    except Exception as e:
        print(f"Error loading proxies: {e}")
    return []

def save_proxies_to_file(new_proxies: list):
    """Append new proxies to unified data file, avoiding duplicates."""
    try:
        data = _load_app_data()
        existing: list = data.get("proxies", [])

        existing_keys = set()
        for p in existing:
            ip   = p.get("ip", p.get("host", ""))
            port = p.get("port", "")
            if ip:
                existing_keys.add(f"{ip}:{port}")

        added = 0
        for p in new_proxies:
            ip   = p.get("ip", p.get("host", ""))
            port = p.get("port", "")
            key  = f"{ip}:{port}"
            if key not in existing_keys:
                existing.append(p)
                existing_keys.add(key)
                added += 1

        data["proxies"] = existing
        _save_app_data(data)
        print(f"[Cache] Saved {added} new proxy(ies). Total: {len(existing)}. File: {APP_DATA_FILE}")
    except Exception as e:
        print(f"Error saving proxies: {e}")

def delete_proxy_from_file(ip: str, port: str):
    """Remove a proxy by ip:port from the unified data file."""
    try:
        data = _load_app_data()
        proxies = data.get("proxies", [])
        key = f"{ip}:{port}"
        data["proxies"] = [
            p for p in proxies
            if f"{p.get('ip', p.get('host', ''))}:{p.get('port', '')}" != key
        ]
        _save_app_data(data)
    except Exception as e:
        print(f"Error deleting proxy: {e}")

# ─── Country Flags ─────────────────────────────────────────────────────────────
def draw_country_flag(painter, country_code, rect):
    """Draw a simple flag icon for the given country code."""
    # Don't save/restore painter state as it may already be managed by caller
    # painter.save()

    # Flag dimensions
    flag_width = 20
    flag_height = 14
    flag_rect = QRect(rect.left() + 5, rect.top() + (rect.height() - flag_height) // 2,
                     flag_width, flag_height)

    if country_code == "US":  # Stars and stripes
        # Red and white stripes
        painter.fillRect(flag_rect, QColor("#B22234"))  # Red background
        for i in range(7):
            if i % 2 == 0:
                painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + i * 2, flag_width, 2),
                               QColor("#FFFFFF"))

        # Blue canton
        canton_rect = QRect(flag_rect.left(), flag_rect.top(), flag_width * 2 // 3, flag_height * 7 // 13)
        painter.fillRect(canton_rect, QColor("#3C3B6E"))

    elif country_code == "GB":  # Union Jack
        painter.fillRect(flag_rect, QColor("#012169"))  # Dark blue background
        # Simple cross
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#C8102E"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#C8102E"))

    elif country_code == "DE":  # German flag
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 3), QColor("#000000"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 3, flag_width, flag_height // 3), QColor("#DD0000"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 2 * flag_height // 3, flag_width, flag_height // 3), QColor("#FFCC00"))

    elif country_code == "FR":  # French flag
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width // 3, flag_height), QColor("#002654"))
        painter.fillRect(QRect(flag_rect.left() + flag_width // 3, flag_rect.top(), flag_width // 3, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left() + 2 * flag_width // 3, flag_rect.top(), flag_width // 3, flag_height), QColor("#ED2939"))

    elif country_code == "JP":  # Japanese flag
        painter.fillRect(flag_rect, QColor("#FFFFFF"))
        painter.setBrush(QColor("#BC002D"))
        painter.drawEllipse(flag_rect.center(), 5, 5)

    elif country_code == "CA":  # Canadian flag (simplified)
        painter.fillRect(flag_rect, QColor("#FF0000"))
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))

    elif country_code == "AU":  # Australian flag (simplified)
        painter.fillRect(flag_rect, QColor("#012169"))
        # Cross
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#FFFFFF"))

    elif country_code == "SG":  # Singapore flag (simplified)
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 2), QColor("#ED2939"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 2, flag_width, flag_height // 2), QColor("#FFFFFF"))

    elif country_code == "IN":  # Indian flag (simplified)
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 3), QColor("#FF9933"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 3, flag_width, flag_height // 3), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 2 * flag_height // 3, flag_width, flag_height // 3), QColor("#128807"))

    elif country_code == "BR":  # Brazilian flag (simplified)
        painter.fillRect(flag_rect, QColor("#009739"))
        # Yellow diamond
        points = [
            QPoint(flag_rect.center().x(), flag_rect.top() + 2),
            QPoint(flag_rect.right() - 2, flag_rect.center().y()),
            QPoint(flag_rect.center().x(), flag_rect.bottom() - 2),
            QPoint(flag_rect.left() + 2, flag_rect.center().y())
        ]
        painter.setBrush(QColor("#FFDF00"))
        painter.drawPolygon(points)

    else:  # Default flag pattern
        painter.fillRect(flag_rect, QColor("#CCCCCC"))
        painter.setPen(QColor("#666666"))
        painter.drawText(flag_rect, Qt.AlignmentFlag.AlignCenter, "?")

    # painter.restore()

# ─── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":           "#0f1117",
    "panel":        "#1a1d2e",
    "card":         "#1e2235",
    "accent":       "#6c63ff",
    "accent2":      "#a78bfa",
    "success":      "#22c55e",
    "error":        "#f87171",
    "text":         "#e2e8f0",
    "subtext":      "#64748b",
    "border":       "#2d3150",
    "border_focus": "#6c63ff",
    "entry_bg":     "#151728",
    "btn_hv":       "#7c73ff",
    "label":        "#94a3b8",
}

# ─── Global stylesheet ─────────────────────────────────────────────────────────
STYLESHEET = f"""
QMainWindow, QWidget#central {{
    background: {C['bg']};
}}
QWidget#card {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 12px;
}}
QLabel#section {{
    color: {C['accent2']};
    font-weight: 700;
    font-size: 9pt;
    background: transparent;
}}
QLabel#field {{
    color: {C['subtext']};
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel {{
    color: {C['text']};
    background: transparent;
}}
QLineEdit {{
    background: {C['entry_bg']};
    color: {C['text']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {C['accent']};
}}
QLineEdit:focus {{
    border-color: {C['border_focus']};
}}
QComboBox {{
    background: {C['entry_bg']};
    color: {C['text']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {C['accent']};
}}
QComboBox:focus {{
    border-color: {C['border_focus']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}}
QComboBox QAbstractItemView {{
    background: {C['panel']};
    color: {C['text']};
    border: 1.5px solid {C['border_focus']};
    border-radius: 8px;
    selection-background-color: {C['accent']};
    selection-color: #fff;
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 2px 10px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {C['accent']};
    color: #fff;
}}
QToolTip {{
    background: {C['panel']};
    color: {C['text']};
    border: 1px solid {C['border']};
}}
QPushButton#fetchBtn {{
    background: {C['accent']};
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 26px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#fetchBtn:hover   {{ background: {C['btn_hv']}; }}
QPushButton#fetchBtn:pressed  {{ background: #5a52e0; }}
QPushButton#fetchBtn:disabled {{ background: {C['border']}; color: {C['subtext']}; }}
QPushButton#clearBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#clearBtn:hover  {{ background: {C['border']}; color: {C['text']}; }}
QPushButton#clearBtn:pressed {{ background: #252840; }}
QPushButton#cliproxyBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1px solid #e05252;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: 700;
}}
QPushButton#cliproxyBtn[running="true"] {{
    border: 1px solid #4caf50;
    color: {C['text']};
}}
QPushButton#cliproxyBtn:hover {{ background: {C['border']}; }}
QPushButton#autoCheckBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#autoCheckBtn:hover  {{ background: {C['border']}; color: {C['text']}; }}
QPushButton#autoCheckBtn:pressed {{ background: #252840; }}
QPushButton#autoCheckBtn:checked {{
    background: {C['accent']};
    color: #fff;
    border-color: {C['accent']};
}}
QPushButton#autoCheckBtn:disabled {{
    background: {C['card']};
    color: {C['subtext']};
    border-color: {C['border']};
    opacity: 0.5;
}}
QPushButton#bulkCheckBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#bulkCheckBtn:hover  {{ background: {C['border']}; color: {C['text']}; }}
QPushButton#bulkCheckBtn:pressed {{ background: #252840; }}
QPushButton#bulkCheckBtn:disabled {{ background: {C['card']}; color: {C['subtext']}; border-color: {C['border']}; }}
QPushButton#bulkRefreshBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#bulkRefreshBtn:hover  {{ background: {C['border']}; color: {C['text']}; }}
QPushButton#bulkRefreshBtn:pressed {{ background: #252840; }}
QPushButton#bulkRefreshBtn:disabled {{ background: {C['card']}; color: {C['subtext']}; border-color: {C['border']}; }}
/* ── Proxy card ── */
QWidget#proxyCard {{
    background: {C['card']};
    border: 1.5px solid #3d4270;
    border-radius: 10px;
}}
QWidget#proxyCard:hover {{
    border-color: {C['accent']};
}}
QLabel#proxyIp {{
    color: {C['text']};
    font-family: "Consolas", monospace;
    font-size: 11pt;
    font-weight: 700;
    background: transparent;
}}
QLabel#proxyInfo {{
    color: {C['subtext']};
    font-size: 8pt;
    background: transparent;
}}
QLabel#tagLabel {{
    color: {C['accent2']};
    font-size: 7pt;
    background: transparent;
}}
QLabel#statusUnknown {{
    color: {C['subtext']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusAlive {{
    color: {C['success']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusDead {{
    color: {C['error']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusChecking {{
    color: {C['subtext']};
    font-size: 8pt;
    background: transparent;
    padding: 0 2px;
}}
/* Card action buttons */
QPushButton#cardRefreshBtn {{
    background: transparent;
    color: {C['subtext']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 68px;
}}
QPushButton#cardRefreshBtn:hover   {{ background: {C['accent']}; color: #fff; border-color: {C['accent']}; }}
QPushButton#cardRefreshBtn:pressed  {{ background: #5a52e0; color: #fff; }}
QPushButton#cardRefreshBtn:disabled {{ color: {C['subtext']}; border-color: {C['border']}; opacity: 0.5; }}
QPushButton#cardCheckBtn {{
    background: transparent;
    color: {C['accent2']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 68px;
}}
QPushButton#cardCheckBtn:hover   {{ background: {C['accent']}; color: #fff; border-color: {C['accent']}; }}
QPushButton#cardCheckBtn:pressed  {{ background: #5a52e0; color: #fff; }}
QPushButton#cardCheckBtn:disabled {{ color: {C['subtext']}; border-color: {C['border']}; }}
QPushButton#cardDeleteBtn {{
    background: transparent;
    color: {C['error']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 68px;
}}
QPushButton#cardDeleteBtn:hover   {{ background: {C['error']}; color: #fff; border-color: {C['error']}; }}
QPushButton#cardDeleteBtn:pressed  {{ background: #d05555; color: #fff; }}
QPushButton#cardCopyBtn {{
    background: transparent;
    color: {C['subtext']};
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10pt;
    min-width: 22px;
    max-width: 22px;
}}
QPushButton#cardCopyBtn:hover   {{ color: {C['accent']}; background: {C['border']}; }}
QPushButton#cardCopyBtn:pressed  {{ color: #fff; background: {C['accent']}; }}
/* Result scroll area */
QScrollArea#resultScroll {{
    background: {C['entry_bg']};
    border: 1px solid {C['border']};
    border-radius: 10px;
}}
QScrollArea#resultScroll > QWidget > QWidget {{
    background: {C['entry_bg']};
}}
QScrollBar:vertical {{
    background: {C['entry_bg']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QFrame#divider {{
    background: {C['border']};
    border: none;
}}
QLabel#badge {{
    background: {C['accent']};
    color: #fff;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 8pt;
    font-weight: 700;
}}
"""


# ─── Worker thread ──────────────────────────────────────────────────────────────
class FetchWorker(QObject):
    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, params: dict, api_base: str):
        super().__init__()
        self._params   = params
        self._api_base = api_base

    def run(self):
        try:
            resp = requests.get(self._api_base, params=self._params, timeout=15)
            self.finished.emit(resp)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused – check API server.")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out.")
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Proxy check worker ────────────────────────────────────────────────────────
class ProxyCheckWorker(QObject):
    result = Signal(bool)   # True = alive, False = dead

    TEST_URL = "http://httpbin.org/ip"

    def __init__(self, proxy_str: str):
        super().__init__()
        self._proxy = proxy_str   # "ip:port"

    def run(self):
        try:
            proxies = {
                "http":  f"http://{self._proxy}",
                "https": f"http://{self._proxy}",
            }
            resp = requests.get(self.TEST_URL, proxies=proxies, timeout=8)
            self.result.emit(resp.status_code == 200)
        except Exception:
            self.result.emit(False)


# ─── Refresh worker (re-fetch one proxy slot by its original params) ───────────
class RefreshWorker(QObject):
    finished = Signal(object)   # requests.Response
    error    = Signal(str)

    def __init__(self, params: dict, api_base: str):
        super().__init__()
        self._params   = params
        self._api_base = api_base

    def run(self):
        try:
            resp = requests.get(self._api_base, params=self._params, timeout=15)
            self.finished.emit(resp)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused – check API server.")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out.")
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Proxy Card widget ─────────────────────────────────────────────────────────
class ProxyCard(QWidget):
    """A rich card widget representing one cached proxy entry."""

    deleted         = Signal(object)        # emits self when user deletes
    refreshed       = Signal(object, dict)   # emits (self, new_proxy_dict) after refresh
    auto_check_done = Signal(object)         # emits self when auto-check cycle finished (alive or refresh done)

    def __init__(self, proxy_dict: dict, api_base_fn, parent=None):
        super().__init__(parent)
        self.setObjectName("proxyCard")
        self._proxy_dict  = dict(proxy_dict)
        self._api_base_fn = api_base_fn   # callable → current api base url
        self._refresh_thread = None
        self._refresh_worker = None
        self._check_thread   = None
        self._check_worker   = None
        self._auto_check_triggered  = False
        self._auto_refresh_pending  = False
        self._build()

    # ── accessors ──
    @property
    def proxy_dict(self) -> dict:
        return self._proxy_dict

    def _ip_port(self) -> tuple:
        ip   = self._proxy_dict.get("ip",   self._proxy_dict.get("host", ""))
        port = self._proxy_dict.get("port", "")
        return ip, str(port)

    def _build(self):
        ip, port = self._ip_port()
        proxy_str = f"{ip}:{port}" if ip else "unknown"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(3)

        # ── Row 1: ip:port  +  status badge  +  action buttons ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Group ip label + copy button tightly together
        ip_copy_layout = QHBoxLayout()
        ip_copy_layout.setSpacing(4)
        ip_copy_layout.setContentsMargins(0, 0, 0, 0)
        ip_copy_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._ip_lbl = QLabel(proxy_str)
        self._ip_lbl.setObjectName("proxyIp")
        self._ip_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ip_copy_layout.addWidget(self._ip_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._copy_btn = QPushButton("⧉")
        self._copy_btn.setObjectName("cardCopyBtn")
        self._copy_btn.setToolTip("Copy proxy")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFixedHeight(24)
        ip_copy_layout.addWidget(self._copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        row1.addLayout(ip_copy_layout)
        row1.addStretch(1)

        self._status_lbl = QLabel("● Status: N/A")
        self._status_lbl.setObjectName("statusUnknown")
        row1.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_btn = QPushButton("↻  Renew")
        self._refresh_btn.setObjectName("cardRefreshBtn")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setFixedHeight(28)

        self._check_btn = QPushButton("⚡ Check")
        self._check_btn.setObjectName("cardCheckBtn")
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_btn.setFixedHeight(28)

        self._delete_btn = QPushButton("✕  Delete")
        self._delete_btn.setObjectName("cardDeleteBtn")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setFixedHeight(28)

        row1.addWidget(self._refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self._check_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self._delete_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(row1)

        # ── Row 2: info tags ──
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.setContentsMargins(0, 0, 0, 0)

        meta_fields = [
            ("country", "🌍"),
            ("state",   "📍"),
            ("city",    "🏙️"),
            ("isp",     "📡"),
        ]
        has_tag = False
        for key, icon in meta_fields:
            val = self._proxy_dict.get(key, "")
            if val and str(val).strip():
                tag = QLabel(f"{icon} {val}")
                tag.setObjectName("tagLabel")
                row2.addWidget(tag)
                has_tag = True

        if not has_tag:
            # Fallback: show all non-empty fields
            for k, v in self._proxy_dict.items():
                if k in ("ip", "host") or not v:
                    continue
                tag = QLabel(f"{k}: {v}")
                tag.setObjectName("tagLabel")
                row2.addWidget(tag)

        row2.addStretch()
        outer.addLayout(row2)

        # ── Wire signals ──
        self._check_btn.clicked.connect(self._do_check)
        self._refresh_btn.clicked.connect(self._do_refresh)
        self._delete_btn.clicked.connect(self._do_delete)
        self._copy_btn.clicked.connect(self._do_copy)

    def update_button_visibility(self, auto_check_enabled: bool):
        """Update visibility of check and refresh buttons based on auto-check state."""
        # Hide check and refresh buttons when auto-check is enabled
        self._check_btn.setVisible(not auto_check_enabled)
        self._refresh_btn.setVisible(not auto_check_enabled)

    # ── Copy ──
    def _do_copy(self):
        ip, port = self._ip_port()
        proxy_str = f"{ip}:{port}" if ip else "unknown"
        QApplication.clipboard().setText(proxy_str)
        self._copy_btn.setText("✓")
        QTimer.singleShot(1500, lambda: self._copy_btn.setText("⧉"))

    # ── Delete ──
    def _do_delete(self):
        ip, port = self._ip_port()
        delete_proxy_from_file(ip, port)
        self.deleted.emit(self)

    # ── Check ──
    def _do_check(self):
        ip, port = self._ip_port()
        if not ip:
            return
        proxy_str = f"{ip}:{port}"
        self._check_btn.setEnabled(False)
        self._status_lbl.setObjectName("statusChecking")
        self._status_lbl.setText("… checking")
        self._status_lbl.setStyleSheet("")   # force re-read from QSS

        self._check_thread = QThread()
        self._check_worker = ProxyCheckWorker(proxy_str)
        self._check_worker.moveToThread(self._check_thread)
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.result.connect(self._on_check_result)
        self._check_worker.result.connect(self._check_thread.quit)
        self._check_thread.start()

    def _on_check_result(self, alive: bool):
        self._check_btn.setEnabled(True)
        if alive:
            self._status_lbl.setObjectName("statusAlive")
            self._status_lbl.setText("● Alive")
            was_auto = self._auto_check_triggered
            self._auto_check_triggered = False  # Reset flag
            if was_auto:
                self.auto_check_done.emit(self)  # Notify: cycle done, proxy is alive
        else:
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ Dead")
            # Auto-refresh if this check was triggered automatically
            if self._auto_check_triggered:
                self._auto_check_triggered = False  # Reset flag
                # Small delay before auto-refresh to avoid overwhelming the API
                self._auto_refresh_pending = True
                QTimer.singleShot(1000, self._do_refresh)
                # auto_check_done will be emitted after refresh finishes
        # Force QSS re-evaluation after objectName change
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    # ── Refresh ──
    def _do_refresh(self):
        # Build API params from metadata stored in proxy_dict
        port = self._proxy_dict.get("port", "")

        params = {
            "country": self._proxy_dict.get("country", ""),
            "state":   self._proxy_dict.get("state",   ""),
            "city":    self._proxy_dict.get("_city",   ""),
            "postal":  self._proxy_dict.get("postal",  ""),
            "isp":     self._proxy_dict.get("isp",     ""),
            "start":   str(port) if port else "40000",
            "num":     "1",
            "ip":      "",
        }

        self._refresh_btn.setEnabled(False)
        self._status_lbl.setObjectName("statusChecking")
        self._status_lbl.setText("… fetching")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

        self._refresh_thread = QThread()
        self._refresh_worker = RefreshWorker(params, self._api_base_fn())
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.finished.connect(self._on_refresh_done)
        self._refresh_worker.error.connect(self._on_refresh_error)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.error.connect(self._refresh_thread.quit)
        self._refresh_thread.start()

    def _on_refresh_done(self, resp):
        self._refresh_btn.setEnabled(True)
        was_auto = self._auto_refresh_pending
        self._auto_refresh_pending = False
        if resp.status_code != 200:
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText(f"✕ HTTP {resp.status_code}")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        content_type = resp.headers.get('content-type', '').lower()
        try:
            text = resp.text.strip()
            data = None

            # Try JSON parse first
            if 'json' in content_type:
                try:
                    data = resp.json()
                    if isinstance(data, str):
                        ip, port = data.split(':', 1) if ':' in data else (data, '')
                        data = {"ip": ip, "port": port}
                except Exception:
                    data = None  # fallback to plain text

            # Plain text / JSON parse failed → try "ip:port" format
            if data is None:
                if ':' in text:
                    ip, port = text.split(':', 1)
                    data = {"ip": ip.strip(), "port": port.strip()}
                else:
                    self._status_lbl.setObjectName("statusDead")
                    self._status_lbl.setText("✕ Bad format")
                    self._status_lbl.style().unpolish(self._status_lbl)
                    self._status_lbl.style().polish(self._status_lbl)
                    if was_auto:
                        self.auto_check_done.emit(self)
                    return
        except Exception as e:
            print(f"[DEBUG] Refresh parse error: {e}")
            print(f"[DEBUG] Refresh response text: {resp.text[:500]}...")
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ Bad JSON")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        # Extract first proxy from response
        new_proxy: dict | None = None
        if isinstance(data, list) and data:
            new_proxy = data[0] if isinstance(data[0], dict) else None
        elif isinstance(data, dict):
            new_proxy = data

        if not new_proxy:
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ No result")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        # Preserve metadata from old entry
        for meta_key in ("country", "state", "city", "postal", "isp", "_city"):
            if meta_key not in new_proxy and meta_key in self._proxy_dict:
                new_proxy[meta_key] = self._proxy_dict[meta_key]

        # Delete old proxy from cache, save new one
        old_ip, old_port = self._ip_port()
        delete_proxy_from_file(old_ip, old_port)
        save_proxies_to_file([new_proxy])

        # Notify auto-check cycle before emitting refreshed (card will be destroyed)
        if was_auto:
            self.auto_check_done.emit(self)
        self.refreshed.emit(self, new_proxy)

    def _on_refresh_error(self, msg: str):
        self._refresh_btn.setEnabled(True)
        was_auto = self._auto_refresh_pending
        self._auto_refresh_pending = False
        self._status_lbl.setObjectName("statusDead")
        self._status_lbl.setText("✕ Error")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)
        if was_auto:
            self.auto_check_done.emit(self)


# ─── Autocomplete ComboBox ──────────────────────────────────────────────────────
class HighlightDelegate(QStyledItemDelegate):
    """Custom delegate to highlight matching text in dropdown items."""

    def __init__(self, combo_box, parent=None):
        super().__init__(parent)
        self.combo_box = combo_box
        self.highlight_color = QColor(C['accent'])
        self.match_text = ""

    def set_match_text(self, text: str):
        self.match_text = text.lower()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().paint(painter, option, index)

        # Check if this is the currently selected item
        is_selected = (index.row() == self.combo_box.currentIndex())

        # Check if this is area code combo box
        is_area_combo = self.combo_box.objectName() == "area_cb"

        # For area combo, show text with flag icon
        display_text = text
        if is_area_combo:
            display_text = f"  {text}"  # Add space for flag icon

        # Check if we need to highlight
        if self.match_text and self.match_text in text.lower():
            # Draw highlighted background for the entire item
            painter.fillRect(option.rect, self.highlight_color)

            # Draw border radius
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.highlight_color)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 4, 4)

            # Draw flag icon if area combo
            if is_area_combo and text:
                draw_country_flag(painter, text, option.rect)

            # Draw text in white
            painter.setPen(QColor("#ffffff"))
            text_rect = option.rect.adjusted(35, 0, -30, 0)  # Leave space for flag and check mark
            painter.drawText(text_rect,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           display_text)

            # Draw check mark if selected
            if is_selected:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                painter.drawText(option.rect.adjusted(0, 0, -10, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               "✓")
        else:
            # No highlighting needed, use default painting but add check mark if selected
            # Draw default background
            super().paint(painter, option, index)

            # Draw flag icon if area combo
            if is_area_combo and text:
                draw_country_flag(painter, text, option.rect)

            # Override text with spacing if area combo
            if is_area_combo:
                # Clear the original text area and redraw
                painter.setPen(option.palette.color(option.palette.ColorRole.Text))
                text_rect = option.rect.adjusted(35, 0, -30, 0)  # Leave space for flag and check mark
                painter.fillRect(text_rect, option.backgroundBrush)  # Clear background
                painter.drawText(text_rect,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               display_text)

            if is_selected:
                # Draw check mark on default background
                painter.setPen(QColor(C['accent']))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                painter.drawText(option.rect.adjusted(0, 0, -10, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               "✓")
class AutoComboBox(QComboBox):
    """Editable QComboBox with live contains-filtering via QCompleter."""

    POPUP_STYLE = f"""
        QAbstractItemView {{
            background: {C['panel']};
            color: {C['text']};
            border: 1.5px solid {C['border_focus']};
            border-radius: 8px;
            selection-background-color: {C['accent']};
            selection-color: #fff;
            padding: 4px;
            outline: none;
        }}
        QAbstractItemView::item {{
            min-height: 28px;
            padding: 2px 10px;
            border-radius: 4px;
        }}
        QAbstractItemView::item:hover {{
            background: {C['accent']};
            color: #fff;
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(12)

        self._model = QStringListModel(self)
        self.setModel(self._model)

        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setMaxVisibleItems(12)
        self.setCompleter(self._completer)

        # Create and set custom delegate for highlighting
        self._highlight_delegate = HighlightDelegate(self)
        self._completer.popup().setItemDelegate(self._highlight_delegate)
        self.view().setItemDelegate(self._highlight_delegate)  # Also set for combo box dropdown
        self._completer.popup().setStyleSheet(self.POPUP_STYLE)

        # Connect text changes to update highlighting
        self.editTextChanged.connect(self._update_highlight)

        # Custom arrow label
        self._arrow = QLabel("▼", self)
        self._arrow.setStyleSheet(f"""
            color: {C['text']};
            font-size: 12pt;
            font-weight: bold;
            background: transparent;
            padding: 0px;
        """)
        self._arrow.setFixedSize(20, 20)
        self._arrow.move(self.width() - 30, (self.height() - 20) // 2)
        self._arrow.show()

        # Update arrow position on resize
        self.resizeEvent = self._on_resize

    def _on_resize(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_arrow'):
            self._arrow.move(self.width() - 30, (self.height() - 20) // 2)

    def _update_highlight(self, text: str):
        """Update the highlight text for the delegate."""
        current_match = self._highlight_delegate.match_text
        new_match = text.strip().lower()
        if current_match != new_match:
            self._highlight_delegate.set_match_text(new_match)
            # Force repaint of the popup
            if self._completer.popup().isVisible():
                self._completer.popup().viewport().update()

    def set_items(self, items: list):
        self._model.setStringList(list(items))

    def current_value(self) -> str:
        return self.currentText().strip()

    def focusInEvent(self, event):
        """Show popup when focusing on combo box."""
        super().focusInEvent(event)
        if not self.view().isVisible():
            self.showPopup()


# ─── Main window ───────────────────────────────────────────────────────────────
class ProxyApp(QMainWindow):
    _status_sig = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxer - Auto retrieve proxies network carrier from Cliproxy")
        self.setFixedSize(760, 720)
        self._status_sig.connect(self._apply_status)
        self._auto_check_enabled = False
        self._auto_check_timer = QTimer()
        self._auto_check_timer.setSingleShot(True)   # fire once; restarted manually after cycle
        self._auto_check_timer.timeout.connect(self._auto_check_all_proxies)
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._countdown_remaining = 30
        self._auto_check_pending = 0   # number of cards still being processed in current cycle
        self._build_ui()
        self._center()
        self._set_defaults()
        self._toggle_auto_check()  # Enable auto-check by default

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def _set_defaults(self):
        # Set default values: Area Code = US, State = Florida, Network = ATT
        self._area_cb.setCurrentText("US")
        self._on_country_change("US")  # Manually trigger to populate state dropdown
        self._state_cb.setCurrentText("Florida")
        self._on_state_change("Florida")  # Manually trigger to populate city dropdown
        self._network_cb.setCurrentText("ATT")
        self._port_edit.setText("2000")
        # Prevent auto-focus on API URL input
        self._fetch_btn.setFocus()

    # ── Build UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("central")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(16, 22, 14, 20)
        main.setSpacing(0)

        # ── API Base URL bar ─────────────────────────────────────────────────
        api_bar = QHBoxLayout(); api_bar.setSpacing(8)
        api_lbl = QLabel("🔗 API URL:")
        api_lbl.setStyleSheet(f"color: {C['label']}; font-size: 9pt; font-weight: 700; background: transparent;")
        api_lbl.setFixedWidth(72)
        self._api_edit = QLineEdit(load_api_base())
        self._api_edit.setPlaceholderText("http://host:port")
        self._api_edit.setFixedHeight(34)
        self._api_save_btn = QPushButton("Save")
        self._api_save_btn.setObjectName("clearBtn")
        self._api_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._api_save_btn.setFixedSize(70, 36)
        self._api_save_btn.clicked.connect(self._save_api_base_manual)
        self._api_edit.returnPressed.connect(self._save_api_base)
        self._api_edit.editingFinished.connect(self._save_api_base)

        self._cliproxy_btn = QPushButton("Cliproxy")
        self._cliproxy_btn.setObjectName("cliproxyBtn")
        self._cliproxy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cliproxy_btn.setFixedSize(80, 36)
        self._cliproxy_btn.setToolTip("Click to check Cliproxy status")
        self._cliproxy_btn.clicked.connect(self._check_cliproxy)

        api_bar.addWidget(api_lbl)
        api_bar.addWidget(self._api_edit, 1)
        api_bar.addWidget(self._api_save_btn)
        api_bar.addWidget(self._cliproxy_btn)
        main.addLayout(api_bar)
        main.addSpacing(10)

        # ── Cliproxy status auto-refresh timer ───────────────────────────────
        self._cliproxy_timer = QTimer(self)
        self._cliproxy_timer.setInterval(3000)
        self._cliproxy_timer.timeout.connect(self._check_cliproxy_silent)
        self._cliproxy_timer.start()
        self._check_cliproxy_silent()  # initial check

        # ── Form card (full width) ──────────────────────────────────────────────
        card = QWidget(); card.setObjectName("card")
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(20, 18, 20, 18)
        card_v.setSpacing(0)

        # Grid 1 — Location (3 cols)
        g1 = QGridLayout()
        g1.setHorizontalSpacing(12); g1.setVerticalSpacing(6)
        for i in range(3): g1.setColumnStretch(i, 1)

        self._fld_lbl(g1, "AREA CODE",        0, 1)
        self._fld_lbl(g1, "STATE / PROVINCE", 1, 1)
        self._fld_lbl(g1, "NETWORK / ISP",    2, 1)

        self._area_cb = AutoComboBox()
        self._area_cb.setObjectName("area_cb")
        self._area_cb.set_items(list(COUNTRY_DATA.keys()))
        self._area_cb.setPlaceholderText("e.g. US")
        self._area_cb.currentTextChanged.connect(self._on_country_change)
        g1.addWidget(self._area_cb, 2, 0)

        self._state_cb = AutoComboBox()
        self._state_cb.setPlaceholderText("Any")
        self._state_cb.currentTextChanged.connect(self._on_state_change)
        g1.addWidget(self._state_cb, 2, 1)

        self._network_cb = AutoComboBox()
        self._network_cb.set_items(ALL_NETWORKS)
        self._network_cb.setPlaceholderText("Any")
        g1.addWidget(self._network_cb, 2, 2)

        card_v.addLayout(g1)
        card_v.addSpacing(14)

        # Grid 2 — Query Options (3 cols)
        g2 = QGridLayout()
        g2.setHorizontalSpacing(12); g2.setVerticalSpacing(6)
        for i in range(3): g2.setColumnStretch(i, 1)

        # sec2 = QLabel("⚙️  Query Options"); sec2.setObjectName("section")
        # g2.addWidget(sec2, 0, 0, 1, 3)
        self._fld_lbl(g2, "PORT",              0, 1)
        self._fld_lbl(g2, "NUMBER OF RESULTS", 1, 1)
        self._fld_lbl(g2, "CITY",      2, 1)

        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("e.g. 2000")
        g2.addWidget(self._port_edit, 2, 0)

        self._number_edit = QLineEdit("1")
        g2.addWidget(self._number_edit, 2, 1)

        self._city_cb = AutoComboBox()
        self._city_cb.setPlaceholderText("Any")
        g2.addWidget(self._city_cb, 2, 2)

        card_v.addLayout(g2)
        main.addWidget(card)
        main.addSpacing(12)

        # ── Action bar (full width, 2 buttons) ───────────────────────────────
        act = QHBoxLayout(); act.setSpacing(10)

        self._fetch_btn = QPushButton("🔍 Retrieve")
        self._fetch_btn.setObjectName("fetchBtn")
        self._fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fetch_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fetch_btn.setFixedHeight(36)
        self._fetch_btn.clicked.connect(self._fetch)

        self._clear_cache_btn = QPushButton("🗑 Reset")
        self._clear_cache_btn.setObjectName("clearBtn")
        self._clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_cache_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._clear_cache_btn.setFixedHeight(36)
        self._clear_cache_btn.clicked.connect(self._clear_cache)

        self._auto_check_btn = QPushButton()
        self._auto_check_btn.setObjectName("autoCheckBtn")
        self._auto_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_check_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._auto_check_btn.setFixedHeight(36)
        auto_check_layout = QHBoxLayout(self._auto_check_btn)
        auto_check_layout.setContentsMargins(10, 0, 0, 0)
        auto_check_layout.setSpacing(0)
        self._auto_check_label = QLabel("⏰ Auto mode:")
        self._auto_check_label.setStyleSheet(f"color: {C['label']}; background: transparent;")
        self._auto_check_status = QLabel("OFF")
        self._auto_check_status.setStyleSheet(f"color: {C['subtext']}; background: transparent;")
        auto_check_layout.addWidget(self._auto_check_label)
        auto_check_layout.addSpacing(2)
        auto_check_layout.addWidget(self._auto_check_status)
        auto_check_layout.addStretch()
        self._auto_check_btn.clicked.connect(self._toggle_auto_check)

        self._bulk_check_btn = QPushButton("⚡Bulk check")
        self._bulk_check_btn.setObjectName("bulkCheckBtn")
        self._bulk_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bulk_check_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._bulk_check_btn.setFixedHeight(36)
        self._bulk_check_btn.setEnabled(False)
        self._bulk_check_btn.clicked.connect(self._bulk_check)

        self._bulk_refresh_btn = QPushButton("🔄️ Bulk refresh")
        self._bulk_refresh_btn.setObjectName("bulkRefreshBtn")
        self._bulk_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bulk_refresh_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._bulk_refresh_btn.setFixedHeight(36)
        self._bulk_refresh_btn.setEnabled(False)
        self._bulk_refresh_btn.clicked.connect(self._bulk_refresh)

        act.addWidget(self._fetch_btn, 2)
        act.addWidget(self._clear_cache_btn, 1)
        act.addWidget(self._bulk_check_btn, 1)
        act.addWidget(self._bulk_refresh_btn, 1)
        act.addWidget(self._auto_check_btn, 2)
        main.addLayout(act)
        main.addSpacing(6)

        div0 = QFrame(); div0.setObjectName("divider"); div0.setFixedHeight(1)
        main.addWidget(div0)
        main.addSpacing(14)

        # ── Result section ────────────────────────────────────────────────────
        res_bar = QHBoxLayout()
        self._res_count_lbl = QLabel("0 proxies")
        self._res_count_lbl.setStyleSheet(
            f"color: {C['accent2']}; font-size: 8pt; font-weight: 700; background: transparent;")

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color: {C['subtext']}; font-size: 8pt; background: transparent;")

        res_bar.addWidget(self._res_count_lbl)
        res_bar.addStretch()
        res_bar.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignRight)
        main.addLayout(res_bar)
        main.addSpacing(4)

        # Scroll area containing a VBox of proxy cards
        self._scroll = QScrollArea()
        self._scroll.setObjectName("resultScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._result_container = QWidget()
        self._result_container.setStyleSheet(f"background: {C['entry_bg']};")
        self._result_layout = QVBoxLayout(self._result_container)
        self._result_layout.setContentsMargins(10, 10, 10, 10)
        self._result_layout.setSpacing(8)
        self._result_layout.addStretch()

        self._scroll.setWidget(self._result_container)
        main.addWidget(self._scroll, 1)

        # Load cached proxies on startup
        self._load_cached_proxies()

    # ── Helper label factories ───────────────────────────────────────────────
    def _sec_lbl(self, grid, text, col, row, span=1):
        lbl = QLabel(text); lbl.setObjectName("section")
        grid.addWidget(lbl, row, col, 1, span)

    def _fld_lbl(self, grid, text, col, row):
        lbl = QLabel(text); lbl.setObjectName("field")
        grid.addWidget(lbl, row, col)

    # ── Country cascade ──────────────────────────────────────────────────────
    def _on_country_change(self, text: str):
        data     = COUNTRY_DATA.get(text.strip().upper(), {})
        states   = data.get("states",   [])
        networks = data.get("networks", ALL_NETWORKS)
        self._state_cb.set_items(states)
        self._network_cb.set_items(networks)
        # Reset city when country changes
        self._city_cb.set_items([])

    def _on_state_change(self, text: str):
        country  = self._area_cb.current_value().strip().upper()
        data     = COUNTRY_DATA.get(country, {})
        cities_map = data.get("cities", {})
        cities   = cities_map.get(text.strip(), [])
        self._city_cb.set_items(cities)

    # ── API Base ─────────────────────────────────────────────────────────────
    def _save_api_base(self, show_status: bool = False):
        url = self._api_edit.text().strip()
        if not url:
            return
        save_api_base(url)
        if show_status:
            self._set_status("✓  API URL saved", C['success'])

    def _is_cliproxy_running(self) -> bool:
        """Return True if Cliproxy.exe process is running."""
        import subprocess
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq Cliproxy.exe"],
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            ).decode(errors="ignore")
            return "cliproxy" in output.lower()
        except Exception:
            return False

    def _update_cliproxy_btn(self, running: bool):
        """Update button border color based on Cliproxy running state."""
        self._cliproxy_btn.setProperty("running", "true" if running else "false")
        self._cliproxy_btn.setToolTip(
            "Cliproxy is running ✔" if running else "Cliproxy is NOT running ✖"
        )
        self._cliproxy_btn.style().unpolish(self._cliproxy_btn)
        self._cliproxy_btn.style().polish(self._cliproxy_btn)

    def _check_cliproxy_silent(self):
        """Auto-check called by timer — no status bar update."""
        self._update_cliproxy_btn(self._is_cliproxy_running())

    def _check_cliproxy(self):
        """Manual check when user clicks the button."""
        running = self._is_cliproxy_running()
        self._update_cliproxy_btn(running)
        if running:
            self._set_status("✔  Cliproxy is running", C['success'])
        else:
            self._set_status("✖  Cliproxy is NOT running", "#e05252")

    def _save_api_base_manual(self):
        url = self._api_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "API URL cannot be empty.")
            return
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "Invalid URL", "API URL must start with http:// or https://")
            return
        if '://' not in url or url.count('://') != 1:
            QMessageBox.warning(self, "Invalid URL", "Invalid URL format.")
            return
        save_api_base(url)
        self._set_status("✓  API URL saved", C['success'])

    # ── Fetch ────────────────────────────────────────────────────────────────
    def _fetch(self):
        country = self._area_cb.current_value().upper()
        if not country:
            QMessageBox.warning(self, "Missing field",
                                "Please enter an Area Code (country).")
            return

        port = self._port_edit.text().strip()

        params = {
            "country": country,
            "state":   self._state_cb.current_value(),
            "city":    self._city_cb.current_value() or "",
            "postal":  "",
            "isp":     self._network_cb.current_value(),
            "start":   port or "2000",
            "num":     self._number_edit.text().strip() or "1",
            "ip":      "",
        }

        # Stash form params so they can be embedded into the saved proxy dict
        self._last_fetch_params = params

        self._set_status("⏳ Fetching…", C['subtext'])
        self._fetch_btn.setEnabled(False)

        self._thread = QThread()
        api_base = self._api_edit.text().strip() or load_api_base()
        self._worker = FetchWorker(params, normalize_api_base_for_requests(api_base))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._handle_response)
        self._worker.error.connect(self._show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _handle_response(self, resp):
        self._fetch_btn.setEnabled(True)
        code = resp.status_code
        content_type = resp.headers.get('content-type', '').lower()

        if code == 200:
            self._set_status(f"✓  {code} OK", C['success'])
            try:
                text = resp.text.strip()
                data = None

                # Try JSON parse first
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        if isinstance(data, str):
                            # JSON string containing "ip:port"
                            ip, port = data.split(':', 1) if ':' in data else (data, '')
                            data = [{"ip": ip, "port": port}]
                    except Exception:
                        data = None  # fallback to plain text

                # Plain text / JSON parse failed → try "ip:port" format
                if data is None:
                    if ':' in text:
                        # Could be multiple lines of ip:port
                        proxies = []
                        for line in text.splitlines():
                            line = line.strip()
                            if ':' in line:
                                ip, port = line.split(':', 1)
                                proxies.append({"ip": ip.strip(), "port": port.strip()})
                        data = proxies if proxies else None

                if data is None:
                    self._add_info_row(f"Unexpected response: {text[:200]}")
                    self._set_status("⚠  Unexpected format", C['subtext'])
                    return

                self._render_json(data, resp.url)
            except Exception as e:
                print(f"[DEBUG] Parse error: {e}")
                print(f"[DEBUG] Response text: {resp.text[:500]}...")
                self._add_info_row(f"Parse error: {str(e)[:100]}...")
                self._set_status("✗  Parse error", C['error'])
        else:
            print(f"[DEBUG] HTTP {code} error: {resp.text[:500]}...")
            self._add_info_row(f"HTTP {code}: {resp.text[:200]}...", is_error=True)
            self._set_status(f"✗  HTTP {code}", C['error'])

    def _show_error(self, msg: str):
        self._fetch_btn.setEnabled(True)
        self._set_status(f"✗  {msg}", C['error'])

    # ── Result rendering ─────────────────────────────────────────────────────
    def _clear_rows(self):
        """Remove all proxy cards from the result layout (keep trailing stretch)."""
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._result_container.update()

    def _render_json(self, data, url: str):
        proxies_to_save = []
        params = getattr(self, "_last_fetch_params", {})

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    proxies_to_save.append(item)
        elif isinstance(data, dict):
            proxies_to_save.append(data)

        if not proxies_to_save:
            self._set_status("⚠  No proxy in response", C['subtext'])
            return

        # Embed form params as metadata into each proxy dict before saving
        for p in proxies_to_save:
            p.setdefault("country", params.get("country", ""))
            p.setdefault("state",   params.get("state",   ""))
            p.setdefault("city",    params.get("city",    ""))
            p.setdefault("isp",     params.get("isp",     ""))
            p["_city"] = params.get("city", "")

        save_proxies_to_file(proxies_to_save)
        # Reload full list so UI is consistent with cache
        self._load_cached_proxies()
        self._set_status(f"✓  Added {len(proxies_to_save)} proxy(ies)", C['success'])

    def _load_cached_proxies(self):
        """Load and display cached proxies."""
        cached = load_proxies_from_file()
        self._clear_rows()
        if cached:
            for proxy in cached:
                self._add_proxy_card(proxy)
        # Update result header count
        self._res_count_lbl.setText(f"{len(cached)} proxies")
        self._update_auto_check_btn_state(len(cached))

    def _add_info_row(self, text: str, color: str = None, is_error: bool = False):
        lbl = QLabel(text)
        lbl.setObjectName("proxyText")
        lbl.setWordWrap(True)
        c = color or (C['error'] if is_error else C['subtext'])
        lbl.setStyleSheet(f"color: {c}; font-size: 9pt; background: transparent; padding: 4px 8px;")
        self._result_layout.insertWidget(self._result_layout.count() - 1, lbl)

    def _add_proxy_card(self, proxy_dict: dict):
        card = ProxyCard(proxy_dict, lambda: normalize_api_base_for_requests(self._api_edit.text().strip() or load_api_base()))
        card.deleted.connect(self._on_card_deleted)
        card.refreshed.connect(self._on_card_refreshed)
        card.auto_check_done.connect(self._on_auto_check_card_done)
        card.update_button_visibility(self._auto_check_enabled)  # Set initial visibility
        self._result_layout.insertWidget(self._result_layout.count() - 1, card)
        count = self._result_layout.count() - 1  # exclude stretch
        self._update_auto_check_btn_state(count)

    def _on_card_deleted(self, card: ProxyCard):
        self._result_layout.removeWidget(card)
        card.deleteLater()
        # Update count
        count = self._result_layout.count() - 1  # exclude stretch
        self._res_count_lbl.setText(f"{count} proxies")
        self._update_auto_check_btn_state(count)

    def _on_card_refreshed(self, old_card: ProxyCard, new_proxy: dict):
        """Replace old card in-place with a new one after refresh."""
        idx = self._result_layout.indexOf(old_card)
        self._result_layout.removeWidget(old_card)
        old_card.deleteLater()

        new_card = ProxyCard(new_proxy, lambda: normalize_api_base_for_requests(self._api_edit.text().strip() or load_api_base()))
        new_card.deleted.connect(self._on_card_deleted)
        new_card.refreshed.connect(self._on_card_refreshed)
        new_card.auto_check_done.connect(self._on_auto_check_card_done)
        new_card.update_button_visibility(self._auto_check_enabled)  # Set visibility for new card
        self._result_layout.insertWidget(idx, new_card)

    # ── Status (thread-safe) ─────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self._status_sig.emit(msg, color)

    def _apply_status(self, msg: str, color: str):
        # Don't override countdown display when auto-check is enabled
        if not self._auto_check_enabled:
            self._status_lbl.setText(msg)
            self._status_lbl.setStyleSheet(
                f"color: {color}; font-size: 8pt; background: transparent;")
        # When auto-check is enabled, only update if it's not a countdown message
        elif not msg.startswith("⏰"):
            # Temporarily show the message, but countdown will override it
            self._status_lbl.setText(msg)
            self._status_lbl.setStyleSheet(
                f"color: {color}; font-size: 8pt; background: transparent;")

    def _toggle_auto_check(self):
        """Toggle automatic proxy checking every 30 seconds."""
        self._auto_check_enabled = not self._auto_check_enabled
        if self._auto_check_enabled:
            self._auto_check_pending = 0
            self._auto_check_timer.start(30000)  # 30 seconds (singleShot)
            self._countdown_remaining = 30
            self._countdown_timer.start(1000)  # Update every second
            self._auto_check_status.setText("ON")
            self._auto_check_status.setStyleSheet(f"color: {C['success']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", True)
            self._update_countdown_display()
        else:
            self._auto_check_pending = 0
            self._auto_check_timer.stop()
            self._countdown_timer.stop()
            self._auto_check_status.setText("OFF")
            self._auto_check_status.setStyleSheet(f"color: {C['subtext']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", False)
            self._set_status("", C['subtext'])  # Clear countdown display
        # Force style update
        self._auto_check_btn.style().unpolish(self._auto_check_btn)
        self._auto_check_btn.style().polish(self._auto_check_btn)

        # Update visibility of buttons on all proxy cards
        self._update_all_proxy_cards_visibility()

    def _update_countdown(self):
        """Update countdown timer display."""
        self._countdown_remaining -= 1
        if self._countdown_remaining < 0:
            self._countdown_remaining = 0
        self._update_countdown_display()

    def _update_countdown_display(self):
        """Update the countdown display in status label."""
        if self._auto_check_enabled:
            self._status_lbl.setText(f"⏰ Next check in {self._countdown_remaining}s")
            self._status_lbl.setStyleSheet(f"color: {C['accent']}; font-size: 8pt; background: transparent;")
        else:
            self._status_lbl.setText("")
            self._status_lbl.setStyleSheet(f"color: {C['subtext']}; font-size: 8pt; background: transparent;")

    def _update_all_proxy_cards_visibility(self):
        """Update button visibility on all proxy cards based on auto-check state."""
        count = self._result_layout.count()
        for i in range(count - 1):  # -1 to skip the stretch
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, 'update_button_visibility'):
                    widget.update_button_visibility(self._auto_check_enabled)

    def _update_auto_check_btn_state(self, count: int = None):
        """Enable/disable the Auto Check button based on whether there are proxy cards."""
        if count is None:
            count = self._result_layout.count() - 1  # exclude stretch
        has_proxies = count > 0
        self._auto_check_btn.setEnabled(has_proxies)
        self._bulk_check_btn.setEnabled(has_proxies)
        self._bulk_refresh_btn.setEnabled(has_proxies)
        if not has_proxies and self._auto_check_enabled:
            # Turn off auto check if list becomes empty
            self._auto_check_enabled = False
            self._auto_check_timer.stop()
            self._countdown_timer.stop()
            self._auto_check_status.setText("OFF")
            self._auto_check_status.setStyleSheet(f"color: {C['subtext']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", False)
            self._auto_check_btn.style().unpolish(self._auto_check_btn)
            self._auto_check_btn.style().polish(self._auto_check_btn)
            self._update_all_proxy_cards_visibility()

    def _auto_check_all_proxies(self):
        """Automatically check all proxy cards and refresh dead ones."""
        # Stop countdown while we are processing (restart after all done)
        self._countdown_timer.stop()
        self._status_lbl.setText("⚡ Checking…")
        self._status_lbl.setStyleSheet(f"color: {C['accent2']}; font-size: 8pt; background: transparent;")

        # Iterate through all widgets in the result layout
        count = self._result_layout.count()
        if count <= 1:  # Only stretch item or empty
            self._restart_auto_check_timer()
            return

        cards = []
        for i in range(count - 1):  # -1 to skip the stretch
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_auto_check_triggered') and hasattr(widget, '_do_check'):
                    cards.append(widget)

        if not cards:
            self._restart_auto_check_timer()
            return

        self._auto_check_pending = len(cards)
        for widget in cards:
            widget._auto_check_triggered = True
            widget._do_check()

    def _on_auto_check_card_done(self, card):
        """Called when a single card finishes its auto-check cycle (alive or refresh done)."""
        self._auto_check_pending = max(0, self._auto_check_pending - 1)
        if self._auto_check_pending == 0:
            # All cards finished → restart the timer for the next cycle
            self._restart_auto_check_timer()

    def _restart_auto_check_timer(self):
        """Restart countdown and schedule the next auto-check cycle."""
        if not self._auto_check_enabled:
            return
        self._countdown_remaining = 30
        self._countdown_timer.start(1000)
        self._auto_check_timer.start(30000)  # singleShot fires after 30 s
        self._update_countdown_display()

    def _bulk_check(self):
        """Check all proxy cards at once."""
        count = self._result_layout.count()
        if count <= 1:
            return
        checked = 0
        for i in range(count - 1):
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_do_check'):
                    widget._auto_check_triggered = False
                    widget._do_check()
                    checked += 1
        if checked:
            self._set_status(f"⚡ Checking {checked} proxies…", C['accent2'])

    def _bulk_refresh(self):
        """Refresh all proxy cards at once."""
        count = self._result_layout.count()
        if count <= 1:
            return
        refreshed = 0
        for i in range(count - 1):
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_do_refresh'):
                    widget._do_refresh()
                    refreshed += 1
        if refreshed:
            self._set_status(f"↻ Refreshing {refreshed} proxies…", C['accent2'])

    def _clear_cache(self):
        """Wipe all saved proxies and clear the result view."""
        reply = QMessageBox.question(
            self, "Clear Cache",
            "Xóa toàn bộ proxy đã lưu?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            data = _load_app_data()
            data["proxies"] = []
            _save_app_data(data)
        except Exception as e:
            print(f"Error clearing cache: {e}")
        self._clear_rows()
        self._res_count_lbl.setText("0 proxies")
        self._set_status("🗑  Cache cleared", C['subtext'])
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    icon_path = os.path.join(_BUNDLE_DIR, "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    app.setFont(QFont("Segoe UI", 10))
    win = ProxyApp()
    win.show()
    sys.exit(app.exec())
