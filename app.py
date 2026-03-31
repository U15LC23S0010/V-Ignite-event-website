from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import json

# ---------------- APP CONFIG ----------------

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "vignite2026")

# ---------------- DATABASE CONFIG ----------------

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "vignite.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# prevents database connection drop
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

# ---------------- ADMIN PASSWORD ----------------

ADMIN_PASSWORDS = os.environ.get(
    "ADMIN_PASSWORDS",
    "admin123,vignite2026"
).split(",")

# ---------------- DATABASE MODELS ----------------

class Event(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)

    about = db.Column(db.Text, nullable=False)

    logo = db.Column(db.String(300))

    organizers = db.Column(db.Text)


class Team(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    team_name = db.Column(db.String(200))

    members = db.Column(db.Text)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("event.id")
    )

    event = db.relationship(
        "Event",
        backref="teams"
    )

# ---------------- CREATE DATABASE ----------------

with app.app_context():

    db.create_all()

    # Load JSON data only if database is empty
    if Event.query.count() == 0:

        try:

            if os.path.exists("events.json"):

                with open("events.json", "r", encoding="utf-8") as f:

                    data = json.load(f)

                for e in data.get("events", []):

                    org_list = [
                        f'{o["name"]} ({o["phone"]})'
                        for o in e.get("organizers", [])
                    ]

                    organizers_text = ", ".join(org_list)

                    event = Event(
                        name=e.get("name", ""),
                        about=e.get("about", ""),
                        logo=e.get("logo", ""),
                        organizers=organizers_text
                    )

                    db.session.add(event)

                    db.session.flush()

                    for t in e.get("teams", []):

                        members_text = ", ".join(
                            t.get("members", [])
                        )

                        team = Team(
                            team_name=t.get("team_name", ""),
                            members=members_text,
                            event_id=event.id
                        )

                        db.session.add(team)

                db.session.commit()

                print("Events loaded successfully")

        except Exception as ex:

            print("JSON Load Error:", ex)

# ---------------- ROUTES ----------------

@app.route("/")
def home():

    return render_template("home.html")


@app.route("/events")
def events():

    events = Event.query.all()

    return render_template(
        "index.html",
        events=events
    )


@app.route("/event/<int:id>")
def event_detail(id):

    event = db.session.get(Event, id)

    if not event:
        return "Event not found", 404

    return render_template(
        "event.html",
        event=event
    )

# ---------------- ADMIN LOGIN ----------------

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        password = request.form.get("password")

        if password in ADMIN_PASSWORDS:

            session["admin"] = True

            return redirect(url_for("admin_panel"))

        return render_template(
            "admin_login.html",
            error="Wrong Password"
        )

    return render_template("admin_login.html")

# ---------------- ADMIN PANEL ----------------

@app.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        new_event = Event(
            name=request.form["name"],
            about=request.form["about"],
            logo=request.form["logo"],
            organizers=request.form["organizers"]
        )

        db.session.add(new_event)

        db.session.commit()

        return redirect(url_for("admin_panel"))

    events = Event.query.all()

    return render_template(
        "admin_panel.html",
        events=events
    )

# ---------------- EDIT EVENT ----------------

@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_event(id):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    event = db.session.get(Event, id)

    if not event:
        return "Event not found", 404

    if request.method == "POST":

        event.name = request.form["name"]

        event.about = request.form["about"]

        event.logo = request.form["logo"]

        event.organizers = request.form["organizers"]

        db.session.commit()

        return redirect(url_for("admin_panel"))

    return render_template(
        "edit_event.html",
        event=event
    )

# ---------------- DELETE EVENT ----------------

@app.route("/admin/delete/<int:id>")
def delete_event(id):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    event = db.session.get(Event, id)

    if event:

        db.session.delete(event)

        db.session.commit()

    return redirect(url_for("admin_panel"))

# ---------------- DASHBOARD ----------------

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    total_events = Event.query.count()

    total_teams = Team.query.count()

    events = Event.query.all()

    total_members = sum(
        len([m for m in t.members.split(",") if m.strip()])
        for e in events
        for t in e.teams
        if t.members
    )

    return render_template(
        "dashboard.html",
        total_events=total_events,
        total_teams=total_teams,
        total_members=total_members,
        events=events
    )

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

# ---------------- RUN ----------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )