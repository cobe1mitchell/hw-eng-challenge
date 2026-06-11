"""
analyze_results.py

Loads results.csv from the device measurement challenge, prints a summary
of the best-performing parameter settings, and generates plots to help
identify promising regions for further testing.

Outputs:
- analysis_summary.txt
- best_results.csv
- snr_vs_parameters.png
- snr_relationships.png
- heatmap_pre_emphasis_<value>.png   (one per pre_emphasis setting found)
- pass_rate_by_pre_emphasis.png

Usage:
    py analyze_results.py
"""

from pathlib import Path
from typing import List

import pandas as pd
import matplotlib.pyplot as plt


RESULTS_FILE = Path("results.csv")
SUMMARY_FILE = Path("analysis_summary.txt")
BEST_RESULTS_FILE = Path("best_results.csv")

NUMERIC_COLUMNS = [
    "trial",
    "snr_db",
    "eye_height_mv",
    "eye_width_ps",
    "ber",
    "tx_level",
    "eq_gain",
    "pre_emphasis",
]

PARAMETERS = ["tx_level", "eq_gain", "pre_emphasis"]


def load_results(path: Path) -> pd.DataFrame:
    """Load results.csv and normalize column types."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path}. Run collect_data.py first to generate results.csv."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"{path} exists but contains no rows.")

    missing = [col for col in ["status", *PARAMETERS] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in {path}: {missing}")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Backward compatibility with the original collect_data.py
    if "stage" not in df.columns:
        df["stage"] = "unknown"

    return df


def best_numeric_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with numeric SNR, sorted from best to worst."""
    valid = df[df["snr_db"].notna()].copy()
    return valid.sort_values("snr_db", ascending=False)


