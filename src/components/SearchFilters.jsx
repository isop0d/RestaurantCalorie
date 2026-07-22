// Search controls for the Explore page: zip code + how far away to look.
// (Calorie and dietary filters live on the restaurant page, applied to its menu,
// because menus aren't loaded during search.)
function SearchFilters({ filters, setFilters, onSearch }) {
  const update = (field, value) =>
    setFilters((prev) => ({ ...prev, [field]: value }))

  return (
    <div className="filters">
      <div className="filter-group">
        <label className="filter-label">Zip code</label>
        <input
          type="text"
          inputMode="numeric"
          className="zip-input"
          placeholder="e.g. 10001"
          value={filters.zip}
          onChange={(e) => update("zip", e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSearch()
          }}
        />
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
