"""
collect_data.py

Sweeps a device under test through a grid of parameter settings,
collects signal characterisation measurements for each, and saves
results to a CSV file.

Usage:
    python collect_data.py
"""

import csv

from device_sim import connect, configure, disconnect, measure


# ---------------------------------------------------------------------------
# Parameter sweep candidates
# ---------------------------------------------------------------------------

CANDIDATES = [
    {"tx_level": tx, "eq_gain": eq, "pre_emphasis": em}
    for tx in range(100, 241, 20)   # 8 levels: 100 … 240
    for eq in range(0,   16,  4)    # 4 levels: 0, 4, 8, 12
    for em in range(0,   8,   2)    # 4 levels: 0, 2, 4, 6
]  # 128 candidates total

OUTPUT_FILE = "results.csv"
FIELDNAMES  = ["trial", "status", "snr_db", "eye_height_mv", "eye_width_ps",
               "ber", "tx_level", "eq_gain", "pre_emphasis"]


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

conn = connect("192.168.10.5")

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()

    for i, candidate in enumerate(CANDIDATES):
        configure(conn, candidate)

        data = measure(conn, n_samples=500)

        if data is None:
            status = "FAIL"
            row = {"trial": i, "status": status, **candidate}
        else:
            status = "PASS" if data["snr_db"] >= 8.0 else "OUT_OF_RANGE"
            row = {"trial": i, "status": status, **data, **candidate}

        writer.writerow(row)
        f.flush()

        print(f"Trial {i:>3d} | {status}")

disconnect(conn)
print("Done.")
