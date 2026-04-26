#!/usr/bin/env bash
set -euo pipefail

for MODEL in llama3.2:3b gemma3:1b ministral-3:3b; do
  for PROMPT in strict_json direct_short guided_compact; do
    SAFE_MODEL="${MODEL//:/_}"
    SAFE_MODEL="${SAFE_MODEL//\//_}"

    BENCHMARK_RUN_ID="ollama_${SAFE_MODEL}_${PROMPT}_small_standard_01" \
    LLM_PROVIDER=ollama \
    STANDARD_AGENT_NAMES=AdrianHerasAgent,CrabisaAgent,EdoAgent \
    LLM_STANDARD_WORKERS=1 \
    LLM_STANDARD_MAX_PERMUTATIONS=8 \
    CATAN_LLM_TIMEOUT_SECONDS=10 \
    ./scripts/run_llm_standard.sh "$MODEL" 1 "$PROMPT" \
      2>&1 | tee "results/logs/llm_standard_ollama_${SAFE_MODEL}_${PROMPT}_small.out"

    cp "results/ollama_${SAFE_MODEL}_${PROMPT}_standard_matches.csv" \
       "results/ollama_${SAFE_MODEL}_${PROMPT}_small_matches.csv"
  done
done
