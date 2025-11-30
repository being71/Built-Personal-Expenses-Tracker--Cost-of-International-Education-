"""Budget planning helper for studying abroad.

Reads `International_Education_Costs.csv` in the workspace and computes per-year
and program totals in USD and converted local currency using `Exchange_Rate`.

Usage examples:
  py budget_planning.py --university Harvard --ny_living 24000
  py budget_planning.py --university "University of Oxford" --ny_living 20000

If multiple universities match the query the first match is used. The script
prints a per-year breakdown and the program total.
"""
from __future__ import annotations
import argparse
import os
import math
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt
import seaborn as sns


def fmt(x: float) -> str:
    return f"{x:,.2f}"


def find_university(df: pd.DataFrame, query: str) -> Optional[pd.Series]:
    if 'University' not in df.columns:
        return None
    mask = df['University'].astype(str).str.contains(query, case=False, na=False)
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
    # Interpret columns according to the user's definitions
    duration = int(safe_float(row.get('Duration_Years', 1)) or 1)

    # Per-user definitions: Tuition_USD = per-year tuition
    tuition_per_year = safe_float(row.get('Tuition_USD', 0.0))
    rent_month = safe_float(row.get('Rent_USD', 0.0))
    rent_annual = rent_month * 12.0
    insurance_annual = safe_float(row.get('Insurance_USD', 0.0))
    visa_fee = safe_float(row.get('Visa_Fee_USD', 0.0))

    # Living cost index baseline 100 == New York
    living_index = safe_float(row.get('Living_Cost_Index', 100.0))
    living_multiplier = living_index / 100.0

    exchange_rate = safe_float(row.get('Exchange_Rate', 1.0))

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

        years.append({
            'year': y,
            'tuition_usd': year_tuition,
            'rent_usd': year_rent,
            'insurance_usd': year_insurance,
            'visa_usd': year_visa,
            'direct_usd': direct_costs,
            'living_usd': living,
            'total_usd': year_total_usd,
            'total_local': year_total_local,
        })

        total_usd_program += year_total_usd
        total_local_program += year_total_local

    return {
        'duration_years': duration,
        'living_multiplier': living_multiplier,
        'exchange_rate': exchange_rate,
        'years': years,
        'program_total_usd': total_usd_program,
        'program_total_local': total_local_program,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--university', '-u', required=True, help='Name (or partial) of university')
    parser.add_argument('--ny_living', type=float, required=True, help='Your baseline annual living cost in New York (USD)')
    parser.add_argument('--csv', default='International_Education_Costs.csv', help='CSV file name (default in workspace)')
    parser.add_argument('--plot', action='store_true', help='Show an interactive per-year stacked bar chart')
    parser.add_argument('--save-plot', metavar='FILE', help='Save per-year stacked bar chart to FILE (e.g. example_budget.png)')
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV file not found: {args.csv}")
        return

    df = pd.read_csv(args.csv)
    print(f"Loaded {len(df)} rows; columns: {list(df.columns)}")

    row = find_university(df, args.university)
    if row is None:
        print(f"No university match found for query: {args.university}")
        # Show sample of universities to help user
        if 'University' in df.columns:
            sample = df['University'].dropna().unique()[:20]
            print('Sample universities:')
            for s in sample:
                print(' -', s)
        return

    uni_name = str(row.get('University', 'Unknown'))
    country = str(row.get('Country', ''))
    city = str(row.get('City', ''))

    print(f"Selected: {uni_name} ({city}, {country})")

    result = compute_budget(row, args.ny_living)

    print('\nPer-year breakdown (USD and local currency):')
    print(f"Living cost multiplier (NY baseline -> destination): {result['living_multiplier']:.3f}")
    print(f"Exchange rate (local units per 1 USD): {result['exchange_rate']:.4f}\n")

    header = f"{'Year':>4}  {'Tuition(USD)':>14}  {'Rent(USD)':>12}  {'Insurance(USD)':>15}  {'Visa(USD)':>10}  {'Living(USD)':>12}  {'Total(USD)':>12}  {'Total(Local)':>14}"
    print(header)
    print('-' * len(header))
    for y in result['years']:
        print(f"{y['year']:>4}  {fmt(y['tuition_usd']):>14}  {fmt(y['rent_usd']):>12}  {fmt(y['insurance_usd']):>15}  {fmt(y['visa_usd']):>10}  {fmt(y['living_usd']):>12}  {fmt(y['total_usd']):>12}  {fmt(y['total_local']):>14}")

    print('\nProgram totals:')
    print(f"Total (USD)   : {fmt(result['program_total_usd'])}")
    print(f"Total (Local) : {fmt(result['program_total_local'])}")

    # Visualization: stacked bar per year of components
    if args.plot or args.save_plot:
        sns.set_style('whitegrid')
        years_df = pd.DataFrame(result['years'])
        years_df = years_df.set_index('year')

        components = ['tuition_usd', 'rent_usd', 'insurance_usd', 'visa_usd', 'living_usd']
        # Ensure all components exist in dataframe
        for c in components:
            if c not in years_df.columns:
                years_df[c] = 0.0

        # Plot stacked bar
        plt.figure(figsize=(10,6))
        bottom = None
        colors = sns.color_palette('tab10', n_colors=len(components))
        for i, comp in enumerate(components):
            if bottom is None:
                p = plt.bar(years_df.index, years_df[comp], label=comp.replace('_',' ').title(), color=colors[i])
                bottom = years_df[comp].copy()
            else:
                p = plt.bar(years_df.index, years_df[comp], bottom=bottom, label=comp.replace('_',' ').title(), color=colors[i])
                bottom = bottom + years_df[comp]

        plt.xlabel('Year')
        plt.ylabel('Amount (USD)')
        plt.title(f'Per-year cost breakdown — {uni_name}')
        plt.legend(title='Component')
        plt.tight_layout()

        if args.save_plot:
            plt.savefig(args.save_plot)
            print(f"Saved plot to {args.save_plot}")
            plt.close()
        elif args.plot:
            try:
                plt.show()
            except Exception:
                # In headless envs, show() may fail — inform user
                print('Unable to show interactive plot in this environment. Use --save-plot to save to a file.')


if __name__ == '__main__':
    main()
