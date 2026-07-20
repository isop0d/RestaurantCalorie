import Map from './components/Map'

// Import the same images the login/register pages use so the map page has
// the identical hand-drawn look. Vite turns these into real URLs at build time.
import food from './assets/food.png'
import plant1 from './assets/plant1.jpg'
import plant2 from './assets/plant2.png'

function App() {
  // home.html sets a global `username` when a logged-in user opens the page.
  // Fall back to "there" if it is not set so the greeting still reads well.
  const username = window.username || 'there'

  return (
    <div className="page-container">
      {/* Corner decorations, placed exactly like the login page. */}
      <img src={plant2} className="bottom-left" alt="" />
      <img src={food} className="top-middle" style={{ top: '3%' }} alt="" />
      <img src={plant1} className="top-right" alt="" />

      {/* White bordered card, matching .content-section on login/register. */}
      <div className="content-section map-section">
        <h1 className="map-title">NutriSpot</h1>
        <p className="map-welcome">Welcome, {username}! Here are restaurants near you.</p>

        <Map />

        {/* Green scribble button with the same hover swap as the Log-In button. */}
        <a href="/home" className="btn-outline-info">Home</a>
      </div>
    </div>
  )
}

export default App
