import os
import sys

import pandas as pd
from flask import Flask, render_template, request


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from feature.budget_planning import (
    compute_budget,
    find_university,
    generate_insight_charts,
)

CSV_PATH = os.path.join(BASE_DIR, "International_Education_Costs.csv")
VIEWS_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(VIEWS_DIR, "static")
DEFAULT_NY_BASELINE = 26000.0
DEFAULT_INFLATION = 0.03  # 3% per year


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def index():
        return render_template("home.html")

    @app.route("/budget-planning", methods=["GET", "POST"], endpoint="budget_planning_view")
    def budget_planning_view():
        if not os.path.exists(CSV_PATH):
            return render_template("budget_planning.html", error="CSV file not found.")

        df = pd.read_csv(CSV_PATH)
        universities = sorted(df.get("University", pd.Series(dtype=str)).dropna().unique().tolist())

        result = None
        selected_university = None
        ny_living = None
        error = None
        charts = None
        inflation_rate = None
        inflation_percent = None

        if request.method == "POST":
            selected_university = request.form.get("university") or ""
            ny_living_raw = (request.form.get("ny_living") or "").strip()
            inflation_raw = (request.form.get("inflation") or "").strip()

            if ny_living_raw:
                try:
                    ny_living = float(ny_living_raw)
                    if ny_living < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    error = (
                        "Please enter a valid non-negative number for New York annual living cost "
                        "or leave it blank to use the default 26,000 USD/year."
                    )
            else:
                ny_living = DEFAULT_NY_BASELINE

            if not error:
                if inflation_raw:
                    try:
                        inflation_percent = float(inflation_raw)
                        if inflation_percent < 0:
                            raise ValueError
                        inflation_rate = inflation_percent / 100.0
                    except (TypeError, ValueError):
                        error = (
                            "Please enter a valid non-negative percentage for average cost-of-living "
                            "inflation or leave it blank to use the default 3% per year."
                        )
                else:
                    inflation_rate = DEFAULT_INFLATION
                    inflation_percent = DEFAULT_INFLATION * 100.0

            if not error:
                row = find_university(df, selected_university)
                if row is None:
                    error = "Selected university was not found in the dataset."
                else:
                    result = compute_budget(row, ny_living, inflation_rate=inflation_rate or 0.0)

                    charts = generate_insight_charts(result, STATIC_DIR, base_name="budget")

        return render_template(
            "budget_planning.html",
            universities=universities,
            selected_university=selected_university,
            ny_living=ny_living,
            inflation=inflation_percent,
            result=result,
            error=error,
            charts=charts,
        )

    @app.route("/policy-analysis")
    def policy_analysis():
        return render_template("policy_analysis.html")

    @app.route("/economic-research")
    def economic_research():
        return render_template("economic_research.html")

    @app.route("/university-benchmarking")
    def university_benchmarking():
        return render_template("university_benchmarking.html")

    return app
