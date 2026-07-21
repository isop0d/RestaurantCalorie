// Helpers for the Explore search feature: distance math, sample data, and the
// filter logic. Kept separate from the UI so it is easy to read and reuse.

// Try to fetch real restaurants from the backend. Returns an array of
// { restaurant, items } on success, or null if the API is not available
// (no keys, backend down, etc.) so the caller can fall back to mock data.
export async function fetchRealRestaurants(location) {
  try {
    const resp = await fetch("/api/explore-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(location),
    })
    if (!resp.ok) return null
    const data = await resp.json()
    // Only use it if the API actually returned some restaurants.
    if (Array.isArray(data.restaurants) && data.restaurants.length > 0) {
      return data.restaurants
    }
    return null
  } catch {
    // Network error, no server, etc. — fall back to mock data.
    return null
  }
}

// Distance between two lat/lng points in miles (Haversine formula).
// Used to work out how far each restaurant is from the user.
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

// Sample restaurants so the search UI works even before the API keys are added.
// Real results from /api/explore-search have the same shape, so the same filter
// code handles both. Coordinates are around New York City (the map's default).
export const SAMPLE_RESTAURANTS = [
  {
    restaurant: {
      name: "Green Leaf Bowls",
      cuisine: "Healthy",
      address: "12 Park Ave, New York, NY",
      lat: 40.7138,
      lng: -74.004,
    },
    items: [
      { name: "Quinoa Veggie Bowl", calories: 420, dietary_tags: ["vegan", "gluten-free"] },
      { name: "Grilled Chicken Salad", calories: 380, dietary_tags: ["gluten-free"] },
    ],
  },
  {
    restaurant: {
      name: "Burger Barn",
      cuisine: "American",
      address: "88 Broadway, New York, NY",
      lat: 40.7075,
      lng: -74.011,
    },
    items: [
      { name: "Double Bacon Burger", calories: 980, dietary_tags: [] },
      { name: "Loaded Fries", calories: 720, dietary_tags: ["vegetarian"] },
    ],
  },
  {
    restaurant: {
      name: "Pasta Palace",
      cuisine: "Italian",
      address: "5 Mulberry St, New York, NY",
      lat: 40.719,
      lng: -73.997,
    },
    items: [
      { name: "Fettuccine Alfredo", calories: 850, dietary_tags: ["vegetarian"] },
      { name: "Garden Veggie Primavera", calories: 510, dietary_tags: ["vegetarian", "vegan"] },
    ],
  },
  {
    restaurant: {
      name: "Sushi Zen",
      cuisine: "Japanese",
      address: "300 5th Ave, New York, NY",
      lat: 40.744,
      lng: -73.987,
    },
    items: [
      { name: "Avocado Roll", calories: 240, dietary_tags: ["vegan", "gluten-free"] },
      { name: "Salmon Nigiri", calories: 310, dietary_tags: ["gluten-free"] },
    ],
  },
]

// Keep only the menu items in a restaurant that pass the calorie + dietary
// filters. Returns the matching items (empty if none match).
function matchingItems(items, filters) {
  return (items || []).filter((item) => {
    const cals = item.calories
    if (filters.minCalories != null && (cals == null || cals < filters.minCalories)) {
      return false
    }
    if (filters.maxCalories != null && (cals == null || cals > filters.maxCalories)) {
      return false
    }
    // Every selected dietary restriction must be present on the item.
    for (const tag of filters.dietary) {
      if (!(item.dietary_tags || []).includes(tag)) return false
    }
    return true
  })
}

// Apply all filters to the list of restaurants.
// filters = { minCalories, maxCalories, dietary: [], maxDistance, userLat, userLng }
// Returns restaurants that still have at least one matching item, each with a
// `distance` (miles) and only the items that matched.
export function filterRestaurants(restaurants, filters) {
  const out = []
  for (const entry of restaurants) {
    const items = matchingItems(entry.items, filters)
    if (items.length === 0) continue

    const { lat, lng } = entry.restaurant
    const distance = distanceMiles(filters.userLat, filters.userLng, lat, lng)
    if (
      filters.maxDistance != null &&
      distance != null &&
      distance > filters.maxDistance
    ) {
      continue
    }

    out.push({ ...entry, items, distance })
  }
  // Closest first when we know the distances.
  out.sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity))
  return out
}
