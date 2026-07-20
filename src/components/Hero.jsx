import Button from "./Button";

import heroMap from "../assets/images/hero-map.png";
import fruitSalad from "../assets/images/salad.svg";
import lemonade from "../assets/images/lemonade.svg";
import plant from "../assets/images/plant.svg";

function Hero() {
  return (
    <main className="hero">
      <img
        className="left-plant"
        src={plant}
        alt=""
        aria-hidden="true"
      />

      <section className="hero-content">
        <h1>
          Find restaurants
          <br />
          that fit your
          <br />
          <span>lifestyle.</span>
        </h1>

        <p>
          Search nearby restaurants, compare nutrition information,
          and filter options by calories, cuisine, distance, and dietary needs.
        </p>

        <a className="explore-link" href="/explore">
          <Button className="explore-button">
            <span className="search-symbol">⌕</span>
            Explore Restaurants
          </Button>
        </a>
      </section>

      <section className="map-section">
        <img
          className="hero-map"
          src={heroMap}
          alt="Map showing nearby restaurants"
        />
      </section>

      <div className="bottom-images">
        <img className="lemonade" src={lemonade} alt="" />
        <img className="fruit-salad" src={fruitSalad} alt="" />
      </div>

      <img
        className="right-plant"
        src={plant}
        alt=""
        aria-hidden="true"
      />
    </main>
  );
}

export default Hero;