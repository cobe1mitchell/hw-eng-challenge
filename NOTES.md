NOTES

1) What did you change in `collect_data.py` and why?

I replaced the original blind sweep with a staged coarse-to-fine search.

Original behavior:
The original script swept a fixed coarse grid of parameter combinations and treated every region of the search space equally, regardless of whether earlier results looked promising.

Changes made:
I updated `collect_data.py` to:

- perform an initial coarse sweep across the parameter space
- rank measured results by `snr_db`
- run a medium refinement search around the best-performing coarse points
- run a fine refinement search around the current best point
- retry transient measurement failures before marking a trial as `FAIL`
- avoid duplicate parameter combinations during refinement
- preserve all measurements in `results.csv`

Why:
The goal was to make the collector smarter than a blind sweep. Instead of spending all test time uniformly across the space, the updated script uses information from early measurements to focus on regions that are more likely to produce high SNR.

This approach produced a clear best setting:

- `tx_level = 186`
- `eq_gain = 8`
- `pre_emphasis = 3`
- `snr_db = 16.589`

---

2) What does the visualization show? What does it suggest about the device?

The analysis and plots show that performance is not random; there is a strong and consistent high-SNR region.

Main observations
- The best-performing settings consistently cluster around:
  - `eq_gain = 8`
  - `pre_emphasis = 3`
  - `tx_level` approximately in the `180–212` range
- The best measured point was:
  - `tx_level = 186`
  - `eq_gain = 8`
  - `pre_emphasis = 3`
  - `snr_db = 16.589`

Metric relationships
The analysis also showed strong correlations:
- `snr_db` vs `eye_height_mv`: strong positive correlation
- `snr_db` vs `eye_width_ps`: strong positive correlation
- `snr_db` vs `ber`: strong negative correlation

This suggests that improving SNR also improves eye quality and reduces BER, which is what I would expect from a healthy operating region.

Device implication:
The device appears to have a relatively smooth optimal region rather than a single isolated point. In particular, `pre_emphasis` seems especially influential, and the combination of `eq_gain = 8` and `pre_emphasis = 3` appears repeatedly among the best results.

The suggested next search window from the analysis was:
- `tx_level: 148 to 236`
- `eq_gain: 7 to 9`
- `pre_emphasis: 2 to 3`

That suggests future tuning should focus around those values instead of the full original space.



3) What would you do next if you had more time?

If I had more time, I would improve both the search strategy and the analysis.

Collector improvements:
- reduce the number of medium/fine refinement trials by refining around fewer top candidates
- add **early stopping** if improvements become very small
- use different sample counts by stage:
  - fewer samples during coarse search
  - more samples during fine search
- preferentially refine around `PASS` results before exploring weaker candidates

Analysis improvements:
- add plots comparing pass rate and average SNR across stages
- quantify the tradeoff between total trial count and best SNR found
- add a local response-surface view around the best setting
- report confidence/repeatability by remeasuring top settings multiple times



4) If this were a real device on a real bench, what would you do differently?

If this were a real bench setup, I would be more careful about measurement repeatability, calibration, and time cost.

On real hardware I would:
- repeat top candidate measurements multiple times to estimate variation and stability
- calibrate instruments and verify the measurement chain before searching
- add logging for timestamp, instrument settings, environmental conditions, and failures
- separate transient communication failures from true electrical failures
- reduce unnecessary retesting because real bench time is expensive
- add safety checks and parameter guardrails before changing device settings
- verify that the “best” setting is still acceptable across multiple operating conditions, not just one measurement snapshot

In a real lab environment, optimizing only for a single best point would not be enough; I would care about robustness, repeatability, and whether the solution remains good over voltage, temperature, and time.

