"""Core budget planning logic and plotting utilities.

This module is shared between the CLI entrypoint and the Flask web UI.
"""
from __future__ import annotations

import argparse
import os
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CLI and web
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def fmt(x: float) -> str:
    return f"{x:,.2f}"


def find_university(df: pd.DataFrame, query: str) -> Optional[pd.Series]:
    if "University" not in df.columns:
        return None
    mask = df["University"].astype(str).str.contains(query, case=False, na=False)
    matches = df[mask]
    if matches.empty:
        return None
    return matches.iloc[0]


def safe_float(val) -> float:
    try:
        if pd.isna(val):
            return 0.0
        return float(val)
    except Exception:
        return 0.0


def compute_budget(row: pd.Series, ny_living: float) -> dict:
    """Compute per-year, program totals, and averages based on a CSV row and NY baseline."""
    duration = int(safe_float(row.get("Duration_Years", 1)) or 1)

    tuition_per_year = safe_float(row.get("Tuition_USD", 0.0))
    rent_month = safe_float(row.get("Rent_USD", 0.0))
    rent_annual = rent_month * 12.0
    insurance_annual = safe_float(row.get("Insurance_USD", 0.0))
    visa_fee = safe_float(row.get("Visa_Fee_USD", 0.0))

    living_index = safe_float(row.get("Living_Cost_Index", 100.0))
    living_multiplier = living_index / 100.0

    exchange_rate = safe_float(row.get("Exchange_Rate", 1.0))

    years = []
    total_usd_program = 0.0
    total_local_program = 0.0

    for y in range(1, duration + 1):
        year_tuition = tuition_per_year
        year_rent = rent_annual
        year_insurance = insurance_annual
        year_visa = visa_fee if y == 1 else 0.0

        direct_costs = year_tuition + year_rent + year_insurance + year_visa
        living = ny_living * living_multiplier

        year_total_usd = direct_costs + living
        year_total_local = year_total_usd * exchange_rate

        years.append(
            {
                "year": y,
                "tuition_usd": year_tuition,
                "rent_usd": year_rent,
                "insurance_usd": year_insurance,
                "visa_usd": year_visa,
                "direct_usd": direct_costs,
                "living_usd": living,
                "total_usd": year_total_usd,
                "total_local": year_total_local,
            }
        )

        total_usd_program += year_total_usd
        total_local_program += year_total_local

    avg_year_usd = total_usd_program / duration if duration > 0 else 0.0
    avg_month_usd = total_usd_program / (duration * 12.0) if duration > 0 else 0.0
    avg_year_local = total_local_program / duration if duration > 0 else 0.0
    avg_month_local = total_local_program / (duration * 12.0) if duration > 0 else 0.0

    return {
        "duration_years": duration,
        "living_multiplier": living_multiplier,
        "exchange_rate": exchange_rate,
        "ny_baseline": float(ny_living),
        "years": years,
        "program_total_usd": total_usd_program,
        "program_total_local": total_local_program,
        "avg_year_usd": avg_year_usd,
        "avg_month_usd": avg_month_usd,
        "avg_year_local": avg_year_local,
        "avg_month_local": avg_month_local,
    }


def _ensure_years_df(result: dict) -> pd.DataFrame:
    years_df = pd.DataFrame(result["years"])
    if years_df.empty:
        return years_df
    years_df = years_df.set_index("year")
    components = ["tuition_usd", "rent_usd", "insurance_usd", "visa_usd", "living_usd"]
    for c in components:
        if c not in years_df.columns:
            years_df[c] = 0.0
    return years_df


def generate_budget_plot(result: dict, title: str, output_path: str) -> None:
    """Generate stacked per-year cost chart (legacy helper for CLI)."""

    sns.set_style("whitegrid")
    years_df = _ensure_years_df(result)
    if years_df.empty:
        return

    components = ["tuition_usd", "rent_usd", "insurance_usd", "visa_usd", "living_usd"]

    plt.figure(figsize=(8, 5))
    bottom = None
    colors = sns.color_palette("tab10", n_colors=len(components))
    for i, comp in enumerate(components):
        label = comp.replace("_", " ").title()
        if bottom is None:
            plt.bar(years_df.index, years_df[comp], label=label, color=colors[i])
            bottom = years_df[comp].copy()
        else:
            plt.bar(years_df.index, years_df[comp], bottom=bottom, label=label, color=colors[i])
            bottom = bottom + years_df[comp]

    plt.xlabel("Year")
    plt.ylabel("Amount (USD)")
    plt.title(title)
    plt.legend(title="Component", fontsize=8)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=120)
    plt.close()


