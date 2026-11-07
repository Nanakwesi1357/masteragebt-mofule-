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
    "Benfica": ["SL Benfica"], "Porto": ["FC Porto"], "Sporting CP": ["Sporting Lisbon", "Sp Lisbon", "Sp. Lisbon", "Sporting"],
    "Galatasaray": [], "Fenerbahce": [], "Besiktas": [], "Celtic": [], "Rangers": [],

    # ------------------------------------------------------------------ wider Europe
    # Belgium (football-data short names; open-matchday full names as aliases)
    "Anderlecht": ["RSC Anderlecht"], "Antwerp": ["Royal Antwerp", "Royal Antwerp FC"],
    "Beerschot": ["Beerschot VA", "Beerschot Wilrijk"], "Cercle Brugge": ["Cercle Brugge KSV"],
    "Charleroi": ["Royal Charleroi SC", "Sporting Charleroi"], "Club Brugge": ["Club Brugge KV"],
    "Dender": ["FCV Dender"], "Eupen": ["KAS Eupen"], "Genk": ["Racing Genk", "KRC Genk"],
    "Gent": ["KAA Gent", "Ghent"], "Kortrijk": ["KV Kortrijk"], "Mechelen": ["KV Mechelen"],
    "Westerlo": ["KVC Westerlo"], "Lokeren": ["Sporting Lokeren"], "Lommel SK": ["Lommel"],
    "Mouscron": ["Royal Excel Mouscron"],
    "OH Leuven": ["Oud-Heverlee Leuven", "Leuven", "O-H Leuven", "OHL"],
    "Oostende": ["KV Oostende"], "RAAL La Louviere": ["La Louviere"],
    "RWD Molenbeek": ["Molenbeek"], "Seraing": ["RFC Seraing"],
    "Sint-Truiden": ["Sint-Truidense", "St Truiden", "St. Truiden"],
    "St. Gilloise": ["Union St.-Gilloise", "Union Saint-Gilloise", "Union SG"],
    "Standard": ["Standard Liege", "St. Liege", "St Liege", "Standard Liège"], "Waasland-Beveren": ["Beveren"],
    "Zulte-Waregem": ["Waregem"],
    # Denmark
    "Aalborg": ["Aalborg BK", "AaB"], "Aarhus": ["AGF", "AGF Aarhus"], "Brondby": ["Brøndby"],
    "Esbjerg": ["Esbjerg fB"], "FC Copenhagen": ["Copenhagen", "FC Kobenhavn", "Kobenhavn"],
    "Fredericia": ["FC Fredericia"], "Helsingor": ["FC Helsingor"], "Hobro": ["Hobro IK"],
    "Horsens": ["AC Horsens"], "Hvidovre IF": ["Hvidovre"], "Lyngby": ["Lyngby BK"],
    "Midtjylland": ["FC Midtjylland"], "Nordsjaelland": ["FC Nordsjaelland", "Nordsjælland"],
    "Odense": ["OB", "Odense BK"], "Randers FC": ["Randers"], "Silkeborg": ["Silkeborg IF"],
    "Sonderjyske": ["Sønderjyske", "SonderjyskE"], "Vejle": ["Vejle BK"], "Vendsyssel": ["Vendsyssel FF"],
    "Vestsjaelland": ["FC Vestsjaelland"], "Viborg": ["Viborg FF"],
    # France (extra spellings seen in the other two sources)
    "Lille": ["LOSC Lille"], "Lens": ["RC Lens"], "Strasbourg": ["RC Strasbourg Alsace"],
    "Brest": ["Stade Brestois 29"], "Nice": ["OGC Nice"],
    "Auxerre": ["AJ Auxerre"], "Ajaccio": ["AC Ajaccio"], "Amiens": ["Amiens SC"],
    "Angers": ["Angers SCO"], "Bordeaux": ["Girondins Bordeaux"], "Caen": ["SM Caen"],
    "Clermont": ["Clermont Foot"], "Dijon": ["Dijon FCO"], "Troyes": ["Estac Troyes"],
    "Guingamp": ["EA Guingamp"], "Le Havre": ["Havre Athletic Club"], "Le Mans FC": ["Le Mans"],
    "Lorient": ["FC Lorient"], "Metz": ["FC Metz"], "Montpellier": ["Montpellier HSC"],
    "Nantes": ["FC Nantes"], "Nimes": ["Nîmes"], "Paris FC": [], "Reims": ["Stade de Reims"],
    "Toulouse": ["Toulouse FC"],
    # Greece
    "AEK Athens": ["AEK Athen", "AEK"], "Aris": ["Aris Saloniki", "Aris Thessaloniki"],
    "Asteras Tripolis": ["Asteras Tripoli"], "Atromitos": [], "Kifisia": ["AE Kifisias", "Kifisias"],
    "Lamia": ["Lamia FC"], "Levadiakos": [], "OFI Crete": ["OFI Heraklion", "OFI"],
    "Olympiacos": ["Olympiakos Piraeus", "Olympiakos"], "PAOK": ["PAOK Saloniki", "PAOK Thessaloniki"],
    "PAS Giannina": [], "Panathinaikos": [], "Panetolikos": [], "Panserraikos": [],
    "Volos NFC": ["Volos"], "AE Larissa": ["Larissa"], "Iraklis": [], "Kalamata": [],
    "Kallithea": ["GS Kallithea"],
    # Netherlands
    "ADO Den Haag": ["Den Haag"], "Almere City": ["Almere City FC"], "Cambuur": ["SC Cambuur"],
    "Excelsior": ["Excelsior Rotterdam"], "FC Emmen": ["Emmen"], "Groningen": ["FC Groningen"],
    "Twente": ["FC Twente"], "Utrecht": ["FC Utrecht"], "Fortuna Sittard": ["For Sittard"],
    "Go Ahead Eagles": ["Go Ahead"], "Graafschap": ["De Graafschap"], "Heerenveen": ["sc Heerenveen"],
    "Heracles": ["Heracles Almelo"], "NEC Nijmegen": ["N.E.C. Nijmegen", "Nijmegen"],
    "NAC Breda": [], "Zwolle": ["PEC Zwolle"], "Sparta Rotterdam": [], "Telstar": ["SC Telstar"],
    "VVV Venlo": ["Venlo"], "Vitesse": ["Vitesse Arnhem"], "Volendam": ["FC Volendam"],
    "Waalwijk": ["RKC Waalwijk"], "Willem II": [],
    # Norway
    "Aalesund": ["Aalesunds FK"], "Bodo/Glimt": ["Bodo Glimt", "Bodø/Glimt"], "Brann": ["SK Brann"],
    "Bryne": ["Bryne FK"], "Fredrikstad": ["Fredrikstad FK"], "HamKam": ["Ham-Kam"],
    "Haugesund": ["FK Haugesund"], "Honefoss": ["Hønefoss"], "Jerv": ["FK Jerv"],
    "KFUM Oslo": ["KFUM"], "Kongsvinger": ["Kongsvinger IL"], "Kristiansund": ["Kristiansund BK"],
    "Lillestrom": ["Lillestrøm"], "Mjondalen": ["Mjøndalen"], "Molde": ["Molde FK"],
    "Moss": ["Moss FK"], "Odd": ["Odds BK", "Odd Grenland"], "Ranheim": ["Ranheim TF"],
    "Rosenborg": ["Rosenborg BK"], "Sandefjord": ["Sandefjord Fotball"], "Sandnes": ["Sandnes Ulf"],
    "Sarpsborg 08": ["Sarpsborg"], "Sogndal": ["Sogndal Fotball"], "Stabaek": ["Stabæk"],
    "Start": ["IK Start"], "Stromsgodset": ["Strømsgodset"], "Tromso": ["Tromsø"],
    "Ull/Kisa": ["Ullensaker/Kisa"], "Valerenga": ["Vålerenga"], "Viking": ["Viking FK"],
    # Romania
    "CFR Cluj": ["CFR 1907 Cluj"], "Universitatea Craiova": ["CS Universitatea Craiova",
        "Univ. Craiova"], "FC U Craiova": ["U Craiova 1948", "FCU Craiova"], "Corvinul": ["Corvinul Hunedoara"],
    "Csikszereda": ["Csikszereda M. Ciuc"], "Dinamo Bucuresti": ["Dinamo Bucharest"],
    "FC Arges": ["Arges Pitesti"], "FC Botosani": ["Botosani"], "FC Hermannstadt": ["Hermannstadt"],
    "Politehnica Iasi": ["FC Politehnica Iasi"], "Rapid Bucuresti": ["FC Rapid Bucuresti"],
    "FC Voluntari": ["Voluntari"], "FCSB": ["Steaua Bucuresti"], "Farul Constanta": ["Farul"],
    "Gloria Buzau": [], "Otelul Galati": ["Otelul"], "Petrolul Ploiesti": ["Petrolul"],
    "Sepsi OSK": ["Sepsi Sf. Gheorghe", "Sepsi"], "Universitatea Cluj": ["U. Cluj"],
    "UTA Arad": [], "Unirea Slobozia": [],
    # Spain (segunda / recent top-flight spellings)
    "Almeria": ["UD Almeria"], "Cadiz": ["Cadiz CF"], "Eibar": ["SD Eibar"],
    "Espanyol": ["Espanol", "RCD Espanyol de Barcelona"], "Granada": ["Granada CF"],
    "Huesca": ["SD Huesca"], "Leganes": ["CD Leganes"], "Levante": ["Levante UD"],
    "Malaga": ["Malaga CF"], "Oviedo": ["Real Oviedo"],
    "Deportivo La Coruna": ["RC Deportivo", "Deportivo"], "Racing Santander": ["R. Racing Club"],
    # Switzerland (incl. Liechtenstein's Vaduz, which plays in the Swiss pyramid)
    "Basel": ["FC Basel 1893", "FC Basel"], "Young Boys": ["BSC Young Boys", "YB"],
    "Zurich": ["FC Zurich"], "Servette": ["Servette FC"], "Lugano": ["FC Lugano"],
    "Luzern": ["FC Luzern"], "Sion": ["FC Sion"], "St. Gallen": ["FC St. Gallen", "St Gallen"],
    "Winterthur": ["FC Winterthur"], "Grasshoppers": ["Grasshopper Club Zurich"],
    "Lausanne": ["FC Lausanne-Sport"], "Stade Lausanne-Ouchy": ["Lausanne-Ouchy"],
    "Thun": ["FC Thun"], "Vaduz": ["FC Vaduz"], "Yverdon": ["Yverdon Sport FC"],
    # -------------------------------------------------- top flights with two sources, two styles
    # These leagues arrive from two sources with different house styles: the mirror uses
    # football-data's long spellings ("1. FC Koln", "Casa Pia AC"), open-matchday the short ones
    # ("FC Koln", "Casa Pia"). Unmapped, one club gets two half-histories and every current-season
    # side looks newly promoted. Canonical = the common short name.
    # Germany
    "FC Koln": ["Koln", "Cologne", "1. FC Koln"], "Union Berlin": ["FC Union Berlin", "1. FC Union Berlin"],
    "Mainz": ["Mainz 05", "FSV Mainz 05", "1. FSV Mainz 05"], "Bayer Leverkusen": ["Leverkusen", "Bayer 04 Leverkusen"],
    "Schalke 04": ["FC Schalke 04"], "Paderborn": ["SC Paderborn 07"],
    "St Pauli": ["FC St. Pauli", "St. Pauli"], "Arminia Bielefeld": ["Bielefeld"], "VfL Bochum": ["Bochum"],
    "Darmstadt 98": ["Darmstadt", "SV Darmstadt 98"], "Hannover 96": ["Hannover"],
    "Hertha BSC": ["Hertha"], "1. FC Nurnberg": ["Nurnberg"], "Fortuna Dusseldorf": [],
    "Greuther Furth": [], "Holstein Kiel": [], "SV 07 Elversberg": [],
    "Heidenheim": ["FC Heidenheim", "1. FC Heidenheim"],
    # Italy
    "Benevento": [], "Brescia": [], "Chievo": ["Chievo Verona"], "Cremonese": [], "Crotone": [],
    "Empoli": [], "Frosinone": [], "Monza": [], "Pisa": [], "Salernitana": [], "Sampdoria": [],
    "Spal": ["SPAL"], "Spezia": [], "Venezia": [],
    # Portugal
    "Vitoria Guimaraes": ["Guimaraes"], "Vitoria Setubal": ["Setubal"],
    "Braga": ["SC Braga", "Sp Braga", "Sporting Braga"], "Nacional": ["CD Nacional", "Nacional Madeira"],
    "Alverca": ["FC Alverca"], "Arouca": ["FC Arouca"], "Casa Pia": ["Casa Pia AC"],
    "Estoril": ["Estoril Praia"], "Estrela Amadora": ["Estrela"], "Famalicao": ["FC Famalicao"],
    "Gil Vicente": ["Gil Vicente FC"], "Maritimo": ["Maritimo M."], "Moreirense": ["Moreirense FC"],
    "Rio Ave": ["Rio Ave FC"], "Academico": ["Academico Viseu"], "AVS": ["AVS Futebol SAD"],
    "Aves": ["Desportivo Aves"], "Belenenses": ["Belenenses SAD"], "Boavista": [], "Chaves": [],
    "Farense": [], "Feirense": [], "Pacos Ferreira": [], "Portimonense": [], "Santa Clara": [],
    "Tondela": [], "Vizela": [],
    # Scotland
    "Hearts": ["Heart of Midlothian"], "St Johnstone": ["St. Johnstone"], "St Mirren": ["St. Mirren"],
    "Hibernian": ["Hibs"], "Aberdeen": [], "Dundee": [], "Dundee United": [], "Falkirk": [],
    "Hamilton": ["Hamilton Academical"], "Kilmarnock": [], "Livingston": [], "Motherwell": [],
    "Ross County": [],
    # Turkey
    "Istanbul Basaksehir": ["Buyuksehyr", "Basaksehir", "Istanbul Basaksehir FK"],
    "Erzurumspor": ["Erzurum BB", "Erzurumspor FK"], "Goztepe": ["Goztep"],
    "Rizespor": ["Caykur Rizespor"], "Adana Demirspor": ["Ad. Demirspor"],
    "Akhisar Belediyespor": ["Akhisarspor"], "Alanyaspor": ["Aytemiz Alanyaspor"],
    "Antalyaspor": ["Fraport TAV Antalyaspor"], "Ankaragucu": ["MKE Ankaragucu"],
    "Bodrumspor": [], "Bursaspor": [], "Corum": ["Corum FK"], "Denizlispor": [],
    "Eyupspor": [], "Genclerbirligi": [], "Giresunspor": [], "Hatayspor": [], "Istanbulspor": [],
    "Karagumruk": ["Fatih Karagumruk"], "Kasimpasa": ["Kasimpasa SK"], "Kayserispor": [],
    "Kocaelispor": [], "Konyaspor": ["Konyaspor KIF"], "Pendikspor": [], "Samsunspor": [],
    "Sivasspor": [], "Trabzonspor": [], "Umraniyespor": [], "Yeni Malatyaspor": [],
    "Gaziantep": ["Gaziantep FK"], "Altay": ["Altay SK"], "Amedspor": ["Amed Sportif"],
    "Fenerbahce": ["Fenerbahce SK"], "Galatasaray": ["Galatasaray SK"], "Besiktas": ["Besiktas JK"],
    # Sweden (Allsvenskan, calendar-year seasons: 2026 is one season, so the mirror's history and
    # open-matchday's "2627" file both land in season 2627 and de-dup on the match key)
    "Osters": ["Oster"],  # Osters IF: "Osters" in 2013, "Oster" in 2022 and 2025, never both at once
    "Malmo FF": ["Malmo"], "Goteborg": ["IFK Goteborg"], "Hammarby": ["Hammarby IF"],
    "Elfsborg": ["IF Elfsborg"], "AIK": ["AIK Stockholm"], "Djurgarden": ["Djurgardens IF"],
    "Hacken": ["BK Hacken"], "Helsingborg": ["Helsingborgs IF"], "Norrkoping": ["IFK Norrkoping"],
    "Sirius": ["IK Sirius"], "Mjallby": ["Mjallby AIF"], "Degerfors": ["Degerfors IF"],
    "Kalmar": ["Kalmar FF"], "Varberg": ["Varbergs BoIS"], "Varnamo": ["IFK Varnamo"],
    "Halmstad": ["Halmstads BK"], "Sundsvall": ["GIF Sundsvall"], "Orebro": ["Orebro SK"],
    "Gefle": ["Gefle IF"], "GAIS": ["GAIS Goteborg"], "Orgryte": ["Orgryte IS"],
    "Brage": ["IK Brage"], "Trelleborgs": ["Trelleborgs FF"], "Brommapojkarna": ["IF Brommapojkarna"],
    "Dalkurd": ["Dalkurd FF"], "Falkenbergs": ["Falkenbergs FF"], "Jonkopings": ["Jonkopings Sodra"],
    "Landskrona": ["Landskrona BoIS"], "Ljungskile": ["Ljungskile SK"], "Syrianska": ["Syrianska FC"],
    "Atvidabergs": ["Atvidabergs FF"], "AFC Eskilstuna": ["AFC Eskilstuna FK"],
    "Vasteras SK": [], "Ostersunds": ["Ostersunds FK"],
}

