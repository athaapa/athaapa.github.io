#!/usr/bin/env python3
"""Mean block time and per-run overruns against voice count.

The left panel uses the coarse runs. The right panel uses every run, including
refinement and confirmation attempts, so scattered overruns stay visible.
Mean-crossing counts interpolate linearly between the two coarse points that
straddle the budget.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, StrMethodFormatter

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
with open(root / 'runs.csv') as f:
    runs = [dict(r, factor=int(r['factor']), voices=int(r['voices']),
                 mean_us=float(r['mean_us']), overruns=int(r['overruns']))
            for r in csv.DictReader(f)]
budget = manifest['budget_us']
colors = {1: '#0072B2', 2: '#D55E00', 4: '#009E73'}


def mean_crossing(points):
    for a, b in zip(points, points[1:]):
        if a['mean_us'] <= budget < b['mean_us']:
            t = (budget - a['mean_us']) / (b['mean_us'] - a['mean_us'])
            return a['voices'] + t * (b['voices'] - a['voices'])
    return None


plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False})
fig, (left, right) = plt.subplots(1, 2, figsize=(12, 5.6))

crossings = {}
for factor in (1, 2, 4):
    coarse = sorted((r for r in runs if r['factor'] == factor and r['phase'] == 'coarse'),
                    key=lambda r: r['voices'])
    left.plot([r['voices'] for r in coarse], [r['mean_us'] for r in coarse],
              color=colors[factor], marker='o', markersize=4.5, linewidth=2,
              label=f'{factor}× oversampling')
    crossing = mean_crossing(coarse)
    crossings[factor] = crossing
    if crossing is not None:
        left.plot([crossing], [budget], marker='v', markersize=9, color=colors[factor])

    every = [r for r in runs if r['factor'] == factor]
    right.scatter([r['voices'] for r in every], [max(r['overruns'], 0.5) for r in every],
                  color=colors[factor], s=22, alpha=.8, label=f'{factor}× oversampling')
    if crossing is not None:
        right.axvline(crossing, color=colors[factor], linestyle=':', linewidth=1.4)

left.axhline(budget, color='#555555', linestyle='--', linewidth=1.4)
left.text(7, budget + 65, '1,333 µs buffer budget', color='#555555', fontsize=10)
left.set(title='Mean block time (coarse runs)', xlabel='Voices',
         ylabel='Time per 64-frame block (µs)', xlim=(4, 132), ylim=(0, 3200))
left.set_xticks([8, 32, 64, 96, 128])
left.yaxis.set_major_locator(MultipleLocator(500))
left.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
left.grid(axis='y', alpha=.18)
left.legend(loc='upper left', frameon=False, fontsize=10)

right.set_yscale('log')
right.set(title='Blocks over budget per 5,000-block run (all runs)', xlabel='Voices',
          ylabel='Overruns (zero plotted at 0.5)', xlim=(4, 132), ylim=(0.3, 8000))
right.set_xticks([8, 32, 64, 96, 128])
right.grid(axis='y', alpha=.18)
fig.suptitle('mohg: voice-count sweep on Apple M4', fontsize=16, x=.07, ha='left', y=.98)
fig.text(.07, .885, '48 kHz · 16 unison · 100 warmup blocks + 5,000 measured blocks per run',
         fontsize=10, color='#444444')
fig.text(.07, .025, f'Commit {manifest["commit"][:12]} · Odin {manifest["odin"].split("version ", 1)[-1]}'
         ' · offline elapsed time\nTriangles (left) and dotted lines (right) mark where each mean crosses the budget.',
         fontsize=9, color='#444444')
fig.subplots_adjust(left=.07, right=.985, top=.82, bottom=.19, wspace=.2)

images = root.parents[2] / 'images' / 'mohg'
for extension in ('svg', 'png'):
    fig.savefig(images / f'final-voice-sweep.{extension}', dpi=180, facecolor='white')
for factor, crossing in crossings.items():
    print(f'{factor}x mean crossing: {crossing:.1f} voices')
