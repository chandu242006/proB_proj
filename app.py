"""
=============================================================
  Tennis Player Endurance & Winning Probability Model
  Flask Web Application
=============================================================
  Converts the original CLI Python program into a web app.
  All formulas are unchanged — only the interface is new.
=============================================================
"""

import math
import os
from flask import Flask, render_template, request, jsonify

# ── Flask app setup ──────────────────────────────────────────
app = Flask(__name__)


# ──────────────────────────────────────────────────────────────
#  FORMULA FUNCTIONS  (identical to original — no changes)
# ──────────────────────────────────────────────────────────────

def geometric_probability(p, k):
    """
    Formula: P(X = k) = (1 - p)^(k-1) * p
    Probability that a player wins exactly on the k-th attempt.
    """
    return ((1 - p) ** (k - 1)) * p


def expected_attempts(p):
    """
    Formula: E(X) = 1 / p
    Average number of attempts needed to win one point.
    """
    return 1 / p


def exponential_pdf(lam, x):
    """
    Formula: f(x) = lambda * e^(-lambda * x)
    Endurance density — how fast the player's energy drops at time x.
    """
    return lam * math.exp(-lam * x)


def expected_endurance(lam):
    """
    Formula: E(X) = 1 / lambda
    Average minutes a player can sustain peak energy.
    """
    return 1 / lam


def winning_probability_at_time(p0, lam, t):
    """
    Formula: p(t) = p0 * e^(-lambda * t)
    Combined model — winning probability decays with fatigue over time.
    """
    return p0 * math.exp(-lam * t)


# ──────────────────────────────────────────────────────────────
#  COMPUTATION  — builds a structured result dict for the template
# ──────────────────────────────────────────────────────────────

def run_model(p0, lam, k, match_duration, interval):
    """
    Run all four sections of the model and return a dict of results.
    Mirrors the original run_model() output, structured for HTML display.
    """
    results = {}

    # ── Section 1: Geometric Distribution ─────────────────────
    p_xk = geometric_probability(p0, k)
    ex   = expected_attempts(p0)

    results["geo"] = {
        "formula":      "P(X = k) = (1 - p)^(k-1) × p",
        "p":            p0,
        "k":            k,
        "step1_base":   round(1 - p0, 6),
        "step1_exp":    k - 1,
        "step1_result": round((1 - p0) ** (k - 1), 6),
        "p_xk":         round(p_xk, 6),
        "p_xk_pct":     round(p_xk * 100, 4),
        "expected_formula": f"E(X) = 1 / {p0} = {round(ex, 4)}",
        "ex":           round(ex, 4),
    }

    # ── Section 2: Exponential Distribution ───────────────────
    avg_endurance = expected_endurance(lam)

    exp_rows = []
    for t in range(0, match_duration + 1, interval):
        fx = exponential_pdf(lam, t)
        bar_width = min(int(fx * 300), 200)
        exp_rows.append({
            "t":    t,
            "fx":   round(fx, 6),
            "bar":  bar_width,
        })

    results["exp"] = {
        "formula":        "f(x) = λ × e^(−λx)",
        "lam":            lam,
        "avg_endurance":  round(avg_endurance, 4),
        "rows":           exp_rows,
    }

    # ── Section 3: Combined Model ──────────────────────────────
    combined_rows = []
    for t in range(0, match_duration + 1, interval):
        pt = winning_probability_at_time(p0, lam, t)

        if t <= match_duration * 0.25:
            stage = "Early"
            stage_class = "stage-early"
        elif t <= match_duration * 0.75:
            stage = "Middle"
            stage_class = "stage-middle"
        else:
            stage = "Late"
            stage_class = "stage-late"

        bar_width = min(int(pt * 200), 200)
        combined_rows.append({
            "t":           t,
            "pt":          round(pt, 6),
            "pt_pct":      round(pt * 100, 2),
            "stage":       stage,
            "stage_class": stage_class,
            "bar":         bar_width,
        })

    results["combined"] = {
        "formula": "p(t) = p0 × e^(−λ × t)",
        "p0":      p0,
        "lam":     lam,
        "rows":    combined_rows,
    }

    # ── Section 4: Stage-wise Summary ─────────────────────────
    early_t = 0
    mid_t   = int(match_duration * 0.5)
    late_t  = match_duration

    p_early = winning_probability_at_time(p0, lam, early_t)
    p_mid   = winning_probability_at_time(p0, lam, mid_t)
    p_late  = winning_probability_at_time(p0, lam, late_t)

    drop_pct = ((p_early - p_late) / p_early) * 100 if p_early > 0 else 0

    results["summary"] = {
        "early_t":     early_t,
        "mid_t":       mid_t,
        "late_t":      late_t,
        "p_early":     round(p_early, 4),
        "p_mid":       round(p_mid, 4),
        "p_late":      round(p_late, 4),
        "p_early_pct": round(p_early * 100, 2),
        "p_mid_pct":   round(p_mid   * 100, 2),
        "p_late_pct":  round(p_late  * 100, 2),
        "drop_pct":    round(drop_pct, 2),
    }

    return results


# ──────────────────────────────────────────────────────────────
#  ROUTES
# ──────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    """Render the main simulator page (empty form)."""
    return render_template("index.html", results=None, error=None, inputs=None)


@app.route("/simulate", methods=["POST"])
def simulate():
    """
    Handle form submission:
    1. Parse and validate inputs.
    2. Run the model.
    3. Re-render the page with results.
    """
    error   = None
    results = None
    inputs  = {}

    try:
        # ── Parse inputs from the HTML form ───────────────────
        p0             = float(request.form["p0"])
        lam            = float(request.form["lam"])
        k              = int(request.form["k"])
        match_duration = int(request.form["match_duration"])
        interval       = int(request.form["interval"])

        # Keep a copy to repopulate the form after submission
        inputs = {
            "p0":             p0,
            "lam":            lam,
            "k":              k,
            "match_duration": match_duration,
            "interval":       interval,
        }

        # ── Validation (same rules as the original script) ────
        if not (0 < p0 < 1):
            raise ValueError("Initial winning probability p must be between 0 and 1 (exclusive).")
        if lam <= 0:
            raise ValueError("Fatigue rate λ must be greater than 0.")
        if k < 1:
            raise ValueError("Attempt number k must be at least 1.")
        if match_duration <= 0:
            raise ValueError("Match duration must be a positive integer.")
        if interval <= 0:
            raise ValueError("Time interval must be a positive integer.")
        if interval > match_duration:
            raise ValueError("Time interval cannot be larger than the match duration.")

        # ── Run the model ──────────────────────────────────────
        results = run_model(p0, lam, k, match_duration, interval)

    except ValueError as e:
        error = str(e)
    except ZeroDivisionError:
        error = "p and λ cannot be zero — division by zero."

    return render_template("index.html", results=results, error=error, inputs=inputs)


# ──────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Read PORT from environment (Replit sets this automatically)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)