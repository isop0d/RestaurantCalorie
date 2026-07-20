import Map from "../components/Map";

// The Explore page shows the live Google Map. The nav bar's
// "Explore Restaurants" link points here (/explore).
function Explore({ username }) {
  return (
    <main className="explore">
      <h1 className="explore-title">Explore Restaurants</h1>
      <p className="explore-welcome">
        Welcome, {username}! Here are restaurants near you.
      </p>

      <Map />
    </main>
  );
}

export default Explore;
