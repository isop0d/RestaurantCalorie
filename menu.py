"""Menu ingestion: fetch a restaurant + its menu from OpenMenu and cache it in
Supabase. This is a Python port of the former `fetch-menu` Supabase Edge
Function. Pass openmenu_id="sample" to use OpenMenu's sandbox (no key, no
credits)."""
import os
from datetime import datetime, timezone

import httpx
from supabase import Client, create_client

from gemini import estimate_calories

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


def _cached_restaurant_id(supabase, openmenu_id):
    resp = (
        supabase.table("restaurants")
        .select("id")
        .eq("openmenu_id", openmenu_id)
        .limit(1)
        .execute()
    )
    return resp.data[0]["id"] if resp.data else None


def _cached_menu_rows(supabase, restaurant_id):
    resp = (
        supabase.table("menu_items")
        .select(
            "id, restaurant_id, name, description, calories, dietary_tags, estimated_at"
        )
        .eq("restaurant_id", restaurant_id)
        .execute()
    )
    return resp.data or []


def _public_item(row):
    return {
        "name": row["name"],
        "description": row.get("description"),
        "calories": row.get("calories"),
        "dietary_tags": row.get("dietary_tags") or [],
    }


def get_menu_with_estimates(openmenu_id, refresh=False):
    """Return a restaurant's menu items WITH calorie estimates, using Supabase
    as a cache. The first lookup for a restaurant hits OpenMenu + Gemini and
    writes the results back; later lookups read straight from the DB (fast).

    Pass refresh=True to bypass the cache and re-run OpenMenu + Gemini — e.g. to
    pick up newly-added dietary tags on a restaurant that was cached earlier.

    Returns [{name, description, calories, dietary_tags}].
    Requires SUPABASE_SERVICE_ROLE_KEY (writes bypass RLS)."""
    supabase = _admin_client()

    # Warm path: restaurant already cached with a fully-estimated menu. Skipped
    # on refresh so we re-estimate from scratch.
    if not refresh:
        restaurant_id = _cached_restaurant_id(supabase, openmenu_id)
        if restaurant_id:
            rows = _cached_menu_rows(supabase, restaurant_id)
            if rows and all(row.get("estimated_at") for row in rows):
                return [_public_item(row) for row in rows]

    # Cold path: pull + cache the menu (restaurant + items, no estimates yet),
    # then re-read the rows we just wrote so we have their ids.
    fetch_and_cache_menu(openmenu_id)
    restaurant_id = _cached_restaurant_id(supabase, openmenu_id)
    rows = _cached_menu_rows(supabase, restaurant_id)

    # Ask Gemini for calorie estimates + inferred dietary tags (one call), then
    # merge onto our rows: keep any calories OpenMenu already gave us, fill the
    # rest from Gemini, and union Gemini's dietary tags with OpenMenu's.
    if rows:
        gemini_by_name = {est["name"]: est for est in estimate_calories(rows)}
        for row in rows:
            est = gemini_by_name.get(row["name"], {})
            if row.get("calories") is None:
                row["calories"] = est.get("calories")
            tags = [*(row.get("dietary_tags") or []), *(est.get("dietary_tags") or [])]
            row["dietary_tags"] = list(dict.fromkeys(tags)) or None

    # Stamp every row as estimated so future lookups are a warm cache hit, and
    # write the calories + timestamp back in one batched update (keyed by id).
    now = datetime.now(timezone.utc).isoformat()
    if rows:
        supabase.table("menu_items").upsert(
            [
                {
                    "id": row["id"],
                    "restaurant_id": row["restaurant_id"],
                    "name": row["name"],
                    "description": row.get("description"),
                    "dietary_tags": row.get("dietary_tags"),
                    "calories": row.get("calories"),
                    "estimated_at": now,
                }
                for row in rows
            ],
            on_conflict="id",
        ).execute()
        for row in rows:
            row["estimated_at"] = now

    return [_public_item(row) for row in rows]


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


def search_zip(zip_code, country="US"):
    """Return the full list of restaurants for a zip, using Supabase as a cache.
    The first search hits OpenMenu's location.php and stores the whole list; every
    later search of the same zip is a single DB read. Does NOT fetch menus — those
    load lazily when a restaurant is opened (see get_restaurant_with_menu).

    Returns [{openmenu_id, name, address, lat, lng, cuisine}].
    Requires SUPABASE_SERVICE_ROLE_KEY (writes bypass RLS)."""
    if not zip_code:
        raise ValueError("A zip code is required")

    supabase = _admin_client()

    cached = (
        supabase.table("zip_searches")
        .select("restaurants")
        .eq("zip", zip_code)
        .eq("country", country)
        .limit(1)
        .execute()
    )
    if cached.data:
        return cached.data[0]["restaurants"]

    found = search_restaurants(postal_code=zip_code, country=country)
    supabase.table("zip_searches").upsert(
        {"zip": zip_code, "country": country, "restaurants": found},
        on_conflict="zip,country",
    ).execute()
    return found


def get_restaurant_with_menu(openmenu_id, refresh=False):
    """Restaurant detail: the restaurant's basic info plus its menu with calorie
    estimates (cached). Called when a user opens a restaurant, so the expensive
    OpenMenu + Gemini work happens once, on demand — not during search.

    Pass refresh=True to force a re-estimate (bypasses the cache).

    Returns {restaurant: {openmenu_id, name, address, lat, lng}, items: [...]}."""
    items = get_menu_with_estimates(openmenu_id, refresh=refresh)
    supabase = _admin_client()
    resp = (
        supabase.table("restaurants")
        .select("openmenu_id, name, address, lat, lng")
        .eq("openmenu_id", openmenu_id)
        .limit(1)
        .execute()
    )
    restaurant = resp.data[0] if resp.data else {"openmenu_id": openmenu_id}
    return {"restaurant": restaurant, "items": items}
