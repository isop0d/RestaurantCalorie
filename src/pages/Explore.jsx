import { useMemo, useState } from "react"
import Map from "../components/Map"
import SearchFilters from "../components/SearchFilters"
import {
  SAMPLE_RESTAURANTS,
  fetchRealRestaurants,
  filterRestaurants,
} from "../lib/restaurantSearch"

// The user's starting point for distance. Defaults to the map center (NYC);
// if the browser shares location we could update this later.
const DEFAULT_USER = { lat: 40.7128, lng: -74.006 }

// The Explore page: live map on top, then a search form to filter restaurants
// by calories, dietary restrictions, and distance from the user.
function Explore({ username }) {
  // The controls' current values.
  const [filters, setFilters] = useState({
    zip: "",
    minCalories: "",
    maxCalories: "",
    dietary: [],
    maxDistance: 10,
  })

  // The restaurants we filter over. We try real API data first and quietly
  // fall back to sample data if the API is not available on this machine.
  const [restaurants, setRestaurants] = useState(SAMPLE_RESTAURANTS)
  // Only recompute the filtered results when the user presses Search.
  const [appliedFilters, setAppliedFilters] = useState(null)
  const [loading, setLoading] = useState(false)
  // Reference point for the distance filter — updated to the searched area on
  // each search so distances make sense for any zip, not just New York.
  const [userLocation, setUserLocation] = useState(DEFAULT_USER)

  // Run the filters over the current restaurant list.
  const results = useMemo(() => {
    if (!appliedFilters) return []
    return filterRestaurants(restaurants, {
      minCalories: appliedFilters.minCalories === "" ? null : Number(appliedFilters.minCalories),
      maxCalories: appliedFilters.maxCalories === "" ? null : Number(appliedFilters.maxCalories),
      dietary: appliedFilters.dietary,
      maxDistance: appliedFilters.maxDistance,
      userLat: userLocation.lat,
      userLng: userLocation.lng,
    })
  }, [restaurants, appliedFilters, userLocation])

  const handleSearch = async () => {
    setLoading(true)
    // Search by the entered zip code. If it's blank, or the API returns nothing
    // (no keys, offline, or a zip OpenMenu doesn't cover), fall back to sample
    // data so the page still shows something to work with.
    const zip = filters.zip.trim()
    const real = zip ? await fetchRealRestaurants({ postal_code: zip }) : null
    const list = real || SAMPLE_RESTAURANTS
    setRestaurants(list)

    // Anchor the distance filter to the average location of the results, so
    // "within N miles" is measured from the searched area rather than New York.
    const located = list.filter((e) => typeof e.restaurant.lat === "number")
    setUserLocation(
      located.length > 0
        ? {
            lat: located.reduce((s, e) => s + e.restaurant.lat, 0) / located.length,
            lng: located.reduce((s, e) => s + e.restaurant.lng, 0) / located.length,
          }
        : DEFAULT_USER
    )

    setAppliedFilters({ ...filters })
    setLoading(false)
  }

  return (
    <main className="explore">
      <h1 className="explore-title">Explore Restaurants</h1>
      <p className="explore-welcome">
        Welcome, {username}! Search restaurants by calories, dietary needs, and
        distance.
      </p>

      <Map />

      <SearchFilters
        filters={filters}
        setFilters={setFilters}
        onSearch={handleSearch}
      />

      <div className="results">
        {loading && <p className="no-results">Searching…</p>}

        {!loading && appliedFilters && results.length === 0 && (
          <p className="no-results">No restaurants match those filters.</p>
        )}

        {!loading &&
          results.map((entry) => (
            <div key={entry.restaurant.name} className="result-card">
              <div className="result-head">
                <h3>{entry.restaurant.name}</h3>
                {entry.distance != null && (
                  <span className="distance">{entry.distance.toFixed(1)} mi</span>
                )}
              </div>
              {entry.restaurant.cuisine && (
                <p className="cuisine">{entry.restaurant.cuisine}</p>
              )}
              <ul className="item-list">
                {entry.items.map((item) => (
                  <li key={item.name}>
                    <span className="item-name">{item.name}</span>
                    <span className="item-cals">
                      {item.calories != null ? `${item.calories} cal` : "—"}
                    </span>
                    {item.dietary_tags?.length > 0 && (
                      <span className="item-tags">
                        {item.dietary_tags.join(", ")}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
      </div>
    </main>
  )
}

export default Explore
