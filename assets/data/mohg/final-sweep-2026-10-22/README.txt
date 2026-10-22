# Final voice-count sweep, 2026-10-22

The manifest records the source commit, compiler, platform, executable hash,
settings, and start/end times. Every configuration used the same executable
built from a `git archive` of that commit. The working checkout was untouched.

`runs.csv` and `runs.json` preserve execution order and every attempt, including
failed confirmations. Raw CLI reports use filenames with factor, voice count,
attempt, and phase. `capacities.json` records the first count in each descending
refinement search that passed three 5,000-block runs without an overrun.

These are observed offline counts under the recorded search protocol. The
search does not test every integer count above a selected count. Elapsed-time
variation can change the selected count on another run. The earlier notes'
115/64/34 counts used a different revision and procedure.

Capacity means are averages of three equal-sized run means. Capacity p99 is the
maximum of the three reported per-run p99 values. The plot uses only the coarse
points, one run per point; it retains their p99 spikes. All timings are rounded
to the CLI's 0.01 microsecond output precision. Overruns count blocks strictly
longer than 64/48000 seconds, including pauses during the timed render call.

## Reproduction

Create an empty directory, extract the recorded commit into it, and build:

```sh
clang -fblocks -O2 -c src/core_midi_bridge.c -o build/core_midi_bridge.o
clang -O2 -g -c bench/signpost_bridge.c -o build/signpost_bridge.o
odin build bench -o:speed -debug -out:build/bench
```

Create `build/` before those commands if it is absent. Use the Odin version in
the manifest. Place `run_sweep.py` at the root of the extracted source tree and
run `python3 run_sweep.py`. It writes a fresh `results/` directory; use a new
extracted tree to preserve these results. Plot with `python3 plot_sweep.py`
(requires Matplotlib).

The script calls the existing `render` command. Each process initializes fresh
synth state and uses 100 warmup blocks followed by 5,000 measured blocks. The
benchmark plays MIDI notes 48 + (voice index modulo 80), velocity 100, with
16 detuned saw oscillators per voice, seed 1, sustain level 1, noise amplitude
0.005, and chorus off. Filter cutoff is 15 kHz, resonance 0.9, and drive 1.

No CPU affinity or fixed clock was requested. The benchmark ran sequentially
as a normal offline process on the working MacBook Air. The probe excludes live
CoreAudio scheduling and MIDI processing.
