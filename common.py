"""Shared config + team-name normalisation for the football data pipeline."""
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

# football-data.co.uk: one CSV per league per season  (mmz4281/<SSYY>/<code>.csv)
MAIN_LEAGUES = {
    "E0": "England Premier League", "E1": "England Championship",
    "E2": "England League One", "E3": "England League Two", "EC": "England Conference",
    "SC0": "Scotland Premiership", "SC1": "Scotland Championship",
    "D1": "Germany Bundesliga", "D2": "Germany 2. Bundesliga",
    "I1": "Italy Serie A", "I2": "Italy Serie B",
    "SP1": "Spain La Liga", "SP2": "Spain La Liga 2",
    "F1": "France Ligue 1", "F2": "France Ligue 2",
    "N1": "Netherlands Eredivisie", "B1": "Belgium Pro League",
    "P1": "Portugal Primeira Liga", "T1": "Turkey Super Lig", "G1": "Greece Super League",
}

# football-data.co.uk "extra leagues": one CSV per league containing all seasons (new/<code>.csv)
EXTRA_LEAGUES = {
    "USA": "USA MLS", "BRA": "Brazil Serie A", "ARG": "Argentina Primera",
    "MEX": "Mexico Liga MX", "JPN": "Japan J1", "CHN": "China Super League",
    "AUT": "Austria Bundesliga", "DNK": "Denmark Superliga", "FIN": "Finland Veikkausliiga",
    "IRL": "Ireland Premier", "NOR": "Norway Eliteserien", "POL": "Poland Ekstraklasa",
    "ROU": "Romania Liga 1", "RUS": "Russia Premier League", "SWE": "Sweden Allsvenskan",
    "SWZ": "Switzerland Super League",
}

# Understat league slugs (xG), keyed by football-data code. Top 5 only.
UNDERSTAT = {"E0": "epl", "SP1": "la_liga", "D1": "bundesliga", "I1": "serie_a", "F1": "ligue_1"}

# The Odds API sport keys (verify against GET /v4/sports if one returns empty)
ODDS_API_SPORTS = [
    "soccer_epl", "soccer_efl_champ", "soccer_spain_la_liga", "soccer_germany_bundesliga",
    "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_usa_mls",
    "soccer_brazil_campeonato", "soccer_argentina_primera_division", "soccer_mexico_ligamx",
    "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
]


def season_codes(n=5, today=None):
    """Last n season codes, e.g. ['2223', ..., '2627'] (season rolls over on 1 July)."""
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(start - n + 1, start + 1)]


