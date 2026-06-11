"""
device_sim.py - DO NOT MODIFY

Simulated hardware driver for a signal characterization device.

Mimics the interface of a real instrument driver:

    conn   = connect("192.168.10.5")
    configure(conn, {"tx_level": 180, "eq_gain": 8, "pre_emphasis": 3})
    result = measure(conn, n_samples=500)
    disconnect(conn)

Timing mirrors realistic instrument behaviour.
Hardware logic runs on a remote simulation server.
"""

from __future__ import annotations

import time
import requests

API_URL = "https://hw-eng-challenge-api.onrender.com"


def connect(host: str, port: int = 5025) -> dict:
    """Open a connection to the device (~0.3 s for TCP handshake + init)."""
    time.sleep(0.3)
    return {"host": host, "port": port, "_params": {}}


def disconnect(conn: dict) -> None:
    """Release the connection."""
    time.sleep(0.05)


def configure(conn: dict, params: dict) -> None:
    """
    Apply parameter settings to the device (~0.15 s).

    Expected keys
    -------------
    tx_level     : int, 0-255   Transmit amplitude DAC level.
    eq_gain      : int, 0-15    Receiver equalizer gain.
    pre_emphasis : int, 0-7     Transmitter pre-emphasis tap weight.
    """
    time.sleep(0.15)
    conn["_params"] = dict(params)


def measure(conn: dict, n_samples: int = 500) -> dict | None:
    """
    Collect a measurement from the device.
    Returns None if the measurement fails (signal too weak or instrument error).

    Returns
    -------
    dict with keys:
        snr_db        : float   Signal-to-noise ratio in dB.
        eye_height_mv : float   Eye opening height in millivolts.
        eye_width_ps  : float   Eye opening width in picoseconds.
        ber           : float   Estimated bit error rate.
    """
    time.sleep(n_samples * 0.003)
    payload = {**conn["_params"], "n_samples": n_samples}
    resp = requests.post(f"{API_URL}/measure", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()