_STOP = re.compile(r"\b(fc|afc|cf|sc|ac|as|ss|us|cd|ca|the|club|de|sv)\b")

# letters NFKD does not decompose but latin-1 cannot hold (or holds badly); used when writing
# raw files, because build_matches.read_csv() reads them as latin-1
_ASCII_FOLD = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE",
                             "đ": "d", "Đ": "D", "ł": "l", "Ł": "L", "ß": "ss", "þ": "th",
                             "ð": "d", "ı": "i"})


def to_ascii(name) -> str:
    """Fold a club name to plain ASCII, even for letters NFKD leaves alone (ø, æ, ł, ß, ţ...)."""
    s = str(name).translate(_ASCII_FOLD)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).encode("ascii", "ignore").decode()


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

# Two clubs can share a spelling across leagues, and `norm_key()` folds the whole world at once:
# "Vitoria" is EC Vitoria in Brazil and Vitoria de Guimaraes in Portugal, and Romanian sources
# write the two Craiova clubs almost identically ("CS Universitatea Craiova" / "FC Universitatea
# Craiova" - the stopword fold makes them the same key). These overrides are applied on the raw
# name, before folding, and only inside the named league.
LEAGUE_ALIASES = {
    "P1": {"Vitoria": "Vitoria Guimaraes", "Vitoria FC": "Vitoria Setubal"},
    "ROU": {"FC Universitatea Craiova": "FC U Craiova", "U Craiova 1948": "FC U Craiova",
            "CS Universitatea Craiova": "Universitatea Craiova"},
    "BRA": {"Vitoria": "Vitoria"},
}

UNMAPPED = set()


def canon(name, league=None) -> str:
    """Canonical team name; unknown names pass through cleaned and are recorded in UNMAPPED.

    `league` disambiguates the handful of spellings two clubs share (see LEAGUE_ALIASES);
    without it the global table is used and such a name resolves to its first owner.
    """
    if name is None or str(name).strip() == "" or str(name).lower() == "nan":
        return ""
    raw = str(name).strip()
    if league:
        override = LEAGUE_ALIASES.get(league, {})
        if raw in override:
            return override[raw]
    key = norm_key(name)
    if key in _LOOKUP:
        return _LOOKUP[key]
    UNMAPPED.add(str(name).strip())
    return str(name).strip()
