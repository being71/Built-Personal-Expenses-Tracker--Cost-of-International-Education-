"""Policy-focused affordability analysis utilities.

This module is intended for educational policymakers and NGOs to analyse
how affordable different international education options are and to
identify where additional support or subsidies may be needed.
"""

from __future__ import annotations

import os
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from feature.budget_planning import safe_float


def build_policy_frame(df: pd.DataFrame, ny_living: float) -> pd.DataFrame:
    """Return a per-program DataFrame with cost components and indices.

    The frame contains, for each program:
    - direct_annual_usd: tuition + annualised rent + insurance + visa amortised
    - indirect_annual_usd: living cost derived from NY baseline and index
    - total_annual_usd: sum of direct and indirect costs
    - affordability_index: 0–100, higher means more affordable (cheaper)
    - policy_gap_usd: deviation from median cost for the same study level
    """

    records = []

    for _, row in df.iterrows():
        duration = int(safe_float(row.get("Duration_Years", 1)) or 1)
        tuition = safe_float(row.get("Tuition_USD", 0.0))
        rent_month = safe_float(row.get("Rent_USD", 0.0))
        insurance = safe_float(row.get("Insurance_USD", 0.0))
        visa_fee = safe_float(row.get("Visa_Fee_USD", 0.0))
        living_index = safe_float(row.get("Living_Cost_Index", 100.0))
        exchange_rate = safe_float(row.get("Exchange_Rate", 1.0))

        direct_annual = tuition + rent_month * 12.0 + insurance + visa_fee / max(duration, 1)
        indirect_annual = ny_living * (living_index / 100.0)
        total_annual = direct_annual + indirect_annual

        records.append(
            {
                "Country": row.get("Country"),
                "City": row.get("City"),
                "University": row.get("University"),
                "Program": row.get("Program"),
                "Level": row.get("Level"),
                "Duration_Years": duration,
                "Tuition_USD": tuition,
                "Rent_USD": rent_month,
                "Insurance_USD": insurance,
                "Visa_Fee_USD": visa_fee,
                "Living_Cost_Index": living_index,
                "Exchange_Rate": exchange_rate,
                "direct_annual_usd": direct_annual,
                "indirect_annual_usd": indirect_annual,
                "total_annual_usd": total_annual,
            }
        )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    min_total = float(frame["total_annual_usd"].min())
    max_total = float(frame["total_annual_usd"].max())
    if max_total > min_total:
        frame["affordability_index"] = 100.0 * (max_total - frame["total_annual_usd"]) / (max_total - min_total)
    else:
        frame["affordability_index"] = 50.0

    level_median = frame.groupby("Level")["total_annual_usd"].transform("median")
    frame["policy_gap_usd"] = frame["total_annual_usd"] - level_median

    return frame


