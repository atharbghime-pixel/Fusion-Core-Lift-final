"""
Fusion Core Lift - Smart Fitness Assistant
A simple Flask + SQLite web application that collects a user's basic
fitness profile and generates rule-based workout and diet recommendations.

Run with:
    python app.py
Then open:
    http://127.0.0.1:5000
"""

import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

# --------------------------------------------------------------------------
# APP SETUP
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = "fusion-core-lift-dev-secret"  # fine for a local college project


# --------------------------------------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------------------------------

def get_db_connection():
    """Open a connection to the SQLite database with sane defaults."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database file and tables if they do not already exist."""
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            height REAL NOT NULL,
            weight REAL NOT NULL,
            gender TEXT NOT NULL,
            goal TEXT NOT NULL,
            fitness_level TEXT NOT NULL,
            diet TEXT NOT NULL,
            injury TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_plan TEXT NOT NULL,
            diet_plan TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# VALIDATION
# --------------------------------------------------------------------------

VALID_GENDERS = {"Male", "Female", "Other"}
VALID_GOALS = {"Weight Loss", "Muscle Gain", "General Fitness"}
VALID_LEVELS = {"Beginner", "Intermediate", "Advanced"}
VALID_DIETS = {"Vegetarian", "Non-Vegetarian"}


def validate_registration(form):
    """
    Validate submitted registration data.
    Returns (cleaned_data, errors_list). If errors_list is non-empty,
    cleaned_data should not be trusted / used.
    """
    errors = []
    cleaned = {}

    # --- Name ---
    name = (form.get("name") or "").strip()
    if not name:
        errors.append("Please enter your name.")
    cleaned["name"] = name

    # --- Age ---
    age_raw = (form.get("age") or "").strip()
    try:
        age = int(age_raw)
        if age < 13 or age > 100:
            errors.append("Please enter a valid age between 13 and 100.")
    except ValueError:
        age = None
        errors.append("Please enter a valid age.")
    cleaned["age"] = age

    # --- Height ---
    height_raw = (form.get("height") or "").strip()
    try:
        height = float(height_raw)
        if height < 50 or height > 250:
            errors.append("Please enter a valid height between 50 and 250 cm.")
    except ValueError:
        height = None
        errors.append("Please enter a valid height.")
    cleaned["height"] = height

    # --- Weight ---
    weight_raw = (form.get("weight") or "").strip()
    try:
        weight = float(weight_raw)
        if weight < 20 or weight > 400:
            errors.append("Please enter a valid weight between 20 and 400 kg.")
    except ValueError:
        weight = None
        errors.append("Please enter a valid weight.")
    cleaned["weight"] = weight

    # --- Gender ---
    gender = (form.get("gender") or "").strip()
    if gender not in VALID_GENDERS:
        errors.append("Please select a valid gender.")
    cleaned["gender"] = gender

    # --- Goal ---
    goal = (form.get("goal") or "").strip()
    if goal not in VALID_GOALS:
        errors.append("Please select a fitness goal.")
    cleaned["goal"] = goal

    # --- Fitness level ---
    fitness_level = (form.get("fitness_level") or "").strip()
    if fitness_level not in VALID_LEVELS:
        errors.append("Please select a fitness level.")
    cleaned["fitness_level"] = fitness_level

    # --- Diet ---
    diet = (form.get("diet") or "").strip()
    if diet not in VALID_DIETS:
        errors.append("Please select a diet preference.")
    cleaned["diet"] = diet

    # --- Injury (optional) ---
    injury = (form.get("injury") or "").strip()
    if injury.lower() in ("", "none", "n/a", "na"):
        injury = ""
    cleaned["injury"] = injury

    return cleaned, errors


# --------------------------------------------------------------------------
# FITNESS CALCULATIONS
# --------------------------------------------------------------------------

def calculate_bmi(weight_kg, height_cm):
    height_m = height_cm / 100
    bmi = weight_kg / (height_m * height_m)
    return round(bmi, 1)


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obesity"


def calculate_bmr(weight_kg, height_cm, age, gender):
    if gender == "Male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    elif gender == "Female":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        # Neutral estimate for "Other": average of the male/female offsets
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 78


ACTIVITY_MULTIPLIERS = {
    "Beginner": 1.2,
    "Intermediate": 1.375,
    "Advanced": 1.55,
}

GOAL_CALORIE_ADJUSTMENT = {
    "Weight Loss": -300,
    "Muscle Gain": 300,
    "General Fitness": 0,
}


def calculate_calories(weight_kg, height_cm, age, gender, fitness_level, goal):
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    activity_multiplier = ACTIVITY_MULTIPLIERS.get(fitness_level, 1.2)
    calories = bmr * activity_multiplier
    calories += GOAL_CALORIE_ADJUSTMENT.get(goal, 0)
    return round(calories)


