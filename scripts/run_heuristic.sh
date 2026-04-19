#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/results"

RANDOM_MATCHES="${1:-20}"
STANDARD_MATCHES="${2:-0}"
RUN_ID="${BENCHMARK_RUN_ID:-heuristic_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$RESULTS_DIR"

cd "$ROOT_DIR"

if [[ "$RANDOM_MATCHES" -gt 0 ]]; then
  echo "Ejecutando heuristico contra random con $RANDOM_MATCHES partidas por posicion"
  BENCHMARK_TARGET=heuristic \
  BENCHMARK_RUN_ID="$RUN_ID" \
  BENCHMARK_RANDOM_MATCHES="$RANDOM_MATCHES" \
  python Benchmarks/benchmark_vs_random.py

  cp benchmark_vs_random_resultados.csv "$RESULTS_DIR/heuristic_random.csv"
  cp benchmark_vs_random_resultados.json "$RESULTS_DIR/heuristic_random.json"
  cp benchmark_vs_random_partidas.csv "$RESULTS_DIR/heuristic_random_matches.csv"
else
  echo "Saltando heuristico contra random porque RANDOM_MATCHES=$RANDOM_MATCHES"
fi

if [[ "$STANDARD_MATCHES" -gt 0 ]]; then
  echo "Ejecutando heuristico contra agentes estandar con $STANDARD_MATCHES partidas por permutacion"
  BENCHMARK_TARGET=heuristic \
  BENCHMARK_RUN_ID="$RUN_ID" \
  BENCHMARK_STANDARD_MATCHES="$STANDARD_MATCHES" \
  python Benchmarks/benchmark_vs_agentes_estandar.py

  cp benchmark_vs_estandar_resultados.csv "$RESULTS_DIR/heuristic_standard.csv"
  cp benchmark_vs_estandar_resultados.json "$RESULTS_DIR/heuristic_standard.json"
  cp benchmark_vs_estandar_partidas.csv "$RESULTS_DIR/heuristic_standard_matches.csv"
else
  rm -f "$RESULTS_DIR/heuristic_standard.csv" "$RESULTS_DIR/heuristic_standard.json" "$RESULTS_DIR/heuristic_standard_matches.csv"
fi

echo "Resultados guardados en $RESULTS_DIR"
