import { useMemo, useState } from "react"
import Map from "../components/Map"
import SearchFilters from "../components/SearchFilters"
import { searchRestaurants, withinDistance } from "../lib/restaurantSearch"

// Fallback reference point for distance (NYC) until a search anchors it to the
// searched area.
const DEFAULT_USER = { lat: 40.7128, lng: -74.006 }
// How many more restaurants each "Show more" adds.
const PAGE = 3

// Average lat/lng of the restaurants that have coordinates, or null.
function averageLocation(list) {
  const located = list.filter((r) => typeof r.lat === "number")
  if (located.length === 0) return null
  return {
    lat: located.reduce((s, r) => s + r.lat, 0) / located.length,
    lng: located.reduce((s, r) => s + r.lng, 0) / located.length,
  }
}

// The Explore page: search restaurants by zip, filter by distance, and open one
// to see its menu. Menus load on the restaurant page (not here), so search is fast.
function Explore({ username }) {
  const [filters, setFilters] = useState({ zip: "", maxDistance: 10 })
  const [restaurants, setRestaurants] = useState([])
  const [totalAvailable, setTotalAvailable] = useState(0)
  const [limit, setLimit] = useState(PAGE)
  const [userLocation, setUserLocation] = useState(DEFAULT_USER)
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  // Filter by distance live as the slider moves (no re-fetch needed).
  const results = useMemo(
    () =>
      withinDistance(
        restaurants,
        userLocation.lat,
        userLocation.lng,
        filters.maxDistance
      ),
    [restaurants, userLocation, filters.maxDistance]
  )

  const runSearch = async (searchLimit) => {
    const zip = filters.zip.trim()
    if (!zip) {
      setError("Enter a zip code to search.")
      return
    }
    setLoading(true)
    setError("")
    try {
      const { restaurants: found, totalAvailable: total } =
        await searchRestaurants(zip, searchLimit)
      setRestaurants(found)
      setTotalAvailable(total)
      setUserLocation(averageLocation(found) || DEFAULT_USER)
      setSearched(true)
    } catch (err) {
      setError(err.message || "Search failed.")
      setRestaurants([])
      setTotalAvailable(0)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    setLimit(PAGE)
    runSearch(PAGE)
  }

  const handleShowMore = () => {
    const next = limit + PAGE
    setLimit(next)
    runSearch(next)
  }

  const canShowMore = searched && !loading && totalAvailable > restaurants.length

  return (
    <main className="explore">
      <h1 className="explore-title">Explore Restaurants</h1>
      <p className="explore-welcome">
        Welcome, {username}! Search restaurants by zip, then open one to see its
        menu and calorie estimates.
      </p>

      <Map />

      <SearchFilters
        filters={filters}
        setFilters={setFilters}
        onSearch={handleSearch}
      />

      <div className="results">
        {loading && <p className="no-results">Searching…</p>}
        {!loading && error && <p className="no-results">{error}</p>}
        {!loading && !error && searched && results.length === 0 && (
          <p className="no-results">
            No restaurants found near that zip. Try a wider distance or another
            zip.
          </p>
        )}

        {!loading &&
          results.map((r) => (
            <a
              key={r.openmenu_id}
              className="result-card result-card-link"
              href={`/restaurant?id=${encodeURIComponent(r.openmenu_id)}`}
            >
              <div className="result-head">
                <h3>{r.name}</h3>
                {r.distance != null && (
                  <span className="distance">{r.distance.toFixed(1)} mi</span>
                )}
              </div>
              {r.cuisine && <p className="cuisine">{r.cuisine}</p>}
              {r.address && <p className="result-address">{r.address}</p>}
              <span className="view-menu">View menu →</span>
            </a>
          ))}

        {canShowMore && (
          <button
            type="button"
            className="search-button show-more"
            onClick={handleShowMore}
          >
            Show more restaurants
          </button>
        )}
      </div>
    </main>
  )
}

export default Explore
