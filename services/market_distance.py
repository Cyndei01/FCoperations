from __future__ import annotations

import math

import requests

from services.live_sources import geocode_market


MARKET_COORDINATES = {
    "Detroit, MI": (42.3314, -83.0458),
    "San Antonio, TX": (29.4241, -98.4936),
    "Baton Rouge, LA": (30.4515, -91.1871),
    "New Orleans, LA": (29.9511, -90.0715),
    "Shreveport, LA": (32.5252, -93.7502),
    "Lafayette, LA": (30.2241, -92.0198),
    "Lake Charles, LA": (30.2266, -93.2174),
    "Laredo, TX": (27.5064, -99.5075),
    "Houston, TX": (29.7604, -95.3698),
    "La Porte, TX": (29.6658, -95.0194),
    "Denton, TX": (33.2148, -97.1331),
    "Coppell, TX": (32.9546, -97.0150),
    "Gallatin, TN": (36.3884, -86.4467),
    "Bowling Green, KY": (36.9685, -86.4808),
    "Louisville, KY": (38.2527, -85.7585),
    "Lexington, KY": (38.0406, -84.5037),
    "Clinton, TN": (36.1034, -84.1319),
    "Jamestown, TN": (36.4276, -84.9319),
    "Knoxville, TN": (35.9606, -83.9207),
    "Memphis, TN": (35.1495, -90.0490),
    "Pulaski, TN": (35.1998, -87.0308),
    "Crossville, TN": (35.9489, -85.0269),
    "Portland, TN": (36.5817, -86.5164),
    "Whitehall, MI": (43.4100, -86.3487),
    "Fraser, MI": (42.5392, -82.9494),
    "Grand Rapids, MI": (42.9634, -85.6681),
    "Auburn Hills, MI": (42.6875, -83.2341),
    "Lansing, MI": (42.7325, -84.5555),
    "Sterling Heights, MI": (42.5803, -83.0302),
    "Toledo, OH": (41.6528, -83.5379),
    "Indianapolis, IN": (39.7684, -86.1581),
    "Columbus, MS": (33.4957, -88.4273),
    "Fairburn, GA": (33.5671, -84.5810),
    "Charlotte, NC": (35.2271, -80.8431),
    "Nashville, TN": (36.1627, -86.7816),
    "Cincinnati, OH": (39.1031, -84.5120),
    "Erlanger, KY": (39.0167, -84.6008),
    "Chicago, IL": (41.8781, -87.6298),
    "Romulus, MI": (42.2223, -83.3966),
    "Holland, MI": (42.7875, -86.1089),
    "Cleveland, OH": (41.4993, -81.6944),
    "Columbus, OH": (39.9612, -82.9988),
    "Vandalia, OH": (39.8906, -84.1988),
    "Bellefontaine, OH": (40.3612, -83.7597),
    "Statesville, NC": (35.7826, -80.8873),
    "Stokesdale, NC": (36.2371, -79.9795),
    "Newton, NC": (35.6699, -81.2215),
    "Fountain Inn, SC": (34.6890, -82.1957),
    "Greer, SC": (34.9387, -82.2271),
    "Auburn, AL": (32.6099, -85.4808),
    "Birmingham, AL": (33.5186, -86.8104),
    "Mobile, AL": (30.6954, -88.0399),
    "Muscle Shoals, AL": (34.7448, -87.6675),
    "West Point, GA": (32.8779, -85.1833),
    "Marietta, GA": (33.9526, -84.5499),
    "Atlanta, GA": (33.7490, -84.3880),
    "Mount Sterling, KY": (38.0565, -83.9433),
    "Sturbridge, MA": (42.1084, -72.0787),
    "Scranton, PA": (41.4089, -75.6624),
    "Allentown, PA": (40.6023, -75.4714),
    "Harrisburg, PA": (40.2732, -76.8867),
    "Pittsburgh, PA": (40.4406, -79.9959),
    "Erie, PA": (42.1292, -80.0851),
    "Latrobe, PA": (40.3212, -79.3795),
    "Hanover, PA": (39.8007, -76.9830),
    "Schuylkill Haven, PA": (40.6306, -76.1716),
    "Kersey, PA": (41.3626, -78.6011),
    "Macungie, PA": (40.5159, -75.5552),
    "New Stanton, PA": (40.2198, -79.6095),
    "Russellton, PA": (40.6117, -79.8362),
    "Youngstown, OH": (41.0998, -80.6495),
    "Sidney, OH": (40.2842, -84.1555),
    "Dayton, OH": (39.7589, -84.1916),
    "Fostoria, OH": (41.1570, -83.4169),
    "Perrysburg, OH": (41.5569, -83.6272),
    "Greenfield, IN": (39.7850, -85.7694),
    "Huntington, IN": (40.8831, -85.4975),
    "Greenwood, IN": (39.6137, -86.1067),
    "Rushville, IN": (39.6092, -85.4464),
    "South Bend, IN": (41.6764, -86.2520),
    "Plainfield, IN": (39.7042, -86.3994),
    "Merrillville, IN": (41.4828, -87.3328),
    "Evansville, IN": (37.9716, -87.5711),
    "Fort Wayne, IN": (41.0793, -85.1394),
}

STATE_CENTROIDS = {
    "AL": (32.8067, -86.7911),
    "AR": (34.9697, -92.3731),
    "AZ": (33.7298, -111.4312),
    "CA": (36.1162, -119.6816),
    "CO": (39.0598, -105.3111),
    "CT": (41.5978, -72.7554),
    "DE": (39.3185, -75.5071),
    "FL": (27.7663, -81.6868),
    "GA": (33.0406, -83.6431),
    "IA": (42.0115, -93.2105),
    "ID": (44.2405, -114.4788),
    "IL": (40.3495, -88.9861),
    "IN": (39.8494, -86.2583),
    "KS": (38.5266, -96.7265),
    "KY": (37.6681, -84.6701),
    "LA": (31.1695, -91.8678),
    "MA": (42.2302, -71.5301),
    "MD": (39.0639, -76.8021),
    "ME": (44.6939, -69.3819),
    "MI": (43.3266, -84.5361),
    "MN": (45.6945, -93.9002),
    "MO": (38.4561, -92.2884),
    "MS": (32.7416, -89.6787),
    "MT": (46.9219, -110.4544),
    "NC": (35.6301, -79.8064),
    "ND": (47.5289, -99.7840),
    "NE": (41.1254, -98.2681),
    "NH": (43.4525, -71.5639),
    "NJ": (40.1430, -74.7311),
    "NM": (34.8405, -106.2485),
    "NV": (38.3135, -117.0554),
    "NY": (42.1657, -74.9481),
    "OH": (40.3888, -82.7649),
    "OK": (35.5653, -96.9289),
    "OR": (44.5720, -122.0709),
    "PA": (40.5908, -77.2098),
    "RI": (41.6809, -71.5118),
    "SC": (33.8569, -80.9450),
    "SD": (44.2998, -99.4388),
    "TN": (35.7478, -86.6923),
    "TX": (31.0545, -97.5635),
    "UT": (40.1500, -111.8624),
    "VA": (37.7693, -78.1700),
    "VT": (44.0459, -72.7107),
    "WA": (47.4009, -121.4905),
    "WI": (44.2685, -89.6165),
    "WV": (38.4912, -80.9545),
    "WY": (42.7560, -107.3025),
}


def estimated_distance_miles(origin_market: str, target_market: str, allow_geocode: bool = True) -> float | None:
    distance, _source = estimated_distance_detail(origin_market, target_market, allow_geocode)
    return distance


def market_coordinate(market: str, allow_geocode: bool = True) -> tuple[float, float] | None:
    coordinate, _source = _market_coordinate(market, allow_geocode)
    return coordinate


def estimated_distance_detail(origin_market: str, target_market: str, allow_geocode: bool = True) -> tuple[float | None, str]:
    origin, origin_source = _market_coordinate(origin_market, allow_geocode)
    target, target_source = _market_coordinate(target_market, allow_geocode)
    if not origin or not target:
        return None, "Unavailable"
    source = "Estimated"
    sources = {origin_source, target_source}
    if "State estimate" in sources:
        source = "State estimate"
    elif "Geocoded" in sources:
        source = "Geocoded estimate"
    distance = round(_haversine_miles(origin[0], origin[1], target[0], target[1]) * 1.18, 1)
    if distance == 0 and _normalize_market(origin_market) != _normalize_market(target_market):
        distance = 75.0
    return distance, source


def _market_coordinate(market: str, allow_geocode: bool) -> tuple[tuple[float, float] | None, str]:
    known = MARKET_COORDINATES.get(_normalize_market(market))
    if known:
        return known, "Estimated"
    if not allow_geocode:
        state_coordinate = STATE_CENTROIDS.get(_state_code(market))
        if state_coordinate:
            return state_coordinate, "State estimate"
        return None, "Unavailable"
    try:
        geocoded = geocode_market(market)
    except requests.RequestException:
        geocoded = None
    if not geocoded:
        state_coordinate = STATE_CENTROIDS.get(_state_code(market))
        if state_coordinate:
            return state_coordinate, "State estimate"
        return None, "Unavailable"
    return (float(geocoded["lat"]), float(geocoded["lon"])), "Geocoded"


def _state_code(market: str) -> str:
    if "," not in market:
        return ""
    return market.rsplit(",", 1)[1].strip().upper()


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalize_market(market: str) -> str:
    if "," not in market:
        return market.strip().title()
    city, state = market.rsplit(",", 1)
    return f"{city.strip().title()}, {state.strip().upper()}"
