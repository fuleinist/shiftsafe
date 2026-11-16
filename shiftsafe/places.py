"""Bundled list of Australian places.

The list is small and fixed. It exists so the app works without a geocoding
service. A user can always enter a latitude and longitude instead.
"""

from __future__ import annotations

PLACES = [
    {"id": "sydney", "name": "Sydney", "state": "NSW", "lat": -33.8688, "lon": 151.2093},
    {"id": "cherrybrook", "name": "Cherrybrook", "state": "NSW", "lat": -33.7333, "lon": 151.0500},
    {"id": "parramatta", "name": "Parramatta", "state": "NSW", "lat": -33.8150, "lon": 151.0000},
    {"id": "penrith", "name": "Penrith", "state": "NSW", "lat": -33.7500, "lon": 150.7000},
    {"id": "blacktown", "name": "Blacktown", "state": "NSW", "lat": -33.7700, "lon": 150.9000},
    {"id": "liverpool", "name": "Liverpool", "state": "NSW", "lat": -33.9200, "lon": 150.9200},
    {"id": "newcastle", "name": "Newcastle", "state": "NSW", "lat": -32.9283, "lon": 151.7817},
    {"id": "wollongong", "name": "Wollongong", "state": "NSW", "lat": -34.4278, "lon": 150.8931},
    {"id": "campbelltown", "name": "Campbelltown", "state": "NSW", "lat": -34.0667, "lon": 150.8167},
    {"id": "gosford", "name": "Gosford", "state": "NSW", "lat": -33.4267, "lon": 151.3417},
    {"id": "dubbo", "name": "Dubbo", "state": "NSW", "lat": -32.2569, "lon": 148.6011},
    {"id": "wagga-wagga", "name": "Wagga Wagga", "state": "NSW", "lat": -35.1082, "lon": 147.3598},
    {"id": "albury", "name": "Albury", "state": "NSW", "lat": -36.0737, "lon": 146.9135},
    {"id": "tamworth", "name": "Tamworth", "state": "NSW", "lat": -31.0927, "lon": 150.9320},
    {"id": "coffs-harbour", "name": "Coffs Harbour", "state": "NSW", "lat": -30.2963, "lon": 153.1135},
    {"id": "lismore", "name": "Lismore", "state": "NSW", "lat": -28.8135, "lon": 153.2773},
    {"id": "orange", "name": "Orange", "state": "NSW", "lat": -33.2833, "lon": 149.1000},
    {"id": "bathurst", "name": "Bathurst", "state": "NSW", "lat": -33.4167, "lon": 149.5833},
    {"id": "nowra", "name": "Nowra", "state": "NSW", "lat": -34.8833, "lon": 150.6000},
    {"id": "queanbeyan", "name": "Queanbeyan", "state": "NSW", "lat": -35.3500, "lon": 149.2333},
    {"id": "melbourne", "name": "Melbourne", "state": "VIC", "lat": -37.8136, "lon": 144.9631},
    {"id": "geelong", "name": "Geelong", "state": "VIC", "lat": -38.1499, "lon": 144.3617},
    {"id": "ballarat", "name": "Ballarat", "state": "VIC", "lat": -37.5622, "lon": 143.8503},
    {"id": "bendigo", "name": "Bendigo", "state": "VIC", "lat": -36.7570, "lon": 144.2794},
    {"id": "shepparton", "name": "Shepparton", "state": "VIC", "lat": -36.3833, "lon": 145.4000},
    {"id": "traralgon", "name": "Traralgon", "state": "VIC", "lat": -38.1953, "lon": 146.5417},
    {"id": "mildura", "name": "Mildura", "state": "VIC", "lat": -34.1856, "lon": 142.1625},
    {"id": "warrnambool", "name": "Warrnambool", "state": "VIC", "lat": -38.3833, "lon": 142.4833},
    {"id": "brisbane", "name": "Brisbane", "state": "QLD", "lat": -27.4698, "lon": 153.0251},
    {"id": "gold-coast", "name": "Gold Coast", "state": "QLD", "lat": -28.0167, "lon": 153.4000},
    {"id": "ipswich", "name": "Ipswich", "state": "QLD", "lat": -27.6167, "lon": 152.7667},
    {"id": "toowoomba", "name": "Toowoomba", "state": "QLD", "lat": -27.5598, "lon": 151.9507},
    {"id": "sunshine-coast", "name": "Sunshine Coast", "state": "QLD", "lat": -26.6500, "lon": 153.0667},
    {"id": "townsville", "name": "Townsville", "state": "QLD", "lat": -19.2590, "lon": 146.8169},
    {"id": "cairns", "name": "Cairns", "state": "QLD", "lat": -16.9203, "lon": 145.7710},
    {"id": "rockhampton", "name": "Rockhampton", "state": "QLD", "lat": -23.3791, "lon": 150.5100},
    {"id": "mackay", "name": "Mackay", "state": "QLD", "lat": -21.1411, "lon": 149.1861},
    {"id": "bundaberg", "name": "Bundaberg", "state": "QLD", "lat": -24.8661, "lon": 152.3489},
    {"id": "adelaide", "name": "Adelaide", "state": "SA", "lat": -34.9285, "lon": 138.6007},
    {"id": "mount-gambier", "name": "Mount Gambier", "state": "SA", "lat": -37.8284, "lon": 140.7804},
    {"id": "port-augusta", "name": "Port Augusta", "state": "SA", "lat": -32.4939, "lon": 137.7728},
    {"id": "perth", "name": "Perth", "state": "WA", "lat": -31.9523, "lon": 115.8613},
    {"id": "bunbury", "name": "Bunbury", "state": "WA", "lat": -33.3271, "lon": 115.6414},
    {"id": "geraldton", "name": "Geraldton", "state": "WA", "lat": -28.7774, "lon": 114.6149},
    {"id": "kalgoorlie", "name": "Kalgoorlie", "state": "WA", "lat": -30.7490, "lon": 121.4660},
    {"id": "broome", "name": "Broome", "state": "WA", "lat": -17.9614, "lon": 122.2359},
    {"id": "karratha", "name": "Karratha", "state": "WA", "lat": -20.7377, "lon": 116.8463},
    {"id": "hobart", "name": "Hobart", "state": "TAS", "lat": -42.8821, "lon": 147.3272},
    {"id": "launceston", "name": "Launceston", "state": "TAS", "lat": -41.4332, "lon": 147.1441},
    {"id": "devonport", "name": "Devonport", "state": "TAS", "lat": -41.1806, "lon": 146.3464},
    {"id": "darwin", "name": "Darwin", "state": "NT", "lat": -12.4634, "lon": 130.8456},
    {"id": "alice-springs", "name": "Alice Springs", "state": "NT", "lat": -23.6980, "lon": 133.8807},
    {"id": "canberra", "name": "Canberra", "state": "ACT", "lat": -35.2809, "lon": 149.1300},
]