def generate_insight_charts(result: dict, output_dir: str, base_name: str = "budget") -> dict:
    """Generate multiple charts for richer insight.

    Returns dict with keys:
      - stacked: stacked bar of component costs per year (USD)
      - totals_line: line chart of total USD cost per year
      - components_share: bar chart of total program cost by component
    Paths returned are filenames (not full paths) so they can be used with url_for(static,...).
    """

    os.makedirs(output_dir, exist_ok=True)
    sns.set_style("whitegrid")
    years_df = _ensure_years_df(result)
    if years_df.empty:
        return {}

    components = ["tuition_usd", "rent_usd", "insurance_usd", "visa_usd", "living_usd"]
    filenames: dict[str, str] = {}

    # 1) Stacked bar components per year
    stacked_name = f"{base_name}_stacked.png"
    plt.figure(figsize=(7.5, 4.5))
    bottom = None
    colors = sns.color_palette("tab10", n_colors=len(components))
    for i, comp in enumerate(components):
        label = comp.replace("_", " ").title()
        if bottom is None:
            plt.bar(years_df.index, years_df[comp], label=label, color=colors[i])
            bottom = years_df[comp].copy()
        else:
            plt.bar(years_df.index, years_df[comp], bottom=bottom, label=label, color=colors[i])
            bottom = bottom + years_df[comp]
    plt.xlabel("Year")
    plt.ylabel("Amount (USD)")
    plt.title("Annual cost breakdown by component")
    plt.legend(title="Component", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, stacked_name), dpi=120)
    plt.close()
    filenames["stacked"] = stacked_name

    # 2) Total USD per year line chart
    totals_name = f"{base_name}_totals.png"
    plt.figure(figsize=(7.0, 3.8))
    plt.plot(years_df.index, years_df["total_usd"], marker="o", color="#38bdf8")
    plt.xlabel("Year")
    plt.ylabel("Total cost (USD)")
    plt.title("Total program cost per year (USD)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, totals_name), dpi=120)
    plt.close()
    filenames["totals_line"] = totals_name

    # 3) Component share across full program (sum per component)
    share_name = f"{base_name}_components.png"
    comp_totals = {c: float(years_df[c].sum()) for c in components}
    comp_labels = [c.replace("_", " ").title() for c in components]
    comp_values = [comp_totals[c] for c in components]

    plt.figure(figsize=(7.0, 3.8))
    bars = plt.bar(comp_labels, comp_values, color="#0ea5e9")
    plt.ylabel("Total over program (USD)")
    plt.title("Program cost composition by component")
    plt.xticks(rotation=15, ha="right")
    for b in bars:
        height = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, height, fmt(height), ha="center", va="bottom", fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, share_name), dpi=120)
    plt.close()
    filenames["components_share"] = share_name

    return filenames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--university", "-u", required=True, help="Name (or partial) of university")
    parser.add_argument(
        "--ny_living",
        type=float,
        required=True,
        help="Your baseline annual living cost in New York (USD)",
    )
    parser.add_argument(
        "--csv", default="International_Education_Costs.csv", help="CSV file name (default in workspace)"
    )
    parser.add_argument(
        "--plot", action="store_true", help="Show an interactive per-year stacked bar chart"
    )
    parser.add_argument(
        "--save-plot",
        metavar="FILE",
        help="Save per-year stacked bar chart to FILE (e.g. example_budget.png)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV file not found: {args.csv}")
        return

    df = pd.read_csv(args.csv)
    print(f"Loaded {len(df)} rows; columns: {list(df.columns)}")

    row = find_university(df, args.university)
    if row is None:
        print(f"No university match found for query: {args.university}")
        if "University" in df.columns:
            sample = df["University"].dropna().unique()[:20]
            print("Sample universities:")
            for s in sample:
                print(" -", s)
        return

    uni_name = str(row.get("University", "Unknown"))
    country = str(row.get("Country", ""))
    city = str(row.get("City", ""))

    print(f"Selected: {uni_name} ({city}, {country})")

    result = compute_budget(row, args.ny_living)

    print("\nPer-year breakdown (USD and local currency):")
    print(
        f"Living cost multiplier (NY baseline -> destination): {result['living_multiplier']:.3f}"
    )
    print(f"Exchange rate (local units per 1 USD): {result['exchange_rate']:.4f}\n")

    header = (
        f"{'Year':>4}  {'Tuition(USD)':>14}  {'Rent(USD)':>12}  "
        f"{'Insurance(USD)':>15}  {'Visa(USD)':>10}  {'Living(USD)':>12}  "
        f"{'Total(USD)':>12}  {'Total(Local)':>14}"
    )
    print(header)
    print("-" * len(header))
    for y in result["years"]:
        print(
            f"{y['year']:>4}  {fmt(y['tuition_usd']):>14}  {fmt(y['rent_usd']):>12}  "
            f"{fmt(y['insurance_usd']):>15}  {fmt(y['visa_usd']):>10}  {fmt(y['living_usd']):>12}  "
            f"{fmt(y['total_usd']):>12}  {fmt(y['total_local']):>14}"
        )

    print("\nProgram totals:")
    print(f"Total (USD)   : {fmt(result['program_total_usd'])}")
    print(f"Total (Local) : {fmt(result['program_total_local'])}")

    if args.plot or args.save_plot:
        out_path = args.save_plot or "_budget_plot.png"
        generate_budget_plot(result, f"Per-year cost breakdown — {uni_name}", out_path)
        print(f"Saved plot to {out_path}")


if __name__ == "__main__":
    main()
