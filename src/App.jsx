import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import "./index.css";

function App() {
  // home.html sets a global `username` when a logged-in user opens the page.
  // Fall back to "there" if it is not set so the greeting still reads well.
  const username = window.username || 'there'

  return (
    <>
      <Navbar />
      <Hero />
    </>
  );
}

export default App;