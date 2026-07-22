"""Gemini nutrition estimation. Given menu items (name + description), ask Gemini
for a rough calorie estimate AND inferred dietary tags per item, returned as
structured JSON. One Gemini call per menu (all items batched together).

Both calories and dietary tags are best-guess inferences from the item text, not
verified facts."""
import json
import os

import httpx

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Dietary tags Gemini may assign. Limited to what's inferable from an item's name
# and description — kosher/halal depend on preparation/certification, so we don't
# ask Gemini to guess those.
DIETARY_TAGS = ["vegetarian", "vegan", "gluten-free"]


def estimate_calories(items):
    """items: list of dicts with "name" and optional "description".
    Returns: list of {"name": str, "calories": int, "dietary_tags": [str]}.
    Calories and dietary_tags are Gemini best-guesses from the item text."""
    api_key = os.environ.get("VITE_GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("VITE_GEMINI_API_KEY is not configured")
    if not items:
        return []

    # Number each item so Gemini answers by index — we map results back onto our
    # own item names, avoiding fragile name-string matching.
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
        "by its index. For each item, using its name and description:\n"
        "1. Estimate the total calories of a typical single serving (always give "
        "a best-guess integer, even when unsure).\n"
        "2. List which of these dietary tags clearly apply: "
        + ", ".join(DIETARY_TAGS)
        + ". Only include a tag when the item clearly qualifies; use an empty "
        "list when unsure or none apply.\n\n"
        'Return a JSON array of {"index": <item index>, "calories": <integer>, '
        '"dietary_tags": [<tags>]}.\n\nMenu:\n' + menu_text
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
                        "dietary_tags": {
                            "type": "ARRAY",
                            "items": {"type": "STRING", "enum": DIETARY_TAGS},
                        },
                    },
                    "required": ["index", "calories", "dietary_tags"],
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

    # Map results back onto our items by index.
    by_index = {e["index"]: e for e in estimates if "index" in e}
    return [
        {
            "name": item.get("name"),
            "calories": by_index.get(i, {}).get("calories"),
            "dietary_tags": by_index.get(i, {}).get("dietary_tags") or [],
        }
        for i, item in enumerate(items)
    ]