# ---------------------------------------------------------------- team names
# canonical name -> aliases seen across football-data, Understat, FPL, The Odds API.
# STARTER LIST: anything not matched is logged to out/unmapped_teams.txt, add it here.
TEAM_ALIASES = {
    # England
    "Manchester City": ["Man City"], "Manchester United": ["Man United", "Man Utd"],
    "Nottingham Forest": ["Nott'm Forest", "Nottm Forest"], "Newcastle United": ["Newcastle"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"], "Wolverhampton Wanderers": ["Wolves", "Wolverhampton"],
    "West Ham United": ["West Ham"], "Brighton & Hove Albion": ["Brighton", "Brighton and Hove Albion"],
    "Leeds United": ["Leeds"], "Leicester City": ["Leicester"], "Sheffield United": ["Sheffield Utd"],
    "West Bromwich Albion": ["West Brom"], "Sheffield Wednesday": ["Sheffield Weds"],
    "Queens Park Rangers": ["QPR"], "Coventry City": ["Coventry"], "Norwich City": ["Norwich"],
    "Ipswich Town": ["Ipswich"], "Cardiff City": ["Cardiff"], "Swansea City": ["Swansea"],
    "Stoke City": ["Stoke"], "Hull City": ["Hull"], "Derby County": ["Derby"],
    "Preston North End": ["Preston"], "Luton Town": ["Luton"], "Bristol City": ["Bristol C"],
    "Blackburn Rovers": ["Blackburn"], "Oxford United": ["Oxford"], "Plymouth Argyle": ["Plymouth"],
    "Birmingham City": ["Birmingham"], "Charlton Athletic": ["Charlton"], "Sunderland": ["Sunderland AFC"],
    "Everton": [], "Arsenal": [], "Chelsea": [], "Liverpool": [], "Fulham": [], "Brentford": [],
    "Burnley": [], "Bournemouth": ["AFC Bournemouth"], "Aston Villa": [], "Crystal Palace": [],
    # England, lower divisions (needed while a club is outside the Premier League)
    "Southampton": ["Southampton FC"], "Watford": [],
    "Middlesbrough": ["Middlesborough"], "Millwall": [], "Portsmouth": [], "Reading": [],
    "Barnsley": [], "Blackpool": [], "Wrexham": [], "Lincoln City": ["Lincoln"],
    "Bolton Wanderers": ["Bolton"], "Huddersfield Town": ["Huddersfield"],
    "Wigan Athletic": ["Wigan"], "Rotherham United": ["Rotherham"],
    "Peterborough United": ["Peterboro", "Peterborough"], "Wycombe Wanderers": ["Wycombe"],
    # Germany
    "Bayern Munich": ["Bayern Munchen", "Bayern Munich"], "Borussia Dortmund": ["Dortmund"],
    "Borussia Monchengladbach": ["M'gladbach", "Monchengladbach", "Gladbach"],
    "Bayer Leverkusen": ["Leverkusen"], "RB Leipzig": ["RasenBallsport Leipzig", "Leipzig"],
    "Eintracht Frankfurt": ["Ein Frankfurt", "Frankfurt"], "VfB Stuttgart": ["Stuttgart"],
    "FC Koln": ["Koln", "Cologne"], "Hamburger SV": ["Hamburg"], "Werder Bremen": ["Bremen"],
    "VfL Wolfsburg": ["Wolfsburg"], "Mainz": ["Mainz 05", "FSV Mainz 05"],
    "Union Berlin": ["FC Union Berlin"], "Hoffenheim": ["TSG Hoffenheim"],
    "St Pauli": ["FC St. Pauli", "St. Pauli"], "Heidenheim": ["FC Heidenheim"],
    "Augsburg": ["FC Augsburg"], "Freiburg": ["SC Freiburg"],
    # Spain
    "Atletico Madrid": ["Ath Madrid", "Atletico de Madrid"], "Athletic Bilbao": ["Ath Bilbao", "Athletic Club"],
    "Real Sociedad": ["Sociedad"], "Real Betis": ["Betis"], "Celta Vigo": ["Celta"],
    "Real Valladolid": ["Valladolid"], "Rayo Vallecano": ["Vallecano"], "Alaves": ["Deportivo Alaves"],
    "Barcelona": ["Barca", "FC Barcelona"], "Real Madrid": [], "Sevilla": [], "Valencia": [],
    "Villarreal": [], "Espanyol": [], "Getafe": [], "Girona": [], "Osasuna": [], "Mallorca": [],
    "Las Palmas": [], "Levante": [], "Elche": [],
    # Italy
    "Inter Milan": ["Inter", "Internazionale"], "AC Milan": ["Milan"], "AS Roma": ["Roma"],
    "Juventus": [], "Napoli": [], "Lazio": [], "Atalanta": [], "Fiorentina": [],
    "Hellas Verona": ["Verona"], "Torino": [], "Bologna": [], "Udinese": [], "Genoa": [],
    "Cagliari": [], "Lecce": [], "Parma": [], "Como": [], "Sassuolo": [],
    # France
    "Paris Saint-Germain": ["Paris SG", "PSG", "Paris Saint Germain"], "Marseille": ["Olympique Marseille"],
    "Lyon": ["Olympique Lyonnais"], "Monaco": ["AS Monaco"], "Lille": [], "Nice": [], "Lens": [],
    "Rennes": ["Stade Rennais"], "Brest": [], "Strasbourg": [], "St Etienne": ["Saint-Etienne", "Saint Etienne"],
    # MLS
    "Inter Miami": ["Inter Miami CF"], "LA Galaxy": ["Los Angeles Galaxy"], "LAFC": ["Los Angeles FC"],
    "New York City FC": ["NYCFC", "New York City"], "New York Red Bulls": ["NY Red Bulls", "Red Bulls"],
    "Seattle Sounders": ["Seattle Sounders FC"], "Atlanta United": ["Atlanta Utd", "Atlanta United FC"],
    "Portland Timbers": [], "Columbus Crew": [], "Orlando City": ["Orlando City SC"],
    "Sporting Kansas City": ["Sporting KC"], "Real Salt Lake": ["Salt Lake"],
    "Vancouver Whitecaps": ["Vancouver Whitecaps FC"], "CF Montreal": ["Montreal", "Montreal Impact"],
    "San Diego FC": ["San Diego"], "FC Cincinnati": ["Cincinnati"], "Philadelphia Union": [],
    "Houston Dynamo": ["Houston Dynamo FC"], "Austin FC": ["Austin"], "Nashville SC": ["Nashville"],
    "Toronto FC": ["Toronto"], "Charlotte FC": ["Charlotte"], "Colorado Rapids": [],
    "Minnesota United": ["Minnesota Utd"], "San Jose Earthquakes": ["San Jose"], "DC United": ["D.C. United"],
    "New England Revolution": ["New England"], "Chicago Fire": [], "FC Dallas": ["Dallas"],
    # Brazil (short names: open-matchday; prefixed names: openfootball official names)
    "Flamengo": ["Flamengo RJ", "CR Flamengo"], "Palmeiras": ["SE Palmeiras"], "Sao Paulo": ["Sao Paulo FC"],
    "Corinthians": ["SC Corinthians Paulista"], "Fluminense": ["Fluminense FC"],
    "Botafogo": ["Botafogo RJ", "Botafogo FR"], "Atletico Mineiro": ["Atletico-MG", "Atletico MG", "CA Mineiro"],
    "Athletico Paranaense": ["Athletico-PR", "Atletico-PR", "Atletico PR", "CA Paranaense"],
    "Gremio": ["Grêmio", "Gremio FBPA", "Grêmio FBPA"],
    "Internacional": ["SC Internacional"], "Santos": ["Santos FC"],
    "Vasco da Gama": ["Vasco", "CR Vasco da Gama"], "Cruzeiro": ["Cruzeiro EC"],
    "Bahia": ["EC Bahia"], "Fortaleza": ["Fortaleza EC"],
    "Bragantino": ["RB Bragantino", "Red Bull Bragantino"], "Cuiaba": ["Cuiabá EC", "Cuiabá"],
    "Goias": ["Goiás EC", "Goiás"], "Coritiba": ["Coritiba FBC"], "Vitoria": ["EC Vitória"],
    "Juventude": ["EC Juventude"], "Sport Recife": ["SC Recife"], "Ceara": ["Ceará SC", "Ceará"],
    "Mirassol": ["Mirassol FC"], "Chapecoense": ["Chapecoense AF"], "Remo": ["Clube do Remo"],
    "America Mineiro": ["América Mineiro", "América-MG"], "Atletico Goianiense": ["AC Goianiense", "Atletico-GO"],
    "Criciuma": ["Criciúma EC", "Criciúma"], "Avai": ["Avaí FC", "Avaí"],
    # Argentina
    "River Plate": [], "Boca Juniors": [], "Racing Club": [], "Independiente": [], "San Lorenzo": [],
    "Estudiantes L.P.": ["Estudiantes La Plata", "Estudiantes", "Estudiantes de La Plata"],
    "Velez Sarsfield": ["Velez"], "Lanus": ["Lanús"], "Talleres Cordoba": ["Talleres", "Talleres de Córdoba"],
    "Argentinos Juniors": [], "Defensa y Justicia": [], "Rosario Central": [],
    "Newells Old Boys": ["Newells", "Newell's Old Boys"], "Huracan": ["Huracán"],
    "Gimnasia L.P.": ["Gimnasia La Plata", "Gimnasia de La Plata"],
    "Gimnasia Mendoza": ["Gimnasia (Mendoza)", "Gimnasia de Mendoza"],
    "Estudiantes Rio Cuarto": ["Estudiantes de Río Cuarto"],
    "Banfield": [], "Godoy Cruz": [], "Belgrano": ["Belgrano de Córdoba", "Belgrano (Córdoba)"],
    "Tigre": [], "Platense": [], "Union Santa Fe": ["Union de Santa Fe", "Unión de Santa Fe"],
    "Colon Santa Fe": ["Colon", "Colón de Santa Fe"],
    "Instituto Cordoba": ["Instituto", "Instituto de Córdoba"],
    "Central Cordoba SdE": ["Central Cordoba", "Central Córdoba (Santiago del Estero)"],
    "Sarmiento Junin": ["Sarmiento", "Sarmiento de Junín"], "Barracas Central": [],
    "Independiente Rivadavia": [], "Atletico Tucuman": ["Atlético Tucumán"],
    "San Martin San Juan": ["San Martín de San Juan"], "Deportivo Riestra": [], "Aldosivi": [],
    "Arsenal de Sarandi": ["Arsenal de Sarandí"],
    # Other
    "PSV Eindhoven": ["PSV"], "Ajax": ["Ajax Amsterdam"], "Feyenoord": [], "AZ Alkmaar": ["AZ"],
    "Benfica": ["SL Benfica"], "Porto": ["FC Porto"], "Sporting CP": ["Sporting Lisbon", "Sporting"],
    "Galatasaray": [], "Fenerbahce": [], "Besiktas": [], "Celtic": [], "Rangers": [],
}

_STOP = re.compile(r"\b(fc|afc|cf|sc|ac|as|ss|us|cd|ca|the|club|de|sv)\b")


def norm_key(name) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s)
    s = _STOP.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


_LOOKUP = {}
for _canon, _aliases in TEAM_ALIASES.items():
    for _n in [_canon, *_aliases]:
        _LOOKUP[norm_key(_n)] = _canon

UNMAPPED = set()


def canon(name) -> str:
    """Canonical team name; unknown names pass through cleaned and are recorded in UNMAPPED."""
    if name is None or str(name).strip() == "" or str(name).lower() == "nan":
        return ""
    key = norm_key(name)
    if key in _LOOKUP:
        return _LOOKUP[key]
    UNMAPPED.add(str(name).strip())
    return str(name).strip()
