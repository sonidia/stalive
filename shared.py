PALETTE = {
    "bg":           "#0f1117",
    "panel":        "#1a1d2e",
    "card":         "#1e2235",
    "accent":       "#6c63ff",
    "accent2":      "#a78bfa",
    "success":      "#22c55e",
    "warning":      "#f59e0b",
    "error":        "#f87171",
    "text":         "#e2e8f0",
    "subtext":      "#64748b",
    "border":       "#2d3150",
    "border_focus": "#6c63ff",
    "entry_bg":     "#151728",
    "btn_hv":       "#7c73ff",
    "label":        "#94a3b8",
}

STYLESHEET = f"""
QMainWindow, QWidget#central {{
    background: {PALETTE['bg']};
}}
QWidget#card {{
    background: {PALETTE['card']};
    border: 1px solid {PALETTE['border']};
    border-radius: 12px;
}}
QLabel#section {{
    color: {PALETTE['accent2']};
    font-weight: 700;
    font-size: 9pt;
    background: transparent;
}}
QLabel#field {{
    color: {PALETTE['subtext']};
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel {{
    color: {PALETTE['text']};
    background: transparent;
}}
QLineEdit {{
    background: {PALETTE['entry_bg']};
    color: {PALETTE['text']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {PALETTE['accent']};
}}
QLineEdit:focus {{
    border-color: {PALETTE['border_focus']};
}}
QComboBox {{
    background: {PALETTE['entry_bg']};
    color: {PALETTE['text']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {PALETTE['accent']};
}}
QComboBox:focus {{
    border-color: {PALETTE['border_focus']};
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
    background: {PALETTE['panel']};
    color: {PALETTE['text']};
    border: 1.5px solid {PALETTE['border_focus']};
    border-radius: 8px;
    selection-background-color: {PALETTE['accent']};
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
    background: {PALETTE['accent']};
    color: #fff;
}}
QToolTip {{
    background: {PALETTE['panel']};
    color: {PALETTE['text']};
    border: 1px solid {PALETTE['border']};
}}
QTabWidget#mainTabs::pane {{
    background: transparent;
    border: none;
    top: -1px;
}}
QTabWidget#mainTabs QTabBar::tab {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1px solid {PALETTE['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 104px;
    padding: 8px 18px;
    margin-right: 6px;
    font-size: 9pt;
    font-weight: 700;
}}
QTabWidget#mainTabs QTabBar::tab:selected {{
    background: {PALETTE['accent']};
    color: #fff;
    border-color: {PALETTE['accent']};
}}
QTabWidget#mainTabs QTabBar::tab:hover:!selected {{
    background: {PALETTE['panel']};
    color: {PALETTE['text']};
    border-color: {PALETTE['border_focus']};
}}
QPushButton#fetchBtn {{
    background: {PALETTE['accent']};
    color: #fff;
    border: none;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    padding: 10px 26px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#fetchBtn:hover   {{ background: {PALETTE['btn_hv']}; }}
QPushButton#fetchBtn:pressed  {{ background: #5a52e0; }}
QPushButton#fetchBtn:disabled {{ background: {PALETTE['border']}; color: {PALETTE['subtext']}; }}
QPushButton#geoCheckBtn {{
    color: #38bdf8;
    border: 1.5px solid {PALETTE['border']};
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
    padding: 0 10px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#geoCheckBtn:hover   {{ background: #0f3460; color: #fff; }}
QPushButton#geoCheckBtn:pressed  {{ background: #0f3460; color: #fff; }}
QPushButton#geoCheckBtn:disabled {{ background: {PALETTE['card']}; color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; }}
QPushButton#clearBtn {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    padding: 0 10px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#clearBtn:hover  {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}
QPushButton#clearBtn:pressed {{ background: #252840; }}
QPushButton#cliproxyBtn {{
    background: {PALETTE['card']};
    color: #e05252;
    border: 2px solid #e05252;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: 700;
}}
QPushButton#cliproxyBtn[running="true"] {{
    border: 2px solid #4caf50;
    color: #4caf50;
}}
QPushButton#cliproxyBtn:hover {{ background: {PALETTE['border']}; }}
QPushButton#autoCheckBtn {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1.5px solid {PALETTE['border']};
    border-right: none;
    border-radius: 8px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#autoCheckBtn:hover  {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}
QPushButton#autoCheckBtn:pressed {{ background: #252840; }}
QPushButton#autoCheckBtn:checked {{
    background: {PALETTE['accent']};
    color: #fff;
    border-color: {PALETTE['accent']};
    border-right: none;
}}
QPushButton#autoCheckBtn:disabled {{
    background: {PALETTE['card']};
    color: {PALETTE['subtext']};
    border-color: {PALETTE['border']};
    opacity: 0.5;
}}
QPushButton#timerIntervalBtn {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    padding: 0;
    font-size: 13pt;
}}
QPushButton#timerIntervalBtn:hover {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}
QPushButton#timerIntervalBtn:pressed {{ background: #252840; }}
QPushButton#timerIntervalBtn:disabled {{ background: {PALETTE['card']}; color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; }}
QPushButton#bulkCheckBtn {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1.5px solid {PALETTE['border']};
    border-right: none;
    border-radius: 8px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    padding: 0px 10px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#bulkCheckBtn:hover  {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}
QPushButton#bulkCheckBtn:pressed {{ background: #252840; }}
QPushButton#bulkCheckBtn:disabled {{ background: {PALETTE['card']}; color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; }}
QPushButton#bulkRefreshBtn {{
    background: {PALETTE['card']};
    color: {PALETTE['label']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    padding: 0px 10px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#bulkRefreshBtn:hover  {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}
QPushButton#bulkRefreshBtn:pressed {{ background: #252840; }}
QPushButton#bulkRefreshBtn:disabled {{ background: {PALETTE['card']}; color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; }}
/* ── Proxy card ── */
QWidget#proxyCard {{
    background: {PALETTE['card']};
    border: 1.5px solid #3d4270;
    border-radius: 10px;
}}
QWidget#proxyCard:hover {{
    border-color: {PALETTE['accent']};
}}
QLabel#proxyIp {{
    color: {PALETTE['text']};
    font-family: "Consolas", monospace;
    font-size: 11pt;
    font-weight: 700;
    background: transparent;
}}
QLabel#proxyInfo {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    background: transparent;
}}
QLabel#tagLabel {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    font-weight: 600;
    background: transparent;
}}
QWidget#tagLabel {{
    background: transparent;
}}
QWidget#tagLabel QLabel {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    font-weight: 600;
    background: transparent;
    border: none;
}}
QLabel#statusUnknown {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusAlive {{
    color: {PALETTE['success']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusDead {{
    color: {PALETTE['error']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0 2px;
}}
QLabel#statusChecking {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    background: transparent;
    padding: 0 2px;
}}
QLabel#pingLabel {{
    color: {PALETTE['subtext']};
    font-size: 8pt;
    font-weight: 600;
    background: transparent;
    padding: 0 2px;
}}
QLabel#respIpLabel {{
    color: {PALETTE['text']};
    font-size: 9pt;
    font-weight: 600;
    background: transparent;
    margin-left: 8px;
    padding: 0 0;
}}
/* Card action buttons */
QPushButton#cardRefreshBtn {{
    background: transparent;
    color: {PALETTE['accent']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 50px;
}}
QPushButton#cardRefreshBtn:hover   {{ background: {PALETTE['accent']}; color: #fff; border-color: {PALETTE['accent']}; }}
QPushButton#cardRefreshBtn:pressed  {{ background: #5a52e0; color: #fff; }}
QPushButton#cardRefreshBtn:disabled {{ color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; opacity: 0.5; }}
QPushButton#cardCheckBtn {{
    background: transparent;
    color: {PALETTE['accent2']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 50px;
}}
QPushButton#cardCheckBtn:hover   {{ background: {PALETTE['accent']}; color: #fff; border-color: {PALETTE['accent']}; }}
QPushButton#cardCheckBtn:pressed  {{ background: #5a52e0; color: #fff; }}
QPushButton#cardCheckBtn:disabled {{ color: {PALETTE['subtext']}; border-color: {PALETTE['border']}; }}
QPushButton#cardDeleteBtn {{
    background: transparent;
    color: {PALETTE['error']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 20px;
}}
QPushButton#cardDeleteBtn:hover   {{ background: {PALETTE['error']}; color: #fff; border-color: {PALETTE['error']}; }}
QPushButton#cardDeleteBtn:pressed  {{ background: #d05555; color: #fff; }}
QPushButton#cardCopyBtn {{
    background: transparent;
    color: {PALETTE['subtext']};
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10pt;
    min-width: 22px;
    max-width: 22px;
}}
QPushButton#cardCopyBtn:hover   {{ color: {PALETTE['accent']}; background: {PALETTE['border']}; }}
QPushButton#cardCopyBtn:pressed  {{ color: #fff; background: {PALETTE['accent']}; }}
/* Result scroll area */
QScrollArea#resultScroll {{
    background: {PALETTE['entry_bg']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
}}
QScrollArea#resultScroll > QWidget > QWidget {{
    background: {PALETTE['entry_bg']};
    border-radius: 10px;
}}
QScrollBar:vertical {{
    background: #101322;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {PALETTE['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: #101322; }}
QFrame#divider {{
    background: {PALETTE['border']};
    border: none;
}}
QLabel#badge {{
    background: {PALETTE['accent']};
    color: #fff;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 8pt;
    font-weight: 700;
}}
/* ── QMessageBox ── */
QMessageBox {{
    background: {PALETTE['panel']};
}}
QMessageBox QLabel {{
    color: {PALETTE['text']};
    background: transparent;
    font-size: 10pt;
}}
QMessageBox QPushButton {{
    background: {PALETTE['card']};
    color: {PALETTE['text']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 5px 18px;
    font-size: 9pt;
    font-weight: 700;
    min-width: 72px;
}}
QMessageBox QPushButton:hover {{
    background: {PALETTE['accent']};
    color: #fff;
    border-color: {PALETTE['accent']};
}}
QMessageBox QPushButton:pressed {{
    background: #5a52e0;
    color: #fff;
}}
"""

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
