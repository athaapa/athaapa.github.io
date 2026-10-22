# Overrun experiment, 2026-10-22

Source: commit 2c9f8d3a607589df0ee4a2847fb78225afcf6ff4, built with
odin build bench -o:speed -debug. Apple M4 MacBook Air.

run.sh runs 4x oversampling, 32 voices, 16 unison, 64 frames, 5000 measured
blocks after 100 warmup blocks, 15 kHz cutoff, 0.9 resonance, 1.0 drive.
Runs 1-8 wait 45 s before starting ("cool"); runs 9-48 run back to back
("hot"). Default and interactive QoS alternate in both phases.

- runs/NN-phase-qos.csv: every block's duration in execution order
  (MOHG_BLOCK_CSV).
- summary.csv: each run's mean, p50, p99, and overrun count.
- thermlog.txt: output of pmset -g thermlog during the experiment (empty).
- plot.py: produces overrun-experiment.png.
