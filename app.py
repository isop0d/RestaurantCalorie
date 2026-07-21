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
from menu import fetch_and_cache_menu, search_restaurants
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

# React explore/map page
@app.route("/map")
@app.route("/explore")
def map_page():
    return send_from_directory("dist", "index.html")

# React map assets
@app.route("/assets/<path:filename>")
def map_assets(filename):
    return send_from_directory("dist/assets", filename)


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


if __name__ == "__main__":
    app.run(debug=True)