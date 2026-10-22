# Alias measurement, 2026-10-22

Source: commit 2c9f8d3a607589df0ee4a2847fb78225afcf6ff4. It's the sweep commit
ed7293a plus a benchmark-only change that adds the folded-harmonic summary at the
end of each output file. alias-metric.patch is that change to bench/alias.odin.

Compiler: odin version dev-2026-09:a2fb372b7, built with -o:speed.

Each file is the full output of:

    build/bench alias --waveform <sine|saw> --frequency <5000|3520> \
      --oversampling <1|2|4> --samples 65536

Alias defaults: 20 kHz cutoff, 0 resonance, 4.0 drive, one voice, one
oscillator, left channel, Hann window, 0.1 s warmup. The RNG is seeded, so the
output is deterministic.

The summary sums power at the 48 kHz bins where harmonics 2..63 above the
output Nyquist land, relative to the fundamental. Folds onto DC or an in-band
harmonic are skipped. "Same bins in ref" reads those bins from the 384 kHz
reference render.