PROTEIN_PER_KG = {
    "Muscle Gain": 1.6,
    "Weight Loss": 1.4,
    "General Fitness": 1.2,
}


def calculate_protein(weight_kg, goal):
    factor = PROTEIN_PER_KG.get(goal, 1.2)
    return round(weight_kg * factor)


def calculate_water(weight_kg):
    return round(weight_kg * 0.035, 1)


SLEEP_RECOMMENDATION = "7-9 hours"


# --------------------------------------------------------------------------
# WORKOUT GENERATION (rule-based, no ML / no external API)
# --------------------------------------------------------------------------

WORKOUT_LIBRARY = {
    "Beginner": {
        "Weight Loss": ["Walking", "Bodyweight Squats", "Wall Push-ups", "Glute Bridges", "Plank", "Light Stretching"],
        "Muscle Gain": ["Bodyweight Squats", "Push-ups (modified if needed)", "Glute Bridges", "Lunges", "Plank"],
        "General Fitness": ["Walking", "Squats", "Push-ups", "Glute Bridges", "Plank", "Stretching"],
    },
    "Intermediate": {
        "Weight Loss": ["Brisk Walking / Jogging", "Squats", "Push-ups", "Lunges", "Plank", "Mountain Climbers"],
        "Muscle Gain": ["Squats", "Push-ups", "Lunges", "Dumbbell Rows (or backpack rows)", "Plank", "Glute Bridges"],
        "General Fitness": ["Jogging", "Squats", "Push-ups", "Lunges", "Plank", "Stretching"],
    },
    "Advanced": {
        "Weight Loss": ["Interval Running", "Jump Squats", "Push-ups", "Burpees", "Plank", "Mountain Climbers"],
        "Muscle Gain": ["Weighted Squats", "Push-ups / Dips", "Lunges", "Rows", "Plank", "Pull-ups (if available)"],
        "General Fitness": ["Running", "Squats", "Push-ups", "Lunges", "Plank", "Full Body Circuit"],
    },
}

# Weekly split by day (same shape for every user; content adapts to goal/level)
WEEKLY_STRUCTURE = [
    ("Monday", "Upper Body / Full Body"),
    ("Tuesday", "Walking / Cardio"),
    ("Wednesday", "Rest / Recovery"),
    ("Thursday", "Strength"),
    ("Friday", "Cardio"),
    ("Saturday", "Full Body"),
    ("Sunday", "Rest"),
]

# Keyword -> (exercises to avoid, alternative suggestions)
INJURY_RULES = {
    "knee": (
        ["jump", "squat", "lunge"],
        ["Walking (if comfortable)", "Upper-body movements", "Gentle mobility work"],
    ),
    "shoulder": (
        ["push-up", "push up", "overhead", "pull-up"],
        ["Lower-body movements", "Core work (plank, avoiding shoulder strain)", "Walking"],
    ),
    "back": (
        ["deadlift", "row", "burpee"],
        ["Walking", "Gentle core activation", "Stretching"],
    ),
    "wrist": (
        ["push-up", "push up"],
        ["Leg-focused exercises", "Walking", "Core work avoiding wrist load"],
    ),
    "ankle": (
        ["jump", "run", "jogging"],
        ["Seated or upper-body exercises", "Gentle stretching", "Swimming if accessible"],
    ),
}


def get_injury_warning_and_alternatives(injury_text):
    """
    Very simple keyword matching against the injury field.
    Returns (warning_message_or_None, list_of_alternatives, list_of_avoid_keywords)
    """
    if not injury_text:
        return None, [], []

    injury_lower = injury_text.lower()
    matched_avoid_keywords = []
    alternatives = []

    for keyword, (avoid_list, alt_list) in INJURY_RULES.items():
        if keyword in injury_lower:
            matched_avoid_keywords.extend(avoid_list)
            alternatives.extend(alt_list)

    if matched_avoid_keywords:
        warning = (
            f"You mentioned a limitation ('{injury_text}'). This app cannot "
            f"medically diagnose or clear you for exercise. Some exercises "
            f"that may aggravate this have been flagged below. Please "
            f"consult a qualified healthcare professional for advice "
            f"specific to your condition."
        )
    else:
        warning = (
            f"You mentioned a limitation ('{injury_text}'). Please exercise "
            f"caution and consult a qualified healthcare professional before "
            f"starting any new routine."
        )

    # de-duplicate while preserving order
    matched_avoid_keywords = list(dict.fromkeys(matched_avoid_keywords))
    alternatives = list(dict.fromkeys(alternatives))

    return warning, alternatives, matched_avoid_keywords


