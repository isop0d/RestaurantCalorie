// Helpers for the Explore restaurant search: calling the backend + distance math.
// Menus are NOT fetched here — search only lists restaurants (fast); a menu loads
// on the restaurant page when a card is opened.

// Search restaurants by zip via the backend (which caches the list in Supabase).
// `limit` controls how many of the cached list to return — raise it to show more.
// Returns { restaurants, totalAvailable }. Throws on network/API error.
export async function searchRestaurants(zip, limit = 3) {
  const resp = await fetch("/api/search-zip", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ postal_code: zip, limit }),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.error || `Search failed (${resp.status})`)
  }
  const data = await resp.json()
  return {
    restaurants: data.restaurants || [],
    totalAvailable: data.total_available || 0,
  }
}

// Distance between two lat/lng points in miles (Haversine formula).
export function distanceMiles(lat1, lng1, lat2, lng2) {
  if ([lat1, lng1, lat2, lng2].some((n) => typeof n !== "number")) return null
  const toRad = (deg) => (deg * Math.PI) / 180
  const earthRadiusMiles = 3958.8
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return earthRadiusMiles * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// Attach a distance (miles from the user) to each restaurant, keep only those
// within maxDistance, and sort closest-first. Restaurants missing coordinates
// are kept (distance null) so we never hide a result just for lacking lat/lng.
export function withinDistance(restaurants, userLat, userLng, maxDistance) {
  return restaurants
    .map((r) => ({ ...r, distance: distanceMiles(userLat, userLng, r.lat, r.lng) }))
    .filter(
      (r) => r.distance == null || maxDistance == null || r.distance <= maxDistance
    )
    .sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity))
}
