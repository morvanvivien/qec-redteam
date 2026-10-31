#!/bin/bash
# Decode one batch at a time and push it at once: the container can be reclaimed at any moment.
cd "$(dirname "$0")/../.."
store=research/duel-d7/batches-d7_p0.003_diaphonie_ZZ_3p_s42_b250.jsonl
while [ "$(wc -l < "$store" 2>/dev/null || echo 0)" -lt 12 ]; do
  .venv/bin/python research/duel-d7/chunked_duel.py --shots 3000 --seed 42 --max-new 1 || exit 1
  git add "$store" && git commit -qm "data(qec-redteam): duel d = 7 sous diaphonie, paquet $(wc -l < "$store")/12

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MhYNbLp7frNb3qwYAB8xTP" && git push -q origin qec/brique-2
done
.venv/bin/python research/duel-d7/chunked_duel.py --shots 3000 --seed 42 > research/duel-d7/results-d7-zz-s42.txt
