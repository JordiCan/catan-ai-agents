#!/usr/bin/env bash
set -euo pipefail

for MODEL in amazon.nova-lite-v1:0 ai21.jamba-1-5-large-v1:0 mistral.mistral-small-2402-v1:0; do
  for PROMPT in strict_json direct_short guided_compact; do
    SAFE_MODEL="${MODEL//:/_}"
    SAFE_MODEL="${SAFE_MODEL//\//_}"

    BENCHMARK_RUN_ID="bedrock_${SAFE_MODEL}_${PROMPT}_small_standard_01" \
    LLM_PROVIDER=bedrock \
    STANDARD_AGENT_NAMES=AdrianHerasAgent,CrabisaAgent,EdoAgent \
    LLM_STANDARD_WORKERS=2 \
    LLM_STANDARD_MAX_PERMUTATIONS=8 \
    CATAN_LLM_TIMEOUT_SECONDS=30 \
    ./scripts/run_llm_standard.sh "$MODEL" 1 "$PROMPT" \
      2>&1 | tee "results/logs/llm_standard_bedrock_${SAFE_MODEL}_${PROMPT}_small.out"

    cp "results/bedrock_${SAFE_MODEL}_${PROMPT}_standard_matches.csv" \
       "results/bedrock_${SAFE_MODEL}_${PROMPT}_small_matches.csv"
  done
done
