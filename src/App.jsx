import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import Explore from "./pages/Explore";
import Restaurant from "./pages/Restaurant";
import "./index.css";

function App() {
  // home.html sets a global `username` when a logged-in user opens the page.
  // Fall back to "there" if it is not set so the greeting still reads well.
  const username = window.username || 'there'

  // Simple routing without a library: pick a page from the URL path.
  //   /restaurant -> restaurant detail (menu)
  //   /explore    -> search page
  //   anything else -> home hero
  const path = window.location.pathname
  let page = <Hero />
  if (path.startsWith("/restaurant")) page = <Restaurant />
  else if (path.startsWith("/explore")) page = <Explore username={username} />

  return (
    <>
      <Navbar />
      {page}
    </>
  );
}

export default App;