def filter_exercises_for_injury(exercises, avoid_keywords):
    """Remove exercises that contain any of the avoid keywords."""
    if not avoid_keywords:
        return exercises, []

    kept = []
    removed = []
    for ex in exercises:
        ex_lower = ex.lower()
        if any(k in ex_lower for k in avoid_keywords):
            removed.append(ex)
        else:
            kept.append(ex)
    return kept, removed


def generate_workout_plan(goal, fitness_level, injury_text):
    """
    Build a weekly workout plan (list of dicts: day, focus, exercises)
    plus any injury warning/alternatives.
    Returns a dict describing the full plan (used both for display and
    for storing a text summary in SQLite).
    """
    base_exercises = WORKOUT_LIBRARY.get(fitness_level, WORKOUT_LIBRARY["Beginner"]).get(
        goal, WORKOUT_LIBRARY["Beginner"]["General Fitness"]
    )

    warning, alternatives, avoid_keywords = get_injury_warning_and_alternatives(injury_text)
    safe_exercises, removed = filter_exercises_for_injury(base_exercises, avoid_keywords)

    # If filtering removed everything (unlikely), fall back to a safe minimal set
    if not safe_exercises:
        safe_exercises = ["Walking", "Gentle Stretching"]

    display_exercises = safe_exercises + alternatives

    weekly_plan = []
    for day, focus in WEEKLY_STRUCTURE:
        if focus == "Rest / Recovery" or focus == "Rest":
            weekly_plan.append({
                "day": day,
                "focus": focus,
                "exercises": [{"name": "Rest / Light Stretching", "sets": "-", "reps": "-", "notes": "Recovery day"}],
            })
        else:
            day_exercises = []
            for ex in display_exercises:
                if fitness_level == "Beginner":
                    sets, reps = "2-3", "10-12 reps (or 20-30 sec hold)"
                elif fitness_level == "Intermediate":
                    sets, reps = "3", "12-15 reps (or 30-45 sec hold)"
                else:
                    sets, reps = "3-4", "15-20 reps (or 45-60 sec hold)"
                day_exercises.append({"name": ex, "sets": sets, "reps": reps, "notes": ""})
            weekly_plan.append({"day": day, "focus": focus, "exercises": day_exercises})

    return {
        "goal": goal,
        "fitness_level": fitness_level,
        "weekly_plan": weekly_plan,
        "injury_warning": warning,
        "removed_exercises": removed,
        "alternatives": alternatives,
    }


