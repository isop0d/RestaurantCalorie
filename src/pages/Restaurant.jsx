import { useEffect, useMemo, useState } from "react"

const DIETARY_OPTIONS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten-free", label: "Gluten-Free" },
]

const CALORIE_PRESETS = [
  { label: "Any", min: "", max: "" },
  { label: "Under 500", min: "", max: "500" },
  { label: "500+", min: "500", max: "" },
]

// The restaurant id comes from the URL: /restaurant?id=<openmenu_id>.
function getRestaurantId() {
  return new URLSearchParams(window.location.search).get("id") || ""
}

// Does a menu item pass the calorie range + selected dietary restrictions?
function itemMatches(item, { minCal, maxCal, dietary }) {
  const cals = item.calories
  if (minCal !== "" && (cals == null || cals < Number(minCal))) return false
  if (maxCal !== "" && (cals == null || cals > Number(maxCal))) return false
  // Every selected restriction must be present on the item.
  for (const tag of dietary) {
    if (!(item.dietary_tags || []).includes(tag)) return false
  }
  return true
}

// The restaurant landing page: fetches one restaurant's menu (with calorie
// estimates) on open, and lets the user filter it by calories and dietary tags.
function Restaurant() {
  const openmenuId = getRestaurantId()
  const [data, setData] = useState(null) // { restaurant, items }
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const [minCal, setMinCal] = useState("")
  const [maxCal, setMaxCal] = useState("")
  const [dietary, setDietary] = useState([])
  const [query , setQuery] = useState("")

  useEffect(() => {
    if (!openmenuId) {
      setError("No restaurant specified.")
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    fetch("/api/restaurant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ openmenu_id: openmenuId }),
    })
      .then(async (resp) => {
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}))
          throw new Error(d.error || `Failed to load menu (${resp.status})`)
        }
        return resp.json()
      })
      .then((d) => {
        if (!cancelled) {
          setData(d)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load menu.")
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [openmenuId])

  const toggleDietary = (value) =>
    setDietary((prev) =>
      prev.includes(value) ? prev.filter((d) => d !== value) : [...prev, value]
    )

  const items = data?.items || []
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter((it) => {
      if (!itemMatches(it, { minCal, maxCal, dietary })) return false
      if (q) {
        const haystack = `${it.name} ${it.description || ""}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [items, query, minCal, maxCal, dietary])

  return (
    <main className="explore">
      <a href="/explore" className="back-link">
        ← Back to search
      </a>

      {loading && (
        <p className="no-results">
          Loading menu… the first time can take a little while while we estimate
          calories.
        </p>
      )}
      {!loading && error && <p className="no-results">{error}</p>}

      {!loading && !error && data && (
        <>
          <h1 className="explore-title">
            {data.restaurant?.name || "Restaurant"}
          </h1>
          {data.restaurant?.address && (
            <p className="explore-welcome">{data.restaurant.address}</p>
          )}

          <div className="filters">
            <div className="filter-group">
              <label className="filter-label">Search menu</label>
              <input
                type="text"
                className="menu-search"
                placeholder="Search dishes… e.g. coffee"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label className="filter-label">Calories</label>
              <div className="calorie-presets">
                {CALORIE_PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    className={
                      minCal === p.min && maxCal === p.max
                        ? "preset active"
                        : "preset"
                    }
                    onClick={() => {
                      setMinCal(p.min)
                      setMaxCal(p.max)
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <div className="calorie-inputs">
                <input
                  type="number"
                  placeholder="Min"
                  value={minCal}
                  onChange={(e) => setMinCal(e.target.value)}
                />
                <span>to</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={maxCal}
                  onChange={(e) => setMaxCal(e.target.value)}
                />
              </div>
            </div>

            <div className="filter-group">
              <label className="filter-label">Dietary restrictions</label>
              <div className="dietary-options">
                {DIETARY_OPTIONS.map((opt) => (
                  <label key={opt.value} className="checkbox">
                    <input
                      type="checkbox"
                      checked={dietary.includes(opt.value)}
                      onChange={() => toggleDietary(opt.value)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="results">
            {filtered.length === 0 ? (
              <p className="no-results">
                {items.length === 0
                  ? "No menu items available for this restaurant."
                  : "No menu items match those filters."}
              </p>
            ) : (
              <ul className="item-list menu-list">
                {filtered.map((item) => (
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
            )}
          </div>
        </>
      )}
    </main>
  )
}

export default Restaurant