def summarize_policy_insights(frame: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Construct core tables for policy work.

    Returns a dict with four tables:
    - total_annual: per-program total annual cost with key descriptors
    - affordability: programs ranked by affordability_index
    - policy_gap: average gaps by country and level
    - comparative: comparative statistics by country
    """

    if frame.empty:
        empty = frame.copy()
        return {
            "total_annual": empty,
            "affordability": empty,
            "policy_gap": empty,
            "comparative": empty,
        }

    cols_base = [
        "Country",
        "City",
        "University",
        "Program",
        "Level",
        "Duration_Years",
        "direct_annual_usd",
        "indirect_annual_usd",
        "total_annual_usd",
        "affordability_index",
        "policy_gap_usd",
    ]

    total_annual = frame[cols_base].sort_values("total_annual_usd")
    affordability = frame[cols_base].sort_values("affordability_index", ascending=False)

    policy_gap = (
        frame.assign(above_median=frame["policy_gap_usd"] > 0)
        .groupby(["Country", "Level"], as_index=False)
        .agg(
            avg_total_annual_usd=("total_annual_usd", "mean"),
            avg_affordability_index=("affordability_index", "mean"),
            share_above_median=("above_median", "mean"),
        )
    )

    comparative = (
        frame.groupby("Country", as_index=False)["total_annual_usd"]
        .agg(
            min_total_annual_usd="min",
            max_total_annual_usd="max",
            mean_total_annual_usd="mean",
        )
        .sort_values("mean_total_annual_usd")
    )

    return {
        "total_annual": total_annual,
        "affordability": affordability,
        "policy_gap": policy_gap,
        "comparative": comparative,
    }


def generate_policy_charts(frame: pd.DataFrame, output_dir: str, base_name: str = "policy") -> Dict[str, str]:
    """Generate graphs for direct vs indirect cost, economic context, and program structure.

    Returns dict mapping semantic chart names to filenames (PNG) stored in output_dir.
    """

    os.makedirs(output_dir, exist_ok=True)
    if frame.empty:
        return {}

    sns.set_style("whitegrid")
    filenames: Dict[str, str] = {}

    top = frame.sort_values("total_annual_usd", ascending=False).head(10).copy()
    top["label"] = top["University"].astype(str) + " (" + top["Country"].astype(str) + ")"

    # 1) Direct vs indirect (living) annual cost components
    # Left: annual total cost split into policy-defined direct vs living-related costs
    # Right: share of direct vs living costs (composition) for the same programmes
    cost_file = f"{base_name}_cost_components.png"
    if not top.empty:
        duration = top["Duration_Years"].replace(0, 1)
        tuition = top["Tuition_USD"]
        insurance = top["Insurance_USD"]
        visa_fee = top["Visa_Fee_USD"]
        rent_month = top["Rent_USD"]
        living_annual = top["indirect_annual_usd"]

        policy_direct = tuition + insurance + visa_fee / duration
        policy_indirect = rent_month * 12.0 + living_annual
        policy_total = policy_direct + policy_indirect

        top["policy_direct_annual_usd"] = policy_direct
        top["policy_indirect_annual_usd"] = policy_indirect

        denom = policy_total.replace(0, 1e-9)
        top["policy_direct_share"] = policy_direct / denom
        top["policy_indirect_share"] = policy_indirect / denom

        y_pos = range(len(top))
        fig_height = max(4.5, 0.4 * len(top) + 2.0)
        fig, (ax_abs, ax_share) = plt.subplots(1, 2, figsize=(11, fig_height), sharey=True)

        # Absolute stacked annual cost (policy-defined direct vs living)
        ax_abs.barh(y_pos, top["policy_direct_annual_usd"], color="#0ea5e9", label="Direct costs (tuition, visa, insurance)")
        ax_abs.barh(
            y_pos,
            top["policy_indirect_annual_usd"],
            left=top["policy_direct_annual_usd"],
            color="#fb923c",
            label="Living-related costs (rent + cost-of-living)",
        )
        ax_abs.set_yticks(list(y_pos))
        ax_abs.set_yticklabels(top["label"])
        ax_abs.invert_yaxis()
        ax_abs.set_xlabel("Annual cost (USD)")
        ax_abs.set_title("Total annual cost (top programmes)")
        ax_abs.legend(fontsize=8)

        # Composition: direct vs living shares (100% stacked)
        ax_share.barh(y_pos, top["policy_direct_share"], color="#0ea5e9", label="Direct share")
        ax_share.barh(
            y_pos,
            top["policy_indirect_share"],
            left=top["policy_direct_share"],
            color="#fb923c",
            label="Living share",
        )
        ax_share.set_yticks(list(y_pos))
        ax_share.set_yticklabels([])
        ax_share.invert_yaxis()
        ax_share.set_xlabel("Share of total annual cost")
        ax_share.set_xlim(0, 1)
        ax_share.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax_share.set_title("Composition: direct vs living")

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, cost_file), dpi=120)
        plt.close(fig)
        filenames["cost_components"] = cost_file

    # 2) Economic context: living-cost index by country, coloured by affordability
    eco_file = f"{base_name}_economic_context.png"
    eco = (
        frame.dropna(subset=["Country"])
        .groupby("Country", as_index=False)
        .agg(
            living_index=("Living_Cost_Index", "mean"),
            affordability=("affordability_index", "mean"),
        )
        .sort_values("living_index")
    )

    if not eco.empty:
        fig_height = max(4.5, 0.35 * len(eco) + 2.0)
        y_pos = range(len(eco))

        norm = matplotlib.colors.Normalize(
            vmin=float(eco["affordability"].min()),
            vmax=float(eco["affordability"].max()),
        )
        # Green = more affordable (higher index), red = less affordable
        cmap = plt.cm.get_cmap("RdYlGn")
        colors = cmap(norm(eco["affordability"].values))

        fig, ax = plt.subplots(figsize=(9, fig_height))
        ax.barh(y_pos, eco["living_index"], color=colors)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(eco["Country"])
        ax.invert_yaxis()
        ax.set_xlabel("Living cost index (avg)")
        ax.set_title("Living cost index by country (colour = affordability)")

        mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
        mappable.set_array([])
        cbar = fig.colorbar(
            mappable,
            ax=ax,
            fraction=0.046,
            pad=0.04,
        )
        cbar.set_label("Affordability index (higher = more affordable)")

        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, eco_file), dpi=120)
        plt.close(fig)
        filenames["economic_context"] = eco_file

    # 3) Institutional & programme variables: level, duration, and cost efficiency
    inst_file = f"{base_name}_institution_program.png"

    # Cost per year metric for efficiency (used in multiple panels)
    duration_all = frame["Duration_Years"].replace(0, 1)
    frame = frame.assign(cost_per_year_usd=frame["total_annual_usd"] / duration_all)

    # Prepare aggregates for duration vs cost (median per level/duration)
    dur_curve = (
        frame.groupby(["Duration_Years", "Level"], as_index=False)["total_annual_usd"]
        .median()
        .rename(columns={"total_annual_usd": "median_total_annual_usd"})
        .sort_values(["Duration_Years", "Level"])
    )

    # Prepare cost-per-year ranking (top 15 most expensive per year)
    eff = frame.sort_values("cost_per_year_usd", ascending=False).head(15).copy()
    eff["eff_label"] = eff["Program"].astype(str) + " (" + eff["Country"].astype(str) + ")"

    levels = list(frame["Level"].dropna().unique())
    levels.sort()

    # Layout: 2 rows x 3 columns
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))

    # A. Boxplot: annual cost distribution per level
    ax_box = axes[0, 0]
    sns.boxplot(
        data=frame,
        x="Level",
        y="total_annual_usd",
        ax=ax_box,
        palette="tab10",
    )
    ax_box.set_ylabel("Annual cost (USD)")
    ax_box.set_title("Annual cost by level")
    ax_box.tick_params(axis="x", rotation=20)

    # B. Duration vs median annual cost (per level)
    ax_line = axes[0, 1]
    if not dur_curve.empty:
        for lvl in levels:
            sub = dur_curve[dur_curve["Level"] == lvl]
            if sub.empty:
                continue
            ax_line.plot(
                sub["Duration_Years"],
                sub["median_total_annual_usd"],
                marker="o",
                label=str(lvl),
            )
    ax_line.set_xlabel("Duration (years)")
    ax_line.set_ylabel("Median annual cost (USD)")
    ax_line.set_title("Duration vs annual cost (median by level)")
    if levels:
        ax_line.legend(title="Level", fontsize=8)

    # D. Cost efficiency: cost per year ranking (top programmes)
    ax_eff = axes[0, 2]
    if not eff.empty:
        idx_eff = range(len(eff))
        ax_eff.barh(idx_eff, eff["cost_per_year_usd"], color="#0f766e")
        ax_eff.set_yticks(list(idx_eff))
        ax_eff.set_yticklabels(eff["eff_label"], fontsize=7)
        ax_eff.invert_yaxis()
        ax_eff.set_xlabel("Cost per year (USD)")
        ax_eff.set_title("Cost per year (top programmes)")

    # C. Small multiples: top programmes by total cost within each level
    for i in range(3):
        ax = axes[1, i]
        if i >= len(levels):
            ax.axis("off")
            continue
        lvl = levels[i]
        sub = frame[frame["Level"] == lvl].sort_values("total_annual_usd", ascending=False).head(8).copy()
        if sub.empty:
            ax.axis("off")
            continue
        sub["label"] = sub["Program"].astype(str).str.slice(0, 18) + " (" + sub["Country"].astype(str) + ")"
        idx = range(len(sub))
        ax.barh(idx, sub["total_annual_usd"], color="#2563eb")
        ax.set_yticks(list(idx))
        ax.set_yticklabels(sub["label"], fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Annual cost (USD)")
        ax.set_title(str(lvl))

    fig.suptitle("Costs by level, duration, and programme structure", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(os.path.join(output_dir, inst_file), dpi=120)
    plt.close(fig)
    filenames["institution_program"] = inst_file

    return filenames


def apply_policy_scenario(
    frame: pd.DataFrame,
    tuition_cut: float = 0.0,
    living_subsidy: float = 0.0,
) -> pd.DataFrame:
    """Apply simple policy levers to derive a scenario frame.

    tuition_cut and living_subsidy are expressed as decimals (e.g. 0.2 = 20%).
    The function recalculates annual totals under the scenario and returns
    a copy of ``frame`` with extra ``scenario_*`` columns.
    """

    if frame.empty:
        return frame.copy()

    try:
        tuition_cut = max(0.0, min(1.0, float(tuition_cut or 0.0)))
    except Exception:
        tuition_cut = 0.0

    try:
        living_subsidy = max(0.0, min(1.0, float(living_subsidy or 0.0)))
    except Exception:
        living_subsidy = 0.0

    scen = frame.copy()

    duration = scen["Duration_Years"].replace(0, 1)
    tuition = scen["Tuition_USD"]
    rent_month = scen["Rent_USD"]
    insurance = scen["Insurance_USD"]
    visa_fee = scen["Visa_Fee_USD"]
    indirect = scen["indirect_annual_usd"]

    tuition_after = tuition * (1.0 - tuition_cut)
    direct_after = tuition_after + rent_month * 12.0 + insurance + visa_fee / duration
    indirect_after = indirect * (1.0 - living_subsidy)
    total_after = direct_after + indirect_after

    scen["scenario_tuition_annual_usd"] = tuition_after
    scen["scenario_direct_annual_usd"] = direct_after
    scen["scenario_indirect_annual_usd"] = indirect_after
    scen["scenario_total_annual_usd"] = total_after

    min_total = float(total_after.min())
    max_total = float(total_after.max())
    if max_total > min_total:
        scen["scenario_affordability_index"] = 100.0 * (max_total - total_after) / (max_total - min_total)
    else:
        scen["scenario_affordability_index"] = 50.0

    return scen


def compute_target_gap_tables(
    frame: pd.DataFrame,
    target_annual: float,
    *,
    total_col: str = "total_annual_usd",
    tuition_col: str = "Tuition_USD",
    indirect_col: str = "indirect_annual_usd",
) -> Dict[str, pd.DataFrame]:
    """Summarise gaps to a user-defined target annual cost.

    Returns two tables:
    - programs: per-program gap to target, sorted by gap (largest above target first)
    - by_country_level: average gap and share above target, with optional
      tuition vs living-cost composition metrics.
    """

    if frame.empty:
        empty = frame.copy()
        return {"programs": empty, "by_country_level": empty}

    work = frame.copy()

    try:
        target = float(target_annual)
    except Exception:
        target = float(work[total_col].median())

    total_series = work[total_col]
    work["gap_to_target_usd"] = total_series - target
    work["above_target"] = work["gap_to_target_usd"] > 0

    # Per-program table
    program_cols = [
        "Country",
        "University",
        "Program",
        "Level",
        total_col,
        "gap_to_target_usd",
    ]
    programs = work[program_cols].sort_values("gap_to_target_usd", ascending=False)

    # Composition of costs (tuition vs living) for interpretation
    has_tuition = tuition_col in work.columns
    has_indirect = indirect_col in work.columns
    if has_tuition or has_indirect:
        denom = total_series.replace(0, 1e-9)
        if has_tuition:
            work["tuition_share"] = work[tuition_col] / denom
        if has_indirect:
            work["living_share"] = work[indirect_col] / denom

    agg_kwargs = {
        "avg_gap_to_target_usd": ("gap_to_target_usd", "mean"),
        "share_above_target": ("above_target", "mean"),
    }
    if "tuition_share" in work.columns:
        agg_kwargs["mean_tuition_share"] = ("tuition_share", "mean")
    if "living_share" in work.columns:
        agg_kwargs["mean_living_share"] = ("living_share", "mean")

    by_country_level = (
        work.groupby(["Country", "Level"], as_index=False)
        .agg(**agg_kwargs)
        .sort_values("avg_gap_to_target_usd", ascending=False)
    )

    return {"programs": programs, "by_country_level": by_country_level}

