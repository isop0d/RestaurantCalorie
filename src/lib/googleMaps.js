// Small helper for loading the Google Maps JavaScript API.
//
// We follow the same idea as src/lib/supabase.js: read the key from the
// environment, expose a flag so the UI can react when it is missing, and keep
// everything in one place so the rest of the app never touches the raw script.

// Vite exposes anything prefixed with VITE_ on import.meta.env at build time.
const googleMapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY

// The UI can check this before trying to show a map (see supabase.js pattern).
export const isGoogleMapsConfigured = Boolean(googleMapsApiKey)

// We remember the loading Promise so that if two components ask for the map at
// the same time we still only add the <script> tag once.
let loadPromise = null

// Load the Google Maps script and resolve once window.google is ready.
// Returns a Promise so callers can `await loadGoogleMaps()` before using maps.
export function loadGoogleMaps() {
  // If the key is missing, fail early with a clear message for the developer.
  if (!isGoogleMapsConfigured) {
    return Promise.reject(
      new Error('Missing VITE_GOOGLE_MAPS_API_KEY in your .env file')
    )
  }

  // If Google Maps is already on the page, reuse it.
  if (window.google && window.google.maps) {
    return Promise.resolve(window.google.maps)
  }

  // If we already started loading, return that same Promise.
  if (loadPromise) {
    return loadPromise
  }

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    // "places" is included now so restaurant search works later on.
    script.src =
      `https://maps.googleapis.com/maps/api/js?key=${googleMapsApiKey}&libraries=places`
    script.async = true
    script.defer = true
    script.onload = () => resolve(window.google.maps)
    script.onerror = () => reject(new Error('Failed to load Google Maps'))
    document.head.appendChild(script)
  })

  return loadPromise
}
