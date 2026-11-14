#!/bin/bash
# Run SelfCheck and the one-prompt baseline on every practice passage, from a clean results folder.
. ~/selfcheck-env/bin/activate
cd ~/selfcheck
if [ -d results ]; then mv results "results_old_$(date +%H%M%S)"; fi
for p in passages/sample*.txt; do
  for mode in selfcheck baseline careful; do
    echo "RUN $p $mode"
    python selfcheck.py "$p" --mode "$mode" > /dev/null 2>&1 || echo "FAILED $p $mode"
  done
done
echo EVAL_DONE
