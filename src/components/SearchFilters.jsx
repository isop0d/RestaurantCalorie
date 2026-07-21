// The filter controls for the Explore search: calorie range, dietary
// restrictions, and how far away the restaurant can be.
const DIETARY_OPTIONS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten-free", label: "Gluten-Free" },
]

// Quick calorie presets so users don't have to think in numbers.
const CALORIE_PRESETS = [
  { label: "Any", min: "", max: "" },
  { label: "Low (under 500)", min: "", max: "500" },
  { label: "High (500+)", min: "500", max: "" },
]

function SearchFilters({ filters, setFilters, onSearch }) {
  // Update one field of the filters object at a time.
  const update = (field, value) =>
    setFilters((prev) => ({ ...prev, [field]: value }))

  // Turn a dietary checkbox on or off.
  const toggleDietary = (value) =>
    setFilters((prev) => ({
      ...prev,
      dietary: prev.dietary.includes(value)
        ? prev.dietary.filter((d) => d !== value)
        : [...prev.dietary, value],
    }))

  return (
    <div className="filters">
      <div className="filter-group">
        <label className="filter-label">Calories</label>
        <div className="calorie-presets">
          {CALORIE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className={
                filters.minCalories === preset.min &&
                filters.maxCalories === preset.max
                  ? "preset active"
                  : "preset"
              }
              onClick={() => {
                update("minCalories", preset.min)
                update("maxCalories", preset.max)
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="calorie-inputs">
          <input
            type="number"
            placeholder="Min"
            value={filters.minCalories}
            onChange={(e) => update("minCalories", e.target.value)}
          />
          <span>to</span>
          <input
            type="number"
            placeholder="Max"
            value={filters.maxCalories}
            onChange={(e) => update("maxCalories", e.target.value)}
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
                checked={filters.dietary.includes(opt.value)}
                onChange={() => toggleDietary(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      <div className="filter-group">
        <label className="filter-label">
          Distance: within {filters.maxDistance} miles
        </label>
        <input
          type="range"
          min="1"
          max="25"
          value={filters.maxDistance}
          onChange={(e) => update("maxDistance", Number(e.target.value))}
        />
      </div>

      <button type="button" className="search-button" onClick={onSearch}>
        Search
      </button>
    </div>
  )
}

export default SearchFilters
