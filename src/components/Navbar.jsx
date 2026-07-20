import leaf from "../assets/images/leaf.svg";

function Navbar() {
  return (
    <header className="navbar">
      <a className="logo" href="/">
        <img src={leaf} alt="" />
        <span>
          Nutri<span>Map</span>
        </span>
      </a>

      <nav className="nav-links">
        <a className="active" href="/">Home</a>
        <a href="/explore">Explore Restaurants</a>
      </nav>

      <div className="account-links">
        <a
          className="login-button"
          href="http://localhost:5000/login"
        >
          Log In
        </a>

        <a
          className="signup-button"
          href="http://localhost:5000/register"
        >
          Sign Up
        </a>
      </div>
    </header>
  );
}

export default Navbar;