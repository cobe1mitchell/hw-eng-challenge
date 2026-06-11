"""
collect_data.py

Smarter parameter search for the device-under-test simulation.

Strategy:
1. Run a coarse sweep over a sparse grid.
2. Keep the best-performing points by snr_db.
3. Refine around those points with smaller steps.
4. Retry transient measurement failures before marking FAIL.
5. Save all results to results.csv.

Usage:
    py collect_data.py
"""

import csv
from typing import Dict, List, Optional, Tuple

from device_sim import connect, configure, disconnect, measure


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

OUTPUT_FILE = "results.csv"
FIELDNAMES = [
    "trial",
    "stage",
    "status",
    "snr_db",
    "eye_height_mv",
    "eye_width_ps",
    "ber",
    "tx_level",
    "eq_gain",
    "pre_emphasis",
]

PASS_SNR_DB = 8.0

# Parameter limits from the README
TX_MIN, TX_MAX = 0, 255
EQ_MIN, EQ_MAX = 0, 15
EM_MIN, EM_MAX = 0, 7

# Search controls
MEASURE_RETRIES = 2            # retry count after the first failure
TOP_K_CENTERS = 5              # refine around the best K coarse points


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def candidate_key(candidate: Dict[str, int]) -> Tuple[int, int, int]:
    return (
        candidate["tx_level"],
        candidate["eq_gain"],
        candidate["pre_emphasis"],
    )


def classify_status(data: Optional[Dict[str, float]]) -> str:
    if data is None:
        return "FAIL"
    return "PASS" if data["snr_db"] >= PASS_SNR_DB else "OUT_OF_RANGE"


def measure_with_retry(conn, n_samples: int = 500) -> Optional[Dict[str, float]]:
    """
    Retry measurement a few times to reduce transient FAILs.
    """
    for _ in range(MEASURE_RETRIES + 1):
        data = measure(conn, n_samples=n_samples)
        if data is not None:
            return data
    return None


def make_row(
    trial_idx: int,
    stage: str,
    candidate: Dict[str, int],
    data: Optional[Dict[str, float]],
) -> Dict:
    status = classify_status(data)

    row = {
        "trial": trial_idx,
        "stage": stage,
        "status": status,
        "tx_level": candidate["tx_level"],
        "eq_gain": candidate["eq_gain"],
        "pre_emphasis": candidate["pre_emphasis"],
    }

    if data is not None:
        row.update({
            "snr_db": data["snr_db"],
            "eye_height_mv": data["eye_height_mv"],
            "eye_width_ps": data["eye_width_ps"],
            "ber": data["ber"],
        })

    return row


def run_trial(conn, writer, trial_idx: int, stage: str, candidate: Dict[str, int]) -> Dict:
    configure(conn, candidate)
    data = measure_with_retry(conn, n_samples=500)
    row = make_row(trial_idx, stage, candidate, data)

    writer.writerow(row)
    print(
        f"Trial {trial_idx:>3d} | "
        f"{stage:<6} | "
        f"{row['status']:<12} | "
        f"tx={candidate['tx_level']:<3d} "
        f"eq={candidate['eq_gain']:<2d} "
        f"em={candidate['pre_emphasis']:<2d}"
    )
    return row


def coarse_candidates() -> List[Dict[str, int]]:
    """
    Broad exploratory sweep.
    Chosen to cover the parameter space sparsely but still reasonably well.
    """
    tx_values = [64, 96, 128, 160, 192, 224, 255]
    eq_values = [0, 4, 8, 12, 15]
    em_values = [0, 2, 4, 6, 7]

    return [
        {"tx_level": tx, "eq_gain": eq, "pre_emphasis": em}
        for tx in tx_values
        for eq in eq_values
        for em in em_values
    ]


