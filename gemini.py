"""Gemini calorie estimation. Given menu items (name + description), ask Gemini
for a rough calorie estimate per item and return structured JSON.

Basic MVP: calories only, estimated from the item name/description. One Gemini
call per menu (all items batched together)."""
import json
import os

import httpx

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def estimate_calories(items):
    """items: list of dicts with "name" and optional "description".
    Returns: list of {"name": str, "calories": int}."""
    api_key = os.environ.get("VITE_GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("VITE_GEMINI_API_KEY is not configured")
    if not items:
        return []

    # Number each item so Gemini answers by index — we map calories back onto
    # our own item names, avoiding fragile name-string matching.
    menu_lines = []
    for i, item in enumerate(items):
        name = (item.get("name") or "").strip()
        desc = (item.get("description") or "").strip()
        line = f"{i}. {name}"
        if desc:
            line += f" — {desc}"
        menu_lines.append(line)
    menu_text = "\n".join(menu_lines)

    prompt = (
        "You are a nutrition estimator. Each line below is a menu item prefixed "
        "by its index. Estimate the total calories of a typical single serving "
        "for each, using the name and description. Always give a best-guess "
        'integer even when unsure. Return a JSON array of {"index": <the item '
        'index>, "calories": <integer>}.\n\nMenu:\n' + menu_text
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "index": {"type": "INTEGER"},
                        "calories": {"type": "INTEGER"},
                    },
                    "required": ["index", "calories"],
                },
            },
        },
    }

    resp = httpx.post(GEMINI_URL, params={"key": api_key}, json=body, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini request failed ({resp.status_code}): {resp.text[:200]}")
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    estimates = json.loads(text)

    # Map calories back onto our items by index.
    by_index = {e["index"]: e["calories"] for e in estimates if "index" in e}
    return [
        {"name": item.get("name"), "calories": by_index.get(i)}
        for i, item in enumerate(items)
    ]