def workout_plan_to_text(plan_dict):
    """Flatten the workout plan dict into a simple text summary for storage."""
    lines = [f"Goal: {plan_dict['goal']} | Level: {plan_dict['fitness_level']}"]
    if plan_dict.get("injury_warning"):
        lines.append(f"Injury note: {plan_dict['injury_warning']}")
    for day_info in plan_dict["weekly_plan"]:
        ex_names = ", ".join(e["name"] for e in day_info["exercises"])
        lines.append(f"{day_info['day']} ({day_info['focus']}): {ex_names}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# DIET GENERATION (rule-based, no external API)
# --------------------------------------------------------------------------

MEAL_LIBRARY = {
    "Vegetarian": {
        "Breakfast": ["Oats with milk and banana", "Vegetable poha", "Paneer sandwich"],
        "Lunch": ["Dal", "Rice / Roti", "Mixed vegetables", "Curd"],
        "Snack": ["Fruit", "Nuts", "Yogurt"],
        "Dinner": ["Paneer sabzi", "Roti", "Vegetables"],
    },
    "Non-Vegetarian": {
        "Breakfast": ["Eggs", "Oats", "Fruit"],
        "Lunch": ["Chicken curry", "Rice / Roti", "Vegetables"],
        "Snack": ["Yogurt", "Fruit", "Nuts"],
        "Dinner": ["Fish or Chicken", "Roti / Rice", "Vegetables"],
    },
}

GOAL_DIET_NOTES = {
    "Weight Loss": "Focus on balanced, portion-conscious meals with plenty of vegetables.",
    "Muscle Gain": "Include higher-protein options at each meal (extra dal/paneer/eggs/chicken).",
    "General Fitness": "Keep meals balanced across carbs, protein, and vegetables.",
}


def generate_diet_plan(goal, diet_preference):
    meals = MEAL_LIBRARY.get(diet_preference, MEAL_LIBRARY["Vegetarian"])
    note = GOAL_DIET_NOTES.get(goal, GOAL_DIET_NOTES["General Fitness"])

    plan = {
        "goal": goal,
        "diet_preference": diet_preference,
        "note": note,
        "meals": meals,
    }
    return plan


def diet_plan_to_text(plan_dict):
    lines = [f"Goal: {plan_dict['goal']} | Diet: {plan_dict['diet_preference']}", plan_dict["note"]]
    for meal_name, items in plan_dict["meals"].items():
        lines.append(f"{meal_name}: {', '.join(items)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# ROUTES - PAGES
# --------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET"])
def register_form():
    return render_template(
        "register.html",
        genders=sorted(VALID_GENDERS),
        goals=sorted(VALID_GOALS),
        levels=["Beginner", "Intermediate", "Advanced"],
        diets=sorted(VALID_DIETS),
        errors=[],
        form_data={},
    )


@app.route("/register", methods=["POST"])
def register_submit():
    cleaned, errors = validate_registration(request.form)

    if errors:
        return render_template(
            "register.html",
            genders=sorted(VALID_GENDERS),
            goals=sorted(VALID_GOALS),
            levels=["Beginner", "Intermediate", "Advanced"],
            diets=sorted(VALID_DIETS),
            errors=errors,
            form_data=cleaned,
        ), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO users (name, age, height, weight, gender, goal, fitness_level, diet, injury)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cleaned["name"], cleaned["age"], cleaned["height"], cleaned["weight"],
            cleaned["gender"], cleaned["goal"], cleaned["fitness_level"],
            cleaned["diet"], cleaned["injury"],
        ),
    )
    user_id = cursor.lastrowid

    # Generate plans right away and store them
    workout_plan = generate_workout_plan(cleaned["goal"], cleaned["fitness_level"], cleaned["injury"])
    diet_plan = generate_diet_plan(cleaned["goal"], cleaned["diet"])

    conn.execute(
        "INSERT INTO plans (user_id, workout_plan, diet_plan) VALUES (?, ?, ?)",
        (user_id, workout_plan_to_text(workout_plan), diet_plan_to_text(diet_plan)),
    )
    conn.commit()
    conn.close()

    flash("User registered successfully.", "success")
    return redirect(url_for("dashboard", user_id=user_id))


def get_user_or_none(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


@app.route("/dashboard/<int:user_id>")
def dashboard(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        flash("We couldn't find that user. Please register first.", "error")
        return redirect(url_for("register_form"))

    bmi = calculate_bmi(user["weight"], user["height"])
    category = bmi_category(bmi)
    calories = calculate_calories(
        user["weight"], user["height"], user["age"], user["gender"],
        user["fitness_level"], user["goal"],
    )
    protein = calculate_protein(user["weight"], user["goal"])
    water = calculate_water(user["weight"])

    return render_template(
        "dashboard.html",
        user=user,
        bmi=bmi,
        bmi_category=category,
        calories=calories,
        protein=protein,
        water=water,
        sleep=SLEEP_RECOMMENDATION,
    )


@app.route("/workout/<int:user_id>")
def workout(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        flash("We couldn't find that user. Please register first.", "error")
        return redirect(url_for("register_form"))

    plan = generate_workout_plan(user["goal"], user["fitness_level"], user["injury"])
    return render_template("workout.html", user=user, plan=plan)


@app.route("/diet/<int:user_id>")
def diet(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        flash("We couldn't find that user. Please register first.", "error")
        return redirect(url_for("register_form"))

    plan = generate_diet_plan(user["goal"], user["diet"])
    calories = calculate_calories(
        user["weight"], user["height"], user["age"], user["gender"],
        user["fitness_level"], user["goal"],
    )
    protein = calculate_protein(user["weight"], user["goal"])

    return render_template("diet.html", user=user, plan=plan, calories=calories, protein=protein)


# --------------------------------------------------------------------------
# ROUTES - SIMPLE API / UTILITY
# --------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/users")
def list_users():
    conn = get_db_connection()
    users = conn.execute("SELECT id, name, age, goal, fitness_level, diet, created_at FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route("/users/<int:user_id>")
def get_user_api(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user_api(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted", "user_id": user_id})


# --------------------------------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    message = "The page you're looking for doesn't exist. Please register first."
    return (
        "<html><head><title>Fusion Core Lift - Not Found</title></head>"
        "<body style='font-family: sans-serif; text-align:center; margin-top: 80px;'>"
        f"<h1>404</h1><p>{message}</p>"
        "<a href='/'>Go to Home</a></body></html>",
        404,
    )


# --------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    # host="0.0.0.0" makes the app reachable from other devices on the
    # same Wi-Fi/LAN (e.g. http://<this-machine-ip>:5000), not just
    # from this computer.
    app.run(debug=True, host="0.0.0.0", port=5000)