def summarize(df: pd.DataFrame) -> str:
    """Build a human-readable text summary."""
    lines: List[str] = []

    total = len(df)
    valid = df[df["snr_db"].notna()].copy()
    passes = df[df["status"] == "PASS"].copy()
    out_of_range = df[df["status"] == "OUT_OF_RANGE"].copy()
    fails = df[df["status"] == "FAIL"].copy()

    lines.append("Device Measurement Challenge - Results Summary")
    lines.append("=" * 52)
    lines.append(f"Total trials: {total}")
    lines.append(f"Trials with numeric measurements: {len(valid)}")
    lines.append(f"PASS count: {len(passes)}")
    lines.append(f"OUT_OF_RANGE count: {len(out_of_range)}")
    lines.append(f"FAIL count: {len(fails)}")
    lines.append("")

    if not valid.empty:
        best = valid.sort_values("snr_db", ascending=False).iloc[0]
        lines.append("Best overall measured setting:")
        lines.append(
            f"  trial={int(best['trial']) if pd.notna(best['trial']) else 'n/a'}  "
            f"stage={best.get('stage', 'unknown')}  status={best['status']}"
        )
        lines.append(
            f"  tx_level={int(best['tx_level'])}, "
            f"eq_gain={int(best['eq_gain'])}, "
            f"pre_emphasis={int(best['pre_emphasis'])}"
        )
        lines.append(
            f"  snr_db={best['snr_db']:.3f}, "
            f"eye_height_mv={best['eye_height_mv']:.3f}, "
            f"eye_width_ps={best['eye_width_ps']:.3f}, "
            f"ber={best['ber']:.6g}"
        )
        lines.append("")

    if not passes.empty:
        best_pass = passes.sort_values("snr_db", ascending=False).iloc[0]
        lines.append("Best PASS setting:")
        lines.append(
            f"  trial={int(best_pass['trial']) if pd.notna(best_pass['trial']) else 'n/a'}  "
            f"stage={best_pass.get('stage', 'unknown')}"
        )
        lines.append(
            f"  tx_level={int(best_pass['tx_level'])}, "
            f"eq_gain={int(best_pass['eq_gain'])}, "
            f"pre_emphasis={int(best_pass['pre_emphasis'])}"
        )
        lines.append(
            f"  snr_db={best_pass['snr_db']:.3f}, "
            f"eye_height_mv={best_pass['eye_height_mv']:.3f}, "
            f"eye_width_ps={best_pass['eye_width_ps']:.3f}, "
            f"ber={best_pass['ber']:.6g}"
        )
        lines.append("")

    if not valid.empty:
        grouped = (
            valid.groupby(PARAMETERS, dropna=False)["snr_db"]
            .mean()
            .reset_index()
            .sort_values("snr_db", ascending=False)
        )

        lines.append("Top 10 parameter combinations by mean snr_db:")
        for _, row in grouped.head(10).iterrows():
            lines.append(
                f"  snr_db={row['snr_db']:.3f} | "
                f"tx_level={int(row['tx_level'])}, "
                f"eq_gain={int(row['eq_gain'])}, "
                f"pre_emphasis={int(row['pre_emphasis'])}"
            )
        lines.append("")

        corr_cols = [c for c in ["snr_db", "eye_height_mv", "eye_width_ps", "ber"] if c in valid.columns]
        corr = valid[corr_cols].corr(numeric_only=True)

        lines.append("Metric correlations:")
        for col in corr.columns:
            if col == "snr_db":
                continue
            value = corr.loc["snr_db", col]
            lines.append(f"  corr(snr_db, {col}) = {value:.3f}")
        lines.append("")

        param_scores = []
        for param in PARAMETERS:
            grouped_param = valid.groupby(param)["snr_db"].mean()
            spread = grouped_param.max() - grouped_param.min()
            param_scores.append((param, spread))
        param_scores.sort(key=lambda x: x[1], reverse=True)

        lines.append("Parameter influence estimate (based on mean-snr range):")
        for name, spread in param_scores:
            lines.append(f"  {name}: {spread:.3f} dB spread")
        lines.append("")

        best_rows = valid.sort_values("snr_db", ascending=False).head(20)
        tx_lo = int(best_rows["tx_level"].min())
        tx_hi = int(best_rows["tx_level"].max())
        eq_lo = int(best_rows["eq_gain"].min())
        eq_hi = int(best_rows["eq_gain"].max())
        em_lo = int(best_rows["pre_emphasis"].min())
        em_hi = int(best_rows["pre_emphasis"].max())

        lines.append("Suggested next search window (based on top 20 rows):")
        lines.append(f"  tx_level: {tx_lo} to {tx_hi}")
        lines.append(f"  eq_gain: {eq_lo} to {eq_hi}")
        lines.append(f"  pre_emphasis: {em_lo} to {em_hi}")
        lines.append("")

    return "\n".join(lines)


def save_best_table(df: pd.DataFrame) -> None:
    """Save the top 25 rows by snr_db to a CSV file."""
    best = best_numeric_rows(df).head(25).copy()
    if not best.empty:
        best.to_csv(BEST_RESULTS_FILE, index=False)


