"""Menu ingestion: fetch a restaurant + its menu from OpenMenu and cache it in
Supabase. This is a Python port of the former `fetch-menu` Supabase Edge
Function. Pass openmenu_id="sample" to use OpenMenu's sandbox (no key, no
credits)."""
import os

import httpx
from supabase import Client, create_client

OPENMENU_BASE = "https://www.openmenu.com/api/v2"

# OpenMenu returns every value as a string ("" when absent, "1"/"0" for flags).


def _to_cents(price):
    try:
        return round(float(price) * 100)
    except (TypeError, ValueError):
        return None


def _to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_DIETARY_FLAGS = {
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "kosher": "kosher",
    "halal": "halal",
    "gluten_free": "gluten-free",
}


def _dietary_tags(item):
    return [tag for key, tag in _DIETARY_FLAGS.items() if item.get(key) == "1"]


def _format_address(info):
    """Stitch OpenMenu's separate address fields into one string."""
    return ", ".join(
        part
        for part in [
            info.get("address_1"),
            info.get("address_2"),
            info.get("city_town"),
            info.get("state_province"),
            info.get("postal_code"),
        ]
        if part
    )


def _admin_client() -> Client:
    """Supabase client using the service-role key, which bypasses RLS so we can
    write to restaurants/menu_items from the server (mirrors the Edge Function's
    ctx.supabaseAdmin)."""
    url = os.environ["VITE_SUPABASE_URL"]
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not service_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. Add it to .env from the "
            "Supabase dashboard (Settings > API > service_role key). It bypasses "
            "RLS, so it must stay server-side — never give it a VITE_ prefix."
        )
    return create_client(url, service_key)


def _openmenu_restaurant(openmenu_id):
    """Fetch a restaurant's full profile + menu from OpenMenu; return the
    `result` dict. openmenu_id="sample" uses the sandbox (no key, no credit)."""
    if not isinstance(openmenu_id, str) or not openmenu_id:
        raise ValueError("openmenu_id must be a non-empty string")

    params = {"id": openmenu_id}
    if openmenu_id != "sample":
        api_key = os.environ.get("VITE_OPENMENU_API_KEY")
        if not api_key:
            raise RuntimeError("VITE_OPENMENU_API_KEY is not configured")
        params["key"] = api_key

    resp = httpx.get(f"{OPENMENU_BASE}/restaurant.php", params=params, timeout=15)
    payload = resp.json() if resp.status_code == 200 else None
    envelope = (payload or {}).get("response", {})
    result = envelope.get("result")
    api_status = envelope.get("api", {}).get("status")
    if api_status != 200 or not result:
        raise RuntimeError(
            f"OpenMenu request failed (status {api_status or resp.status_code})"
        )
    return result


def _extract_items(result):
    """Flatten OpenMenu's menus -> groups -> items into a deduped list of
    {name, description, price_cents, calories, dietary_tags}. Deduped by name
    since the same item can appear on multiple menus (e.g. lunch and dinner)."""
    items = {}
    for menu in result.get("menus") or []:
        for group in menu.get("menu_groups") or []:
            for item in group.get("menu_items") or []:
                name = (item.get("menu_item_name") or "").strip()
                if not name or name in items:
                    continue
                tags = _dietary_tags(item)
                items[name] = {
                    "name": name,
                    "description": item.get("menu_item_description") or None,
                    "price_cents": _to_cents(item.get("menu_item_price")),
                    "calories": _to_number(item.get("menu_item_calories")),
                    "dietary_tags": tags or None,
                }
    return list(items.values())


def fetch_menu_items(openmenu_id):
    """Read-only: fetch a restaurant's menu items from OpenMenu WITHOUT caching.
    Returns [{name, description, price_cents, calories, dietary_tags}]. Needs no
    service-role key — used by the no-cache MVP loop."""
    return _extract_items(_openmenu_restaurant(openmenu_id))


def fetch_and_cache_menu(openmenu_id: str) -> dict:
    result = _openmenu_restaurant(openmenu_id)
    info = result.get("restaurant_info", {})

    supabase = _admin_client()
    restaurant_resp = (
        supabase.table("restaurants")
        .upsert(
            {
                "openmenu_id": result.get("id"),
                "name": info.get("restaurant_name") or "Unknown restaurant",
                "address": _format_address(info) or None,
                "lat": _to_number(info.get("latitude")),
                "lng": _to_number(info.get("longitude")),
            },
            on_conflict="openmenu_id",
        )
        .execute()
    )
    restaurant = restaurant_resp.data[0]

    rows = [
        {**item, "restaurant_id": restaurant["id"]}
        for item in _extract_items(result)
    ]

    inserted = 0
    if rows:
        # ignore_duplicates -> ON CONFLICT DO NOTHING: re-fetching a menu never
        # overwrites rows that already hold Gemini nutrition estimates.
        items_resp = (
            supabase.table("menu_items")
            .upsert(rows, on_conflict="restaurant_id,name", ignore_duplicates=True)
            .execute()
        )
        inserted = len(items_resp.data or [])

    return {
        "restaurant": {"id": restaurant["id"], "name": restaurant["name"]},
        "items_found": len(rows),
        "items_inserted": inserted,
    }


def search_restaurants(
    postal_code=None, city=None, state=None, country="US", name=None
):
    """Find restaurants near a location via OpenMenu's location.php. Read-only:
    returns a list of {openmenu_id, name, address, lat, lng, cuisine}. The
    openmenu_id on each result is what fetch_and_cache_menu() takes.

    Pass name="sample" to use OpenMenu's sandbox (no key, no credits)."""
    if not postal_code and not city:
        raise ValueError("Provide at least a postal_code or a city")

    params = {"country": country}
    if postal_code:
        params["postal_code"] = postal_code
    if city:
        params["city"] = city
    if state:
        params["state"] = state

    if name == "sample":
        params["s"] = "sample"  # sandbox mode, no key
    else:
        api_key = os.environ.get("VITE_OPENMENU_API_KEY")
        if not api_key:
            raise RuntimeError("VITE_OPENMENU_API_KEY is not configured")
        params["key"] = api_key
        if name:
            params["s"] = name  # optional name filter

    resp = httpx.get(f"{OPENMENU_BASE}/location.php", params=params, timeout=15)
    payload = resp.json() if resp.status_code == 200 else None
    envelope = (payload or {}).get("response", {})
    api_status = envelope.get("api", {}).get("status")
    if api_status != 200:
        raise RuntimeError(
            f"OpenMenu search failed (status {api_status or resp.status_code})"
        )

    restaurants = envelope.get("result", {}).get("restaurants") or []
    return [
        {
            "openmenu_id": r.get("id"),
            "name": r.get("restaurant_name"),
            "address": _format_address(r) or None,
            "lat": _to_number(r.get("latitude")),
            "lng": _to_number(r.get("longitude")),
            "cuisine": r.get("cuisine_type_primary") or None,
        }
        for r in restaurants
    ]
