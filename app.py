from flask import (
    Flask,
    render_template,
    flash,
    redirect,
    session,
    request,
    jsonify,
    send_from_directory,
    url_for,
)
from forms import RegistrationForm, LogInForm
from dotenv import load_dotenv
from supabase import create_client
from menu import (
    fetch_and_cache_menu,
    fetch_menu_items,
    get_menu_with_estimates,
    get_restaurant_with_menu,
    search_restaurants,
    search_zip,
)
from gemini import estimate_calories
from concurrent.futures import ThreadPoolExecutor
import os


# Load values from the .env file
load_dotenv()

VITE_SUPABASE_URL = os.environ["VITE_SUPABASE_URL"]
VITE_SUPABASE_ANON_KEY = os.environ["VITE_SUPABASE_ANON_KEY"]

supabase = create_client(
    VITE_SUPABASE_URL,
    VITE_SUPABASE_ANON_KEY,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["VITE_SECRET_KEY"]


# Public homepage
@app.route("/")
@app.route("/home")
def start():
    return render_template(
        "home.html",
        username=session.get("username"),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        check_user = (
            supabase.table("Users")
            .select("*")
            .eq("username", form.username.data)
            .execute()
        )

        check_email = (
            supabase.table("Users")
            .select("*")
            .eq("email", form.email.data)
            .execute()
        )

        if check_user.data:
            flash(
                "Username already taken, please try again",
                "danger",
            )
            return render_template(
                "register.html",
                form=form,
            )

        if check_email.data:
            flash(
                "Email already in use, please try again",
                "danger",
            )
            return render_template(
                "register.html",
                form=form,
            )

        supabase.table("Users").insert(
            {
                "username": form.username.data,
                "email": form.email.data,
                "password": form.password.data,
            }
        ).execute()

        flash(
            f"Account created for {form.username.data}!",
            "success",
        )

        return redirect(url_for("login"))

    return render_template(
        "register.html",
        title="Register",
        form=form,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LogInForm()

    if form.validate_on_submit():
        response = (
            supabase.table("Users")
            .select("*")
            .eq("username", form.username.data)
            .execute()
        )

        if response.data:
            user = response.data[0]

            if user["password"] == form.password.data:
                session["username"] = form.username.data
                return redirect(url_for("start"))

        flash(
            "Incorrect login information, please try again!",
            "danger",
        )

    return render_template(
        "login.html",
        title="Login",
        form=form,
    )


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("start"))


@app.route("/index")
def index():
    return render_template("index.html")

# React explore/map/restaurant pages (all served by the same built SPA)
@app.route("/map")
@app.route("/explore")
@app.route("/restaurant")
def map_page():
    return send_from_directory("dist", "index.html")

# React map assets
@app.route("/assets/<path:filename>")
def map_assets(filename):
    return send_from_directory("dist/assets", filename)

# Root-level static file from the Vite build (e.g. the favicon).
@app.route("/favicon.svg")
def favicon():
    return send_from_directory("dist", "favicon.svg")


@app.route("/api/search", methods=["POST"])
def api_search():
    body = request.get_json(silent=True) or {}

    try:
        results = search_restaurants(
            postal_code=body.get("postal_code"),
            city=body.get("city"),
            state=body.get("state"),
            country=body.get("country", "US"),
            name=body.get("name"),
        )

    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    return jsonify(
        {
            "restaurants": results,
            "count": len(results),
        }
    )


@app.route("/api/fetch-menu", methods=["POST"])
def api_fetch_menu():
    body = request.get_json(silent=True) or {}

    try:
        result = fetch_and_cache_menu(
            body.get("openmenu_id")
        )

    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    return jsonify(result)


@app.route("/api/search-with-menus", methods=["POST"])
def api_search_with_menus():
    """The MVP loop: search a location, then for the first `limit` restaurants
    pull each menu and get Gemini calorie estimates. No caching yet, so every
    call spends OpenMenu credits (1 search + 1 per restaurant menu)."""
    body = request.get_json(silent=True) or {}
    limit = body.get("limit", 3)

    try:
        restaurants = search_restaurants(
            postal_code=body.get("postal_code"),
            city=body.get("city"),
            state=body.get("state"),
            country=body.get("country", "US"),
            name=body.get("name"),
        )

    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    results = []
    for restaurant in restaurants[:limit]:
        try:
            items = fetch_menu_items(restaurant["openmenu_id"])
            estimates = estimate_calories(items)
            results.append({"restaurant": restaurant, "items": estimates})

        except Exception as err:  # one bad restaurant shouldn't kill the search
            results.append(
                {"restaurant": restaurant, "items": [], "error": str(err)}
            )

    return jsonify(
        {
            "restaurants": results,
            "count": len(results),
        }
    )


@app.route("/api/explore-search", methods=["POST"])
def api_explore_search():
    """Search feature endpoint for the /explore page. Like search-with-menus,
    but it KEEPS each item's dietary_tags (and the restaurant's lat/lng) so the
    front end can filter by calories, dietary restrictions, and distance.
    Additive: does not change the existing search endpoints."""
    body = request.get_json(silent=True) or {}
    limit = body.get("limit", 3)

    try:
        restaurants = search_restaurants(
            postal_code=body.get("postal_code"),
            city=body.get("city"),
            state=body.get("state"),
            country=body.get("country", "US"),
            name=body.get("name"),
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    # Look up each restaurant's menu concurrently. get_menu_with_estimates uses
    # Supabase as a cache: cold restaurants hit OpenMenu + Gemini once and are
    # written back; warm ones return from the DB. Running the lookups in parallel
    # keeps the cold path (up to `limit` restaurants) from stacking sequentially.
    def lookup(restaurant):
        try:
            items = get_menu_with_estimates(restaurant["openmenu_id"])
            return {"restaurant": restaurant, "items": items}
        except Exception as err:  # one bad restaurant shouldn't kill the search
            return {"restaurant": restaurant, "items": [], "error": str(err)}

    with ThreadPoolExecutor(max_workers=max(limit, 1)) as executor:
        results = list(executor.map(lookup, restaurants[:limit]))

    return jsonify({"restaurants": results, "count": len(results)})


@app.route("/api/search-zip", methods=["POST"])
def api_search_zip():
    """Fast restaurant search by zip, cached in Supabase. Returns just the
    restaurant list (no menus) so search stays quick — menus load when a
    restaurant is opened. `limit` controls how many of the cached list to return,
    so raising it "searches for more restaurants" without re-hitting OpenMenu."""
    body = request.get_json(silent=True) or {}
    limit = body.get("limit", 3)

    try:
        restaurants = search_zip(body.get("postal_code"), body.get("country", "US"))
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    return jsonify(
        {
            "restaurants": restaurants[:limit],
            "count": len(restaurants[:limit]),
            "total_available": len(restaurants),
        }
    )


@app.route("/api/restaurant", methods=["POST"])
def api_restaurant():
    """Restaurant detail: menu + calorie estimates for one restaurant, fetched on
    demand (when opened) and cached. This is where the OpenMenu + Gemini cost is
    paid — once per restaurant a user actually clicks, not during search."""
    body = request.get_json(silent=True) or {}

    try:
        data = get_restaurant_with_menu(body.get("openmenu_id"))
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except RuntimeError as err:
        return jsonify({"error": str(err)}), 502

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)