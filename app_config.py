APP_NAME = "F&C Packaging Load Map"
COMPANY_NAME = "F&C Packaging"
WEBSITE_URL = "https://fcpackaginginc.com"
APP_URL = "https://loadmap.fcpackaginginc.com"

BRAND_COLORS = {
    "navy": "#0b1f3a",
    "navy_light": "#14345c",
    "yellow": "#f3c400",
    "white": "#ffffff",
    "grey": "#f4f6f8",
    "grey_dark": "#6b7280",
    "black": "#111827",
}

OWNER_SETTINGS = {
    "revenue_split": {
        "company_percent": 40,
        "driver_percent": 60,
    },
    "relocation_distance_limit_miles": 250,
    "weather_sensitivity": "medium",
}

LIVE_DATA = {
    "enabled": True,
    "user_agent": "FCPackagingLoadMap/0.1 contact: fcpackaginginc.com",
    "max_live_markets": 5,
    "nominatim_url": "https://nominatim.openstreetmap.org/search",
    "overpass_url": "https://overpass-api.de/api/interpreter",
    "osrm_route_url": "https://router.project-osrm.org/route/v1/driving",
    "nws_api_url": "https://api.weather.gov",
}

ARCGIS_MARKET_DENSITY = {
    "enabled": True,
    "dashboard_url": "https://bgafoundation.maps.arcgis.com/apps/dashboards/90b75ed13442482b82b240d5f206fbdb",
    "portal_url": "https://bgafoundation.maps.arcgis.com",
    "dashboard_item_id": "90b75ed13442482b82b240d5f206fbdb",
    "radius_miles": 50,
    "market_limit": 12,
    "max_layers": 3,
}

MOMENTUM = {
    "base_url_env": "MOMENTUM_API_BASE_URL",
    "tenant_id_env": "MOMENTUM_TENANT_ID",
    "email_env": "MOMENTUM_EMAIL",
    "username_env": "MOMENTUM_USERNAME",
    "password_env": "MOMENTUM_PASSWORD",
    "token_env": "MOMENTUM_JWT",
}

SUPABASE = {
    "url_env": "SUPABASE_URL",
    "service_role_key_env": "SUPABASE_SERVICE_ROLE_KEY",
    "anon_key_env": "SUPABASE_ANON_KEY",
    "storage_bucket_env": "SUPABASE_STORAGE_BUCKET",
    "default_storage_bucket": "fcoperations",
}

WEB_PAGES = {
    "Load 1": {
        "url": "https://fleet.load1.com/vehicles",
        "note": "If the board blocks embedding, use the open-site button.",
    },
    "Expeditus": {
        "url": "https://www.fleet-vu.com",
        "note": "If Fleet-Vu blocks embedding, use the open-site button.",
    },
    "Whatsapp": {
        "url": "https://web.whatsapp.com/",
        "note": "WhatsApp Web may require browser sign-in and may block embedding in some environments.",
    },
}

FREE_FREIGHT_SOURCES = [
    {
        "name": "Trulos Freight Heat Map",
        "url": "https://www.trulos.com/heat_map/",
        "signal": "State-level posted-load demand by equipment",
        "status": "Best free candidate",
        "integration": "Public pages and public rate files; use respectfully with caching",
    },
    {
        "name": "Trulos Freight Rate Intelligence",
        "url": "https://trulos.com/freight-rate-intelligence/",
        "signal": "State-to-state loads, rates, spread, and lane trends",
        "status": "Best free candidate",
        "integration": "Public rate files are referenced by Trulos pages",
    },
    {
        "name": "FreightFinder",
        "url": "https://www.freightfinder.com/database/search/city-radius",
        "signal": "Free load search with visible current load count",
        "status": "Good manual source",
        "integration": "No clear public API; link out unless permission/API is available",
    },
    {
        "name": "Trucker Path TruckLoads",
        "url": "https://www.truckerpath.com/truckloads/free-load-board/",
        "signal": "Large free load board, broker info, load density tools",
        "status": "Good manual source",
        "integration": "App/web login workflow; use manually unless official API is available",
    },
    {
        "name": "TruckSmarter",
        "url": "https://apps.apple.com/us/app/trucksmarter-free-load-board/id1555516481",
        "signal": "Free load board and market insights",
        "status": "Good manual source",
        "integration": "Mobile/app workflow; use manually unless official API is available",
    },
    {
        "name": "DAT One / Hot Market Maps",
        "url": "https://www.dat.com/blog/hot-market-maps",
        "signal": "Load-to-truck ratios by market for van, reefer, flatbed",
        "status": "Excellent data, usually subscription-gated",
        "integration": "Use manually through DAT; API/data feed requires DAT terms",
    },
]

MARKET_INTELLIGENCE_SOURCES = [
    {
        "name": "FreightWaves SONAR / Market Updates",
        "url": "https://www.freightwaves.com/news",
        "cadence": "Weekly / near real-time articles",
        "best_use": "Market-specific OTVI, OTRI, headhaul, rejection, and volume trend notes",
        "integration": "Manual market intelligence overlay unless official SONAR/API access is added",
    },
    {
        "name": "OOIDA Monthly Market Update",
        "url": "https://www.ooida.com/foundation/monthly-trucking-market-update/",
        "cadence": "Monthly",
        "best_use": "National and regional freight condition bias for small carriers",
        "integration": "Manual monthly score bias from the published/free report",
    },
]

PAGES = [
    {
        "name": "Load 1",
        "module": "feature_pages.web_access",
        "enabled": True,
    },
    {
        "name": "Expeditus",
        "module": "feature_pages.web_access",
        "enabled": True,
    },
    {
        "name": "Whatsapp",
        "module": "feature_pages.web_access",
        "enabled": True,
    },
    {
        "name": "Live Freight Map",
        "module": "feature_pages.live_freight_map",
        "enabled": False,
    },
    {
        "name": "Sprinter Heat Map",
        "module": "feature_pages.sprinter_heat_map",
        "enabled": True,
    },
    {
        "name": "Hot Markets",
        "module": "feature_pages.hot_markets",
        "enabled": False,
    },
    {
        "name": "Dead Zones",
        "module": "feature_pages.dead_zones",
        "enabled": False,
    },
    {
        "name": "Best Lanes",
        "module": "feature_pages.best_lanes",
        "enabled": False,
    },
    {
        "name": "Relocation Finder",
        "module": "feature_pages.relocation_finder",
        "enabled": True,
    },
    {
        "name": "Weather Risk Map",
        "module": "feature_pages.weather_risk_map",
        "enabled": True,
    },
    {
        "name": "Momentum GPS",
        "module": "feature_pages.momentum_gps",
        "enabled": False,
    },
    {
        "name": "Settings",
        "module": "feature_pages.settings",
        "enabled": True,
    },
]
