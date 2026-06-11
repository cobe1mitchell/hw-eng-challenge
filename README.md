# Device Measurement Challenge

## Setup

> **IMPORTANT: Read before you start**
>
> **Fork this repo to your own public GitHub account.**
> Work in your fork. **DO NOT open a pull request back to this repository.**
> Doing so would expose your work to other candidates.
> **Failure to follow this instruction will be penalized.**

1. Fork this repo to your own public GitHub account.
2. Clone your fork locally.
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   pip install -r requirements.txt
   ```
4. Run the script to confirm everything works:
   ```bash
   python collect_data.py
   ```

---

## Background

`collect_data.py` sweeps a device under test through a grid of parameter
settings, collects signal characterization measurements for each, and saves
results to a CSV file.

The device is simulated, no real equipment needed. `device_sim.py` handles
communication with the simulation server. In practice, a sweep like this runs
unattended for several minutes while a test engineer waits for results.

**Goal:** Find the combination of parameters that gives the best `snr_db`.
The other measurements (`eye_height_mv`, `eye_width_ps`, `ber`) are correlated
with SNR and can support your analysis.

**Parameters you can set on the device:**

| Parameter | Range | Description |
|---|---|---|
| `tx_level` | 0-255 | Transmit amplitude DAC level |
| `eq_gain` | 0-15 | Receiver equalizer gain |
| `pre_emphasis` | 0-7 | Transmitter pre-emphasis tap weight |

**Measurements returned:**

| Measurement | Description |
|---|---|
| `snr_db` | Signal-to-noise ratio in dB |
| `eye_height_mv` | Eye opening height in millivolts |
| `eye_width_ps` | Eye opening width in picoseconds |
| `ber` | Estimated bit error rate |

---

## Files

| File | Description |
|---|---|
| `device_sim.py` | Do not modify. Hardware driver. |
| `collect_data.py` | Data collection script, modify this. |
| `analyze_results.py` | Write this from scratch. |

---

## Task 1 - Make `collect_data.py` smarter

The script works but it sweeps all combinations blindly regardless of outcome.
Make it smarter. What smarter means is up to you.

## Task 2 - Write `analyze_results.py`

Write a script that loads `results.csv` and visualizes the results. Think about
what would actually help someone decide where to look next.

---

## Submission

Once done, push your work to your fork and notify your recruiter by sending the link to your repo.

Please include a brief write-up in a `NOTES.md` file answering the following:

1. What did you change in `collect_data.py` and why?
2. What does your visualization show? What does it suggest about the device?
3. What would you do next if you had more time?
4. If this were a real device on a real bench, what would you do differently?

If you used AI tools, include the transcript and a brief note on what you kept, changed, or threw out from the output. Include these in your repo (e.g. in `NOTES.md` or a separate `ai_transcript.md`).

Try to keep it under 2 hours. If you find yourself going over, stop and submit what you have.
