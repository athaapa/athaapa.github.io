#!/bin/zsh
# Overrun experiment: 4x, 32 voices, 16 unison, 5000 blocks per run.
# Cool phase: idle before each run. Hot phase: back-to-back runs.
# Default and interactive QoS alternate in both phases.
set -e
cd "$(dirname "$0")"
BENCH=../bench_blocks
ARGS=(render --voices 32 --unison 16 --oversampling 4 --frames 64 --blocks 5000 --warmup 100 --cutoff 15000 --resonance 0.9 --drive 1)
mkdir -p runs
echo "run,phase,qos,start_epoch,mean_us,p50_us,p99_us,overruns" > summary.csv

pmset -g thermlog > thermlog.txt 2>&1 &
THERM=$!
trap "kill $THERM 2>/dev/null" EXIT

run() {
  local n=$1 phase=$2 qos=$3
  local csv=runs/$(printf %02d $n)-$phase-$qos.csv
  local start=$(date +%s)
  local line
  if [ $qos = interactive ]; then
    line=$(MOHG_QOS=interactive MOHG_BLOCK_CSV=$csv $BENCH $ARGS | tail -1)
  else
    line=$(MOHG_BLOCK_CSV=$csv $BENCH $ARGS | tail -1)
  fi
  set -- ${=line}
  echo "$n,$phase,$qos,$start,$2,$3,$4,${7%%/*}" >> summary.csv
  echo "$n $phase $qos mean=$2 p99=$4 overruns=$7"
}

n=0
for pair in 1 2 3 4; do
  for qos in default interactive; do
    sleep 45
    n=$((n + 1)); run $n cool $qos
  done
done
for i in $(seq 1 20); do
  for qos in default interactive; do
    n=$((n + 1)); run $n hot $qos
  done
done
echo done
