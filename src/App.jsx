import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import Explore from "./pages/Explore";
import "./index.css";

function App() {
  // home.html sets a global `username` when a logged-in user opens the page.
  // Fall back to "there" if it is not set so the greeting still reads well.
  const username = window.username || 'there'

  // Simple routing without a library: look at the URL path and pick a page.
  // "/explore" shows the live map, anything else shows the home hero.
  const path = window.location.pathname
  const showExplore = path.startsWith("/explore")

  return (
    <>
      <Navbar />
      {showExplore ? <Explore username={username} /> : <Hero />}
    </>
  );
}

export default App;
