#!/usr/bin/env python3
"""Final offline sweep: one immutable executable, raw reports, and provenance."""
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'
OUT.mkdir(exist_ok=True)
EXE = ROOT/'build/bench'
COMMIT = 'ed7293a84d9044f143beaea6afada5b67abb3816'
BLOCKS = 5000
WARMUP = 100
rows = []


def command(*args):
    return subprocess.check_output(args, text=True).strip()


manifest = {
    'commit': COMMIT,
    'odin': command('odin', 'version'),
    'machine': command('sysctl', '-n', 'machdep.cpu.brand_string'),
    'platform': platform.platform(),
    'build': 'odin build bench -o:speed -debug -out:build/bench',
    'executable_sha256': hashlib.sha256(EXE.read_bytes()).hexdigest(),
    'sample_rate_hz': 48000, 'frames': 64, 'unison': 16,
    'waveform': 'saw', 'cutoff_hz': 15000, 'resonance': 0.9, 'drive': 1,
    'blocks_per_run': BLOCKS, 'warmup_blocks_per_run': WARMUP,
    'budget_us': 64/48000*1e6, 'voice_pool_limit': 128,
    'capacity_protocol': ('Coarse counts 8,16,32,48,64,80,96,112,128 at each factor; '
                          'refine individual counts above the largest passing coarse point '
                          'up to the next coarse point; confirm candidate in two more runs. '
                          'Any observed overrun disqualifies that candidate. '
                          'Report the largest tested count passing all three runs, not a bound.'),
    'started_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
}
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


def save():
    (OUT/'runs.json').write_text(json.dumps(rows, indent=2)+'\n')
    with (OUT/'runs.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def measure(factor, voices, phase):
    attempt = sum(r['factor'] == factor and r['voices'] == voices for r in rows)
    args = [str(EXE), 'render', '--voices', str(voices), '--unison', '16',
            '--oversampling', str(factor), '--frames', '64', '--blocks', str(BLOCKS),
            '--warmup', str(WARMUP), '--cutoff', '15000', '--resonance', '0.9', '--drive', '1']
    output = subprocess.check_output(args, text=True)
    (OUT/f'L{factor}-n{voices:03d}-r{attempt}-{phase}.txt').write_text(output)
    fields = next(line.split() for line in output.splitlines()
                  if re.match(r'^\s*'+str(voices)+r'\s+\d', line))
    missed, count = map(int, fields[6].split('/'))
    row = dict(factor=factor, voices=voices, attempt=attempt, phase=phase,
               mean_us=float(fields[1]), p50_us=float(fields[2]), p99_us=float(fields[3]),
               overruns=missed, blocks=count)
    rows.append(row)
    save()
    print(f'{phase:8} L={factor} n={voices:3}: mean={row["mean_us"]:8.2f} '
          f'p99={row["p99_us"]:8.2f}, overruns={missed}/{count}', flush=True)
    return row


print(f'Commit {COMMIT}; {manifest["odin"]}', flush=True)
coarse = [8,16,32,48,64,80,96,112,128]
for n in coarse:
    for factor in (1,2,4):
        measure(factor, n, 'coarse')

capacities = []
for factor in (1,2,4):
    passed = [r['voices'] for r in rows if r['factor'] == factor and r['overruns'] == 0]
    if not passed:
        candidates = range(7, 0, -1)
    else:
        best = max(passed)
        upper = min((n for n in coarse if n > best), default=129)
        candidates = range(min(128, upper-1), 0, -1)
    for n in candidates:
        observations = [r for r in rows if r['factor'] == factor and r['voices'] == n]
        if not observations:
            observations.append(measure(factor, n, 'refine'))
        if any(r['overruns'] for r in observations):
            continue
        while len(observations) < 3:
            observations.append(measure(factor, n, 'confirm'))
            if observations[-1]['overruns']:
                break
        if any(r['overruns'] for r in observations):
            continue
        cap = dict(factor=factor, voices=n, pool_limited=n == 128,
                   blocks=sum(r['blocks'] for r in observations),
                   overruns=0, mean_us=statistics.mean(r['mean_us'] for r in observations),
                   maximum_run_p99_us=max(r['p99_us'] for r in observations))
        capacities.append(cap)
        print('CAPACITY '+json.dumps(cap), flush=True)
        break
    else:
        capacities.append(dict(factor=factor, voices=0, pool_limited=False))

manifest['finished_at_local'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
assert manifest['executable_sha256'] == hashlib.sha256(EXE.read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
(OUT/'capacities.json').write_text(json.dumps(capacities, indent=2)+'\n')
print('Finished. Evidence: '+str(OUT), flush=True)
