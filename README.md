# Fusion Core Lift — Smart Fitness Assistant

A simple, local web application that collects a user's fitness profile and
generates personalized (rule-based) fitness metrics, a weekly workout plan,
and a diet plan.

## Features

- Profile registration form with server-side validation
- BMI calculation and category
- Estimated daily calories (Mifflin-St Jeor equation)
- Recommended daily protein and water intake
- General sleep recommendation
- Rule-based weekly workout plan, adjusted for injuries/limitations via keyword matching
- Rule-based diet plan based on goal and diet preference (vegetarian / non-vegetarian)
- Data persisted in SQLite (survives app restarts)
- Simple JSON API routes (`/health`, `/users`, `/users/<id>`)

## Technology Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite (via Python's built-in `sqlite3` module)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5 (via CDN)
- **Templating:** Jinja2 (built into Flask)

No React/Angular/Vue, no Node.js, no external databases, no paid APIs,
no machine learning — kept intentionally simple and reliable.

## Folder Structure

```
FusionCoreLift/
│
├── app.py                 # Flask app: routes, calculations, recommendation logic
├── requirements.txt       # Python dependencies (just Flask)
├── database.db             # SQLite database (created automatically on first run)
├── README.md
│
├── templates/
│   ├── base.html           # Shared layout (nav bar, flash messages, footer)
│   ├── index.html          # Landing page
│   ├── register.html       # Registration/profile form
│   ├── dashboard.html      # Metrics + links to workout/diet
│   ├── workout.html        # Weekly workout plan
│   └── diet.html           # Diet/meal plan
│
└── static/
    ├── style.css           # Custom styling
    └── script.js           # Minor UX polish (auto-dismiss alerts)
```

## Installation (Windows)

1. **Open the project folder in VS Code** (or a terminal) and navigate into it:
   ```
   cd FusionCoreLift
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   ```
   If `python` doesn't work, try:
   ```
   py -m venv venv
   ```

3. **Activate the virtual environment:**
   ```
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```
   python -m pip install -r requirements.txt
   ```
   or:
   ```
   py -m pip install -r requirements.txt
   ```

## How to Run

```
python app.py
```
or:
```
py app.py
```

Then open your browser to:

```
http://127.0.0.1:5000
```

The SQLite database (`database.db`) and its tables are created automatically
the first time the app starts — no manual database setup is required.

## How to Test

You do not need any special testing tools. Just use the app in the browser:

1. Go to `http://127.0.0.1:5000` — the home page should load.
2. Click **Get Started** — the registration form should load.
3. Fill in the form with the example test data below and submit.
4. You should be redirected to your **Dashboard**, showing your BMI, estimated
   calories, protein, water, and sleep recommendation.
5. Click **View Workout** — you should see a weekly workout plan.
6. Click **View Diet** — you should see a meal plan.
7. Restart the app (`Ctrl+C`, then `python app.py` again) and revisit your
   dashboard URL (e.g. `http://127.0.0.1:5000/dashboard/1`) — your data should
   still be there.

### Example Test Data

| Field          | Value        |
|----------------|--------------|
| Name           | Test User    |
| Age            | 20           |
| Height         | 170          |
| Weight         | 65           |
| Gender         | Male         |
| Goal           | Muscle Gain  |
| Fitness Level  | Beginner     |
| Diet           | Vegetarian   |
| Injury         | None         |

### Trying the Injury Logic

Register a second user and enter `knee pain` in the injury field. On their
Workout page you should see a warning message and squats/lunges/jumping
exercises replaced with safer alternatives.

### Trying Validation

On the registration form, try:
- Leaving Name empty → "Please enter your name."
- Age = `5` or `150` → "Please enter a valid age between 13 and 100."
- Height = `1000` → "Please enter a valid height between 50 and 250 cm."
- Weight = `1` → "Please enter a valid weight between 20 and 400 kg."
- Leaving a dropdown unselected → a message asking you to select it.

## Database Information

Two tables are created automatically in `database.db`:

- **users** — stores each registered profile (name, age, height, weight,
  gender, goal, fitness level, diet, injury).
- **plans** — stores a text summary of the generated workout and diet plan
  for each user, linked by `user_id` (foreign key, `ON DELETE CASCADE`).

Visiting the Dashboard/Workout/Diet pages recalculates and regenerates the
plan live from the user's saved profile (so it always reflects the latest
rule-based logic), while the `plans` table keeps a historical record of what
was generated at registration time.

## Notes / Disclaimer

All fitness metrics and recommendations are simple, transparent, rule-based
estimates for demonstration purposes only. They are **not** medical advice.
Anyone with an injury, medical condition, or health concern should consult a
qualified healthcare professional. This is stated in the app's footer and
(where relevant) directly on the workout/diet pages.

## Common Errors and Fixes

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Use `py` instead of `python` on Windows. |
| `ModuleNotFoundError: No module named 'flask'` | Make sure the virtual environment is activated, then re-run `pip install -r requirements.txt`. |
| Port already in use | Close other apps using port 5000, or run `app.run(debug=True, port=5001)` and open that port instead. |
| Dashboard shows "couldn't find that user" | The user ID in the URL doesn't exist yet — register a user first via `/register`. |
| Changes to templates/CSS not showing | Hard refresh the browser (Ctrl+F5); Flask's debug mode should auto-reload the server. |
