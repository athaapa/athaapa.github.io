#!/usr/bin/env python3
"""Plot the nine coarse configurations; keep all refinement data in the CSV."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, StrMethodFormatter

root = Path(__file__).resolve().parent
out = root / 'results'
manifest = json.loads((out / 'manifest.json').read_text())
runs = json.loads((out / 'runs.json').read_text())
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False})
fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), sharey=True)
colors = {1: '#0072B2', 2: '#D55E00', 4: '#009E73'}
for ax, key, title in zip(axes, ('mean_us', 'p99_us'), ('Mean block time', 'p99 block time')):
    for factor in (1, 2, 4):
        points = sorted((r for r in runs if r['factor'] == factor and r['phase'] == 'coarse'),
                        key=lambda r: r['voices'])
        ax.plot([r['voices'] for r in points], [r[key] for r in points],
                color=colors[factor], marker='o', markersize=4.5, linewidth=2,
                label=f'{factor}× oversampling')
    ax.axhline(manifest['budget_us'], color='#555555', linestyle='--', linewidth=1.4)
    ax.text(7, manifest['budget_us'] + 65, '1,333 µs buffer budget', color='#555555', fontsize=10)
    ax.set(title=title, xlabel='Voices', xlim=(4, 132), ylim=(0, 3500))
    ax.set_xticks([8, 32, 64, 96, 128])
    ax.yaxis.set_major_locator(MultipleLocator(500))
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    ax.grid(axis='y', alpha=.18)
axes[0].set_ylabel('Time per 64-frame block (µs)')
axes[0].legend(loc='upper left', frameon=False, fontsize=10)
fig.suptitle('mohg: voice-count sweep on Apple M4', fontsize=16, x=.08, ha='left', y=.98)
fig.text(.08, .885, '48 kHz · 16 unison · 100 warmup blocks + 5,000 measured blocks per point',
         fontsize=10, color='#444444')
fig.text(.08, .025, f'Commit {manifest["commit"][:12]} · Odin {manifest["odin"].split("version ", 1)[-1]}\n'
         'Offline elapsed time. Each point is one run; p99 spikes remain in the plot.',
         fontsize=9, color='#444444')
fig.subplots_adjust(left=.08, right=.985, top=.82, bottom=.19, wspace=.12)
for extension in ('svg', 'png'):
    fig.savefig(out / f'final-voice-sweep.{extension}', dpi=180, facecolor='white')
print(out / 'final-voice-sweep.svg')
