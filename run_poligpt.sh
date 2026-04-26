for MODEL in poligpt qwen phi4; do
  for PROMPT in strict_json direct_short guided_compact; do
    SAFE_MODEL="${MODEL//:/_}"
    SAFE_MODEL="${SAFE_MODEL//\//_}"

    BENCHMARK_RUN_ID="${MODEL}_${PROMPT}_small_standard_01" \
    STANDARD_AGENT_NAMES=AdrianHerasAgent,CrabisaAgent,EdoAgent \
    LLM_STANDARD_WORKERS=2 \
    LLM_STANDARD_MAX_PERMUTATIONS=8 \
    CATAN_LLM_TIMEOUT_SECONDS=30 \
    ./scripts/run_llm_standard.sh "$MODEL" 1 "$PROMPT" \
      2>&1 | tee "results/logs/llm_standard_${SAFE_MODEL}_${PROMPT}_small.out"

    cp "results/poligpt_${SAFE_MODEL}_${PROMPT}_standard_matches.csv" \
       "results/poli_${SAFE_MODEL}_${PROMPT}_small_matches.csv"
  done
done