def plot_snr_vs_parameters(df: pd.DataFrame) -> None:
    """Create scatter plots of snr_db versus each controllable parameter."""
    valid = best_numeric_rows(df)
    if valid.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    status_order = ["PASS", "OUT_OF_RANGE", "FAIL"]
    colors = {
        "PASS": "tab:green",
        "OUT_OF_RANGE": "tab:orange",
        "FAIL": "tab:red",
    }

    for ax, param in zip(axes, PARAMETERS):
        for status in status_order:
            subset = valid[valid["status"] == status]
            if subset.empty:
                continue
            ax.scatter(
                subset[param],
                subset["snr_db"],
                label=status,
                alpha=0.75,
                s=36,
                c=colors[status],
                edgecolors="none",
            )

        ax.set_xlabel(param)
        ax.set_ylabel("snr_db")
        ax.set_title(f"snr_db vs {param}")
        ax.grid(True, alpha=0.25)

    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=3)

    fig.suptitle("SNR versus controllable parameters", y=1.03)
    fig.savefig("snr_vs_parameters.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_metric_relationships(df: pd.DataFrame) -> None:
    """Create scatter plots showing how supporting metrics track with snr_db."""
    valid = best_numeric_rows(df)
    if valid.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    axes[0].scatter(valid["eye_height_mv"], valid["snr_db"], alpha=0.75, s=36)
    axes[0].set_xlabel("eye_height_mv")
    axes[0].set_ylabel("snr_db")
    axes[0].set_title("SNR vs eye height")
    axes[0].grid(True, alpha=0.25)

    axes[1].scatter(valid["eye_width_ps"], valid["snr_db"], alpha=0.75, s=36)
    axes[1].set_xlabel("eye_width_ps")
    axes[1].set_ylabel("snr_db")
    axes[1].set_title("SNR vs eye width")
    axes[1].grid(True, alpha=0.25)

    positive_ber = valid[valid["ber"] > 0]
    if positive_ber.empty:
        axes[2].scatter(valid["ber"], valid["snr_db"], alpha=0.75, s=36)
    else:
        axes[2].scatter(positive_ber["ber"], positive_ber["snr_db"], alpha=0.75, s=36)
        axes[2].set_xscale("log")

    axes[2].set_xlabel("ber")
    axes[2].set_ylabel("snr_db")
    axes[2].set_title("SNR vs BER")
    axes[2].grid(True, alpha=0.25)

    fig.suptitle("Relationships between SNR and supporting measurements", y=1.03)
    fig.savefig("snr_relationships.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_heatmaps(df: pd.DataFrame) -> None:
    """
    Create one heatmap per pre_emphasis value, plotting:
    - x axis: tx_level
    - y axis: eq_gain
    - color: mean snr_db
    """
    valid = best_numeric_rows(df)
    if valid.empty:
        return

    unique_em = sorted(valid["pre_emphasis"].dropna().unique())

    for em_value in unique_em:
        subset = valid[valid["pre_emphasis"] == em_value]
        if subset.empty:
            continue

        pivot = subset.pivot_table(
            index="eq_gain",
            columns="tx_level",
            values="snr_db",
            aggfunc="mean",
        ).sort_index().sort_index(axis=1)

        if pivot.empty:
            continue

        fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
        im = ax.imshow(pivot.values, aspect="auto", origin="lower")

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([str(int(v)) for v in pivot.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([str(int(v)) for v in pivot.index])

        ax.set_xlabel("tx_level")
        ax.set_ylabel("eq_gain")
        ax.set_title(f"Mean snr_db heatmap at pre_emphasis={int(em_value)}")

        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("snr_db")

        for y in range(pivot.shape[0]):
            for x in range(pivot.shape[1]):
                value = pivot.iloc[y, x]
                if pd.notna(value):
                    ax.text(x, y, f"{value:.1f}", ha="center", va="center", fontsize=8)

        fig.savefig(
            f"heatmap_pre_emphasis_{int(em_value)}.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig)


def plot_pass_rate(df: pd.DataFrame) -> None:
    """Plot PASS fraction by pre_emphasis."""
    rates = (
        df.assign(pass_flag=(df["status"] == "PASS").astype(int))
        .groupby("pre_emphasis")["pass_flag"]
        .mean()
        .sort_index()
    )

    if rates.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    ax.bar(rates.index.astype(int).astype(str), rates.values)

    ax.set_xlabel("pre_emphasis")
    ax.set_ylabel("PASS fraction")
    ax.set_title("PASS rate by pre_emphasis")
    ax.set_ylim(0, 1)
    ax.grid(True, axis="y", alpha=0.25)

    fig.savefig("pass_rate_by_pre_emphasis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    try:
        df = load_results(RESULTS_FILE)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    summary = summarize(df)
    print(summary)

    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    save_best_table(df)
    plot_snr_vs_parameters(df)
    plot_metric_relationships(df)
    plot_heatmaps(df)
    plot_pass_rate(df)

    print("\nSaved outputs:")
    print(f"  - {SUMMARY_FILE}")
    if BEST_RESULTS_FILE.exists():
        print(f"  - {BEST_RESULTS_FILE}")

    for p in sorted(Path(".").glob("*.png")):
        if (
            p.name.startswith("snr_")
            or p.name.startswith("heatmap_")
            or p.name.startswith("pass_rate_")
        ):
            print(f"  - {p.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
