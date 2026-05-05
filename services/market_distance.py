from __future__ import annotations

import math


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


def estimated_distance_miles(origin_market: str, target_market: str) -> float | None:
    origin = MARKET_COORDINATES.get(_normalize_market(origin_market))
    target = MARKET_COORDINATES.get(_normalize_market(target_market))
    if not origin or not target:
        return None
    return round(_haversine_miles(origin[0], origin[1], target[0], target[1]) * 1.18, 1)


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
