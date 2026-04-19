# Trabajo de Agentes para Catan

Este repositorio contiene mi trabajo sobre agentes inteligentes para Catan, desarrollado a partir del codebase base proporcionado por el profesor para la asignatura. La base original incluia el simulador, la estructura general de agentes y los componentes necesarios para ejecutar partidas y benchmarks. A partir de ese punto, el trabajo realizado aqui consiste en una adaptacion y ampliacion de ese codebase docente para cubrir la practica de heuristicas y modelos de lenguaje.

## Referencia al codebase original

El proyecto parte del simulador y la estructura inicial entregados por el profesor como material base de la practica. Sobre esa base se han mantenido los componentes nucleares del juego y se han añadido nuevas piezas orientadas al desarrollo experimental del trabajo.

Repositorio original de referencia:

- [PyCatan](https://github.com/jaumejordan/PyCatan.git)

Si en la memoria final necesitas una formulacion breve, una forma correcta de citarlo seria:

> Trabajo desarrollado a partir del codebase base del simulador de Catan proporcionado por el profesor para la practica, tomando como referencia el repositorio PyCatan: https://github.com/jaumejordan/PyCatan.git

## Cambios realizados sobre la base original

Los cambios principales introducidos en esta adaptacion son estos:

- Desarrollo de un agente heuristico propio en [HeuristicAgent.py](/root/catan-ai-agents/Agents/HeuristicAgent.py).
- Extraccion de la logica de evaluacion estrategica a [HeuristicEvaluator.py](/root/catan-ai-agents/Strategy/HeuristicEvaluator.py).
- Integracion de un agente hibrido con soporte para LLM en [HybridLLMAgent.py](/root/catan-ai-agents/Agents/HybridLLMAgent.py).
- Capa unificada para proveedores LLM en `LLM/`, con soporte para `Poligpt`, `Ollama`, `Bedrock` y modo `mock`.
- Sistema de prompts versionados en `LLM/prompts/`.
- Adaptacion de benchmarks para evaluar el agente contra `RandomAgent` y contra los agentes estandar disponibles del repositorio.
- Scripts de analisis para resumir resultados y generar graficas a partir de los experimentos.
- Ajustes de robustez y compatibilidad en partes del motor para facilitar la ejecucion de pruebas y la reproducibilidad.

## Estructura relevante del trabajo

- [Agents/HeuristicAgent.py](/root/catan-ai-agents/Agents/HeuristicAgent.py): agente heuristico principal.
- [Agents/HybridLLMAgent.py](/root/catan-ai-agents/Agents/HybridLLMAgent.py): agente hibrido con fallback heuristico.
- [Strategy/HeuristicEvaluator.py](/root/catan-ai-agents/Strategy/HeuristicEvaluator.py): funciones de evaluacion de nodos, carreteras, comercio y robo.
- [LLM/providers.py](/root/catan-ai-agents/LLM/providers.py): integracion con proveedores de modelos.
- [Benchmarks/benchmark_vs_random.py](/root/catan-ai-agents/Benchmarks/benchmark_vs_random.py): benchmark contra random.
- [Benchmarks/benchmark_vs_agentes_estandar.py](/root/catan-ai-agents/Benchmarks/benchmark_vs_agentes_estandar.py): benchmark contra agentes estandar disponibles.
- [Experiments/analyze_results.py](/root/catan-ai-agents/Experiments/analyze_results.py): analisis de resultados y generacion de graficas.
- [Instrucciones.txt](/root/catan-ai-agents/Instrucciones.txt): enunciado de la practica.

## Agentes implementados para el trabajo

### Agente heuristico

El agente heuristico implementa reglas explicitas para:

- colocacion inicial
- priorizacion de construcciones
- decision de comercio con banco o puertos
- movimiento del ladron
- uso de algunas cartas de desarrollo

La idea central es valorar produccion esperada, diversidad de recursos, acceso a puertos y expansion futura de la red de carreteras.

### Agente hibrido con LLM

El agente hibrido reutiliza la base heuristica, pero consulta un modelo para algunas decisiones concretas:

- `on_game_start`
- `on_build_phase`

Si la respuesta del modelo no es valida, hay timeout o el proveedor no esta disponible, el agente vuelve automaticamente a la politica heuristica.

## Instalacion

```bash
python -m pip install -r requirements.txt
```

## Configuracion de modelos

Variables principales:

- `CATAN_LLM_ENABLED=1`
- `CATAN_LLM_PROVIDER=mock|poligpt|ollama|bedrock`
- `CATAN_LLM_MODEL=<modelo>`
- `CATAN_LLM_PROMPT=direct_short|strict_json|guided_compact`
- `CATAN_LLM_LOG_PATH=artifacts/llm_decisions.jsonl`
- `CATAN_LLM_TIMEOUT_SECONDS=20`

Configuracion especifica:

- `POLIGPT_KEY` para Poligpt
- `OLLAMA_BASE_URL` para Ollama
- credenciales AWS estandar y `AWS_DEFAULT_REGION` para Bedrock

## Ejecucion interactiva

```bash
python main.py
```

Ejemplos de agentes:

- `HeuristicAgent.HeuristicAgent`
- `HybridLLMAgent.HybridLLMAgent`
- `RandomAgent.RandomAgent`

## Pruebas recomendadas para la practica

### 0. Scripts simples de ejecucion

Heuristico:

```bash
./scripts/run_heuristic.sh 20
```

LLM con Poligpt:

```bash
./scripts/run_llm.sh poligpt 10 strict_json
```

LLM con Ollama:

```bash
LLM_PROVIDER=ollama ./scripts/run_llm.sh llama3.2:3b 10 strict_json
```

Todos los resultados quedan guardados en `results/`.
Si quieres incluir benchmark contra agentes estandar, añade un cuarto parametro al script LLM y un segundo parametro al heuristico.

Si quieres ejecutar solo contra agentes estandar con una prueba corta:

```bash
./scripts/run_llm_standard.sh poligpt 1 strict_json
```

### 1. Agente heuristico contra random

```bash
BENCHMARK_TARGET=heuristic BENCHMARK_RANDOM_MATCHES=20 python Benchmarks/benchmark_vs_random.py
```

### 2. Poligpt

```bash
CATAN_LLM_PROVIDER=poligpt CATAN_LLM_MODEL=openai/poligpt CATAN_LLM_LOG_PATH=artifacts/poligpt_log.jsonl BENCHMARK_TARGET=poligpt BENCHMARK_RANDOM_MATCHES=10 python Benchmarks/benchmark_vs_random.py
```

Sweep de prompts con Poligpt:

```bash
MATRIX_PROVIDER=poligpt MATRIX_MODELS=poligpt MATRIX_PROMPTS=direct_short,strict_json,guided_compact python Benchmarks/benchmark_llm_matrix.py
```

Sweep de modelos de texto utiles en Poligpt:

```bash
MATRIX_PROVIDER=poligpt MATRIX_MODELS=poligpt,poligpt2,qwen,phi4,gemma,llama-mini MATRIX_PROMPTS=strict_json python Benchmarks/benchmark_llm_matrix.py
```

### 3. Ollama

```bash
CATAN_LLM_PROVIDER=ollama CATAN_LLM_MODEL=ollama/llama3.2:3b CATAN_LLM_LOG_PATH=artifacts/ollama_log.jsonl BENCHMARK_TARGET=ollama BENCHMARK_RANDOM_MATCHES=10 python Benchmarks/benchmark_vs_random.py
```

Sweep de modelos locales recomendados:

```bash
MATRIX_PROVIDER=ollama MATRIX_MODELS=llama3.2:3b,qwen3:4b,gemma3:4b,phi4-mini:3.8b MATRIX_PROMPTS=strict_json python Benchmarks/benchmark_llm_matrix.py
```

### 4. Benchmark estandar

```bash
BENCHMARK_TARGET=heuristic BENCHMARK_STANDARD_MATCHES=5 python Benchmarks/benchmark_vs_agentes_estandar.py
```

### 5. Comprobaciones rapidas

```bash
BENCHMARK_QUICK=1 BENCHMARK_TARGET=mock python Benchmarks/benchmark_vs_random.py
```

```bash
BENCHMARK_QUICK=1 BENCHMARK_TARGET=poligpt python Benchmarks/benchmark_vs_random.py
```

## Analisis de resultados

Para regenerar tablas y macros de la memoria a partir de los CSV de `results/`:

```bash
python memoria/generate_report_data.py
```

Y para compilar la memoria:

```bash
cd memoria
pdflatex main.tex
pdflatex main.tex
```

Para generar estadisticas y graficas:

```bash
python -m Experiments.analyze_results artifacts/heuristic.json --output-dir artifacts/analysis_heuristic
```

O comparando varios resultados:

```bash
python -m Experiments.analyze_results artifacts/heuristic.json artifacts/llm_poligpt.json --labels heuristic poligpt --output-dir artifacts/analysis_compare
```

El analisis genera:

- resumen JSON
- tasa de victorias
- puntos medios
- rondas medias
- margen respecto al segundo clasificado
- distribuciones de puntos y duracion

## Visualizacion

1. Abre [index.html](/root/catan-ai-agents/Visualizer/index.html).
2. Carga una traza JSON desde el selector de archivo.

<img src="assets/visualizer_screenshot.png" width="900" alt="Screenshot of the visualizer">

## Nota final

Este repositorio no pretende reemplazar el codebase base del profesor, sino documentar y organizar la adaptacion realizada para el trabajo practico. La contribucion principal aqui esta en el diseño del agente heuristico, la integracion experimental con LLM, la adaptacion de benchmarks y el soporte para analizar resultados de forma reproducible.
