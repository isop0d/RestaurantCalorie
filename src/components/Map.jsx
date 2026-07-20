import { useEffect, useRef, useState } from 'react'
import { loadGoogleMaps, isGoogleMapsConfigured } from '../lib/googleMaps'

// A reusable Google Map. Drop it anywhere with <Map />.
//
// Props:
//   center - { lat, lng } where the map starts (defaults to New York City)
//   zoom   - how far in the map is zoomed (bigger number = closer)
function Map({ center = { lat: 40.7128, lng: -74.006 }, zoom = 13 }) {
  // This div is the box the Google map draws itself into.
  const mapRef = useRef(null)
  // Track a friendly error message so we can show it instead of a blank box.
  const [error, setError] = useState('')

  useEffect(() => {
    // If the key is missing, tell the developer instead of loading nothing.
    if (!isGoogleMapsConfigured) {
      setError('Google Maps is not set up yet. Add VITE_GOOGLE_MAPS_API_KEY to .env')
      return
    }

    // loadGoogleMaps() returns a Promise, so we wait for the script, then draw.
    loadGoogleMaps()
      .then((maps) => {
        // The div might be gone if the component unmounted while loading.
        if (!mapRef.current) return
        new maps.Map(mapRef.current, { center, zoom })
      })
      .catch((err) => setError(err.message))
    // We only want this to run once when the component first appears.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (error) {
    return <div className="map-message">{error}</div>
  }

  // The map needs a size, so give the container a fixed height.
  return <div ref={mapRef} className="map-container" />
}

export default Map
