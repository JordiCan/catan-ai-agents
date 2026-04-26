#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/results"

MODEL="${1:-}"
STANDARD_MATCHES="${2:-1}"
PROMPT_NAME="${3:-strict_json}"
PROVIDER_NAME="${LLM_PROVIDER:-poligpt}"
LLM_STANDARD_MAX_PERMUTATIONS="${LLM_STANDARD_MAX_PERMUTATIONS:-8}"
LLM_STANDARD_WORKERS="${LLM_STANDARD_WORKERS:-4}"
STANDARD_AGENT_NAMES="${STANDARD_AGENT_NAMES:-RandomAgent,CrabisaAgent,EdoAgent}"
RUN_ID="${BENCHMARK_RUN_ID:-}"

if [[ -z "$MODEL" ]]; then
  echo "Uso: ./scripts/run_llm_standard.sh <model> [standard_matches] [prompt]"
  echo "Ejemplo Poligpt: ./scripts/run_llm_standard.sh poligpt 1 strict_json"
  echo "Ejemplo Ollama: LLM_PROVIDER=ollama ./scripts/run_llm_standard.sh llama3.2:3b 1 strict_json"
  echo "Por defecto usa estos rivales: RandomAgent,CrabisaAgent,EdoAgent"
  echo "Puedes cambiarlos con STANDARD_AGENT_NAMES=RandomAgent,CrabisaAgent,EdoAgent"
  exit 1
fi

SAFE_MODEL="${MODEL//\//_}"
SAFE_MODEL="${SAFE_MODEL//:/_}"
LABEL="${PROVIDER_NAME}_${SAFE_MODEL}_${PROMPT_NAME}"
LOG_PATH="$RESULTS_DIR/${LABEL}.jsonl"
if [[ -z "$RUN_ID" ]]; then
  RUN_ID="${LABEL}_standard_$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$RESULTS_DIR"
cd "$ROOT_DIR"

if [[ "$PROVIDER_NAME" == "poligpt" ]]; then
  export BENCHMARK_POLIGPT_MODELS="$MODEL"
  TARGET_NAME="poligpt"
elif [[ "$PROVIDER_NAME" == "ollama" ]]; then
  export BENCHMARK_OLLAMA_MODELS="$MODEL"
  TARGET_NAME="ollama"
elif [[ "$PROVIDER_NAME" == "bedrock" ]]; then
  if [[ "$MODEL" != bedrock/* ]]; then
    export CATAN_LLM_MODEL="bedrock/$MODEL"
  else
    export CATAN_LLM_MODEL="$MODEL"
  fi
  TARGET_NAME="bedrock"
else
  echo "Provider no soportado en este script: $PROVIDER_NAME"
  exit 1
fi

echo "Ejecutando agente LLM solo contra agentes estandar"
echo "Modo ligero: workers=$LLM_STANDARD_WORKERS, max_permutations=$LLM_STANDARD_MAX_PERMUTATIONS"
echo "Agentes rivales: $STANDARD_AGENT_NAMES"

CATAN_LLM_PROVIDER="$PROVIDER_NAME" \
CATAN_LLM_PROMPT="$PROMPT_NAME" \
CATAN_LLM_LOG_PATH="$LOG_PATH" \
BENCHMARK_TARGET="$TARGET_NAME" \
BENCHMARK_RUN_ID="$RUN_ID" \
BENCHMARK_WORKERS="$LLM_STANDARD_WORKERS" \
BENCHMARK_STANDARD_MAX_PERMUTATIONS="$LLM_STANDARD_MAX_PERMUTATIONS" \
BENCHMARK_STANDARD_MATCHES="$STANDARD_MATCHES" \
BENCHMARK_STANDARD_AGENT_NAMES="$STANDARD_AGENT_NAMES" \
python Benchmarks/benchmark_vs_agentes_estandar.py

cp benchmark_vs_estandar_resultados.csv "$RESULTS_DIR/${LABEL}_standard.csv"
cp benchmark_vs_estandar_resultados.json "$RESULTS_DIR/${LABEL}_standard.json"
cp benchmark_vs_estandar_partidas.csv "$RESULTS_DIR/${LABEL}_standard_matches.csv"

python scripts/summarize_llm_log.py "$LOG_PATH" "$RESULTS_DIR/${LABEL}_metrics.csv"

echo "Resultados guardados en $RESULTS_DIR"