def neighborhood(
    center: Dict[str, int],
    tx_step: int,
    eq_step: int,
    em_step: int,
) -> List[Dict[str, int]]:
    """
    Generate a local neighborhood around a promising point.
    """
    tx_values = sorted({
        clamp(center["tx_level"] - tx_step, TX_MIN, TX_MAX),
        center["tx_level"],
        clamp(center["tx_level"] + tx_step, TX_MIN, TX_MAX),
    })
    eq_values = sorted({
        clamp(center["eq_gain"] - eq_step, EQ_MIN, EQ_MAX),
        center["eq_gain"],
        clamp(center["eq_gain"] + eq_step, EQ_MIN, EQ_MAX),
    })
    em_values = sorted({
        clamp(center["pre_emphasis"] - em_step, EM_MIN, EM_MAX),
        center["pre_emphasis"],
        clamp(center["pre_emphasis"] + em_step, EM_MIN, EM_MAX),
    })

    return [
        {"tx_level": tx, "eq_gain": eq, "pre_emphasis": em}
        for tx in tx_values
        for eq in eq_values
        for em in em_values
    ]


def sort_best_rows(rows: List[Dict]) -> List[Dict]:
    valid = [r for r in rows if isinstance(r.get("snr_db"), (int, float))]
    return sorted(valid, key=lambda r: r["snr_db"], reverse=True)


# ---------------------------------------------------------------------------
# Main search flow
# ---------------------------------------------------------------------------

def main():
    conn = connect("192.168.10.5")
    seen = set()
    all_rows: List[Dict] = []
    trial_idx = 0

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        # ---------------------------------------------------------------
        # Stage 1: coarse sweep
        # ---------------------------------------------------------------
        for candidate in coarse_candidates():
            key = candidate_key(candidate)
            if key in seen:
                continue
            seen.add(key)

            row = run_trial(conn, writer, trial_idx, "coarse", candidate)
            all_rows.append(row)
            trial_idx += 1
            f.flush()

        ranked = sort_best_rows(all_rows)

        if not ranked:
            disconnect(conn)
            print("No valid measurements were collected.")
            print("Done.")
            return

        # ---------------------------------------------------------------
        # Stage 2: medium refinement around top coarse points
        # ---------------------------------------------------------------
        top_centers = ranked[:TOP_K_CENTERS]

        for center_row in top_centers:
            center = {
                "tx_level": center_row["tx_level"],
                "eq_gain": center_row["eq_gain"],
                "pre_emphasis": center_row["pre_emphasis"],
            }

            for candidate in neighborhood(center, tx_step=12, eq_step=2, em_step=1):
                key = candidate_key(candidate)
                if key in seen:
                    continue
                seen.add(key)

                row = run_trial(conn, writer, trial_idx, "medium", candidate)
                all_rows.append(row)
                trial_idx += 1
                f.flush()

        # Re-rank after medium refinement
        ranked = sort_best_rows(all_rows)
        best = ranked[0]

        # ---------------------------------------------------------------
        # Stage 3: fine refinement around the current best point
        # ---------------------------------------------------------------
        best_center = {
            "tx_level": best["tx_level"],
            "eq_gain": best["eq_gain"],
            "pre_emphasis": best["pre_emphasis"],
        }

        for candidate in neighborhood(best_center, tx_step=6, eq_step=1, em_step=1):
            key = candidate_key(candidate)
            if key in seen:
                continue
            seen.add(key)

            row = run_trial(conn, writer, trial_idx, "fine", candidate)
            all_rows.append(row)
            trial_idx += 1
            f.flush()

    disconnect(conn)

    ranked = sort_best_rows(all_rows)
    if ranked:
        best = ranked[0]
        print("\nBest setting found:")
        print(
            f"  tx_level      = {best['tx_level']}\n"
            f"  eq_gain       = {best['eq_gain']}\n"
            f"  pre_emphasis  = {best['pre_emphasis']}\n"
            f"  snr_db        = {best['snr_db']:.3f}"
        )

        top_pass = [r for r in ranked if r["status"] == "PASS"][:10]
        if top_pass:
            print("\nTop PASS results:")
            for row in top_pass:
                print(
                    f"  trial={row['trial']:>3d} "
                    f"stage={row['stage']:<6} "
                    f"snr={row['snr_db']:.3f} "
                    f"tx={row['tx_level']:>3d} "
                    f"eq={row['eq_gain']:>2d} "
                    f"em={row['pre_emphasis']:>2d}"
                )

    print(f"\nSaved results to {OUTPUT_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()