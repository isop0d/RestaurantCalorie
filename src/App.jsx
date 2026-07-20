import Map from './components/Map'

function App() {
  // home.html sets a global `username` when a logged-in user opens the page.
  // Fall back to "there" if it is not set so the greeting still reads well.
  const username = window.username || 'there'

  return (
    <div className="home-page">
      <h1>NutriSpot</h1>
      <p>Welcome, {username}! Here are restaurants near you.</p>
      <Map />
    </div>
  )
}

export default App
