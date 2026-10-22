#!/usr/bin/env python3
"""Block-time series and per-run summary for the overrun experiment."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
BUDGET = 64 / 48000 * 1e6
summary = list(csv.DictReader(open(root / 'summary.csv')))
colors = {'default': '#D55E00', 'interactive': '#0072B2'}


def series(row):
    path = root / 'runs' / f"{int(row['run']):02d}-{row['phase']}-{row['qos']}.csv"
    return [float(r['us']) for r in csv.DictReader(open(path))]


def pick(phase, qos, last=False):
    rows = [r for r in summary if r['phase'] == phase and r['qos'] == qos]
    return rows[-1] if last else rows[0]


fig = plt.figure(figsize=(13, 9))
grid = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.1], hspace=.55, wspace=.15)
panels = [('cool', 'default', False), ('cool', 'interactive', False),
          ('hot', 'default', True), ('hot', 'interactive', True)]
for i, (phase, qos, last) in enumerate(panels):
    ax = fig.add_subplot(grid[i // 2, i % 2])
    row = pick(phase, qos, last)
    ax.plot(series(row), linewidth=.5, color=colors[qos])
    ax.axhline(BUDGET, color='#555555', linestyle='--', linewidth=1)
    ax.set_ylim(0, 2500)
    ax.set_title(f"Run {row['run']}: {phase}, {qos} QoS "
                 f"(mean {float(row['mean_us']):.0f} µs, {row['overruns']} overruns)", fontsize=10)
    ax.set_xlabel('Block index')
    ax.set_ylabel('µs')

ax = fig.add_subplot(grid[2, :])
for qos in ('default', 'interactive'):
    rows = [r for r in summary if r['qos'] == qos]
    ax.plot([int(r['run']) for r in rows], [float(r['mean_us']) for r in rows],
            marker='o', color=colors[qos], label=f'{qos} QoS, mean')
    ax.scatter([int(r['run']) for r in rows], [float(r['p99_us']) for r in rows],
               marker='x', color=colors[qos], label=f'{qos} QoS, p99')
ax.axhline(BUDGET, color='#555555', linestyle='--', linewidth=1)
cool_runs = sum(1 for r in summary if r['phase'] == 'cool')
ax.axvspan(.5, cool_runs + .5, color='#cccccc', alpha=.3, label='cool phase')
ax.set(xlabel='Run (execution order)', ylabel='µs per block')
ax.legend(fontsize=8, ncol=3, frameon=False)
ax.set_title('Per-run mean and p99, 4x oversampling, 32 voices, 16 unison', fontsize=10)
fig.savefig(root / 'overrun-experiment.png', dpi=150, facecolor='white')
print(root / 'overrun-experiment.png')