BY_ID = {place["id"]: place for place in PLACES}

# Timezone per state. Forecast hours must match the site clock, not Sydney's.
TZ_BY_STATE = {
    "NSW": "Australia/Sydney",
    "VIC": "Australia/Melbourne",
    "QLD": "Australia/Brisbane",
    "SA": "Australia/Adelaide",
    "WA": "Australia/Perth",
    "TAS": "Australia/Hobart",
    "NT": "Australia/Darwin",
    "ACT": "Australia/Sydney",
}
DEFAULT_TZ = "Australia/Sydney"


def timezone_for(place: dict | None) -> str:
    """Return the timezone for a place dict. Falls back to Sydney."""
    if not place:
        return DEFAULT_TZ
    return TZ_BY_STATE.get(place.get("state", ""), DEFAULT_TZ)


def search(query: str = "") -> list[dict]:
    """Prefix matches first, then substring matches. Empty query returns all."""
    needle = (query or "").strip().lower()
    if not needle:
        return PLACES
    prefix = []
    contains = []
    for place in PLACES:
        haystack = f"{place['name']} {place['state']}".lower()
        if place["name"].lower().startswith(needle):
            prefix.append(place)
        elif needle in haystack:
            contains.append(place)
    return prefix + contains


def get(identifier: str) -> dict | None:
    """Find a place by id, or by exact name, case-insensitive."""
    if not identifier:
        return None
    key = identifier.strip().lower()
    if key in BY_ID:
        return BY_ID[key]
    for place in PLACES:
        if place["name"].lower() == key:
            return place
    return None