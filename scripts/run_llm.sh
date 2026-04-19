#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/results"

MODEL="${1:-}"
RANDOM_MATCHES="${2:-10}"
PROMPT_NAME="${3:-strict_json}"
STANDARD_MATCHES="${4:-0}"
PROVIDER_NAME="${LLM_PROVIDER:-poligpt}"
LLM_STANDARD_MAX_PERMUTATIONS="${LLM_STANDARD_MAX_PERMUTATIONS:-8}"
LLM_STANDARD_WORKERS="${LLM_STANDARD_WORKERS:-2}"
LLM_RANDOM_WORKERS="${LLM_RANDOM_WORKERS:-4}"
RUN_ID="${BENCHMARK_RUN_ID:-}"

if [[ -z "$MODEL" ]]; then
  echo "Uso: ./scripts/run_llm.sh <model> [random_matches] [prompt] [standard_matches]"
  echo "Ejemplo Poligpt: ./scripts/run_llm.sh poligpt 10 strict_json 0"
  echo "Ejemplo Ollama: LLM_PROVIDER=ollama ./scripts/run_llm.sh llama3.2:3b 10 strict_json 0"
  exit 1
fi

SAFE_MODEL="${MODEL//\//_}"
SAFE_MODEL="${SAFE_MODEL//:/_}"
LABEL="${PROVIDER_NAME}_${SAFE_MODEL}_${PROMPT_NAME}"
LOG_PATH="$RESULTS_DIR/${LABEL}.jsonl"
if [[ -z "$RUN_ID" ]]; then
  RUN_ID="${LABEL}_$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$RESULTS_DIR"

cd "$ROOT_DIR"

if [[ "$PROVIDER_NAME" == "poligpt" ]]; then
  export BENCHMARK_POLIGPT_MODELS="$MODEL"
  TARGET_NAME="poligpt"
elif [[ "$PROVIDER_NAME" == "ollama" ]]; then
  export BENCHMARK_OLLAMA_MODELS="$MODEL"
  TARGET_NAME="ollama"
else
  echo "Provider no soportado en este script: $PROVIDER_NAME"
  exit 1
fi

echo "Ejecutando agente LLM contra random"
CATAN_LLM_PROVIDER="$PROVIDER_NAME" \
CATAN_LLM_PROMPT="$PROMPT_NAME" \
CATAN_LLM_LOG_PATH="$LOG_PATH" \
BENCHMARK_TARGET="$TARGET_NAME" \
BENCHMARK_RUN_ID="$RUN_ID" \
BENCHMARK_WORKERS="$LLM_RANDOM_WORKERS" \
BENCHMARK_RANDOM_MATCHES="$RANDOM_MATCHES" \
python Benchmarks/benchmark_vs_random.py

cp benchmark_vs_random_resultados.csv "$RESULTS_DIR/${LABEL}_random.csv"
cp benchmark_vs_random_resultados.json "$RESULTS_DIR/${LABEL}_random.json"
cp benchmark_vs_random_partidas.csv "$RESULTS_DIR/${LABEL}_random_matches.csv"

if [[ "$STANDARD_MATCHES" -gt 0 ]]; then
  echo "Ejecutando agente LLM contra agentes estandar"
  echo "Modo ligero: workers=$LLM_STANDARD_WORKERS, max_permutations=$LLM_STANDARD_MAX_PERMUTATIONS"
  CATAN_LLM_PROVIDER="$PROVIDER_NAME" \
  CATAN_LLM_PROMPT="$PROMPT_NAME" \
  CATAN_LLM_LOG_PATH="$LOG_PATH" \
  BENCHMARK_TARGET="$TARGET_NAME" \
  BENCHMARK_RUN_ID="$RUN_ID" \
  BENCHMARK_WORKERS="$LLM_STANDARD_WORKERS" \
  BENCHMARK_STANDARD_MAX_PERMUTATIONS="$LLM_STANDARD_MAX_PERMUTATIONS" \
  BENCHMARK_STANDARD_MATCHES="$STANDARD_MATCHES" \
  python Benchmarks/benchmark_vs_agentes_estandar.py

  cp benchmark_vs_estandar_resultados.csv "$RESULTS_DIR/${LABEL}_standard.csv"
  cp benchmark_vs_estandar_resultados.json "$RESULTS_DIR/${LABEL}_standard.json"
  cp benchmark_vs_estandar_partidas.csv "$RESULTS_DIR/${LABEL}_standard_matches.csv"
else
  rm -f "$RESULTS_DIR/${LABEL}_standard.csv" "$RESULTS_DIR/${LABEL}_standard.json" "$RESULTS_DIR/${LABEL}_standard_matches.csv"
fi

python scripts/summarize_llm_log.py "$LOG_PATH" "$RESULTS_DIR/${LABEL}_metrics.csv"

echo "Resultados guardados en $RESULTS_DIR"
