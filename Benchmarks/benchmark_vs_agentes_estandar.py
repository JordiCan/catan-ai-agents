import os
import sys
import time
import concurrent.futures
import itertools
import csv
import json
import random
import traceback
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Benchmarks.helpers import (
    agent_metadata,
    benchmark_targets_from_env,
    configured_agent_class,
    load_agent_class,
)
from LLM.config import load_env
from Managers.GameDirector import GameDirector

BENCHMARK_AGENT_PATHS = [
    "Agents.RandomAgent.RandomAgent",
    "Agents.AdrianHerasAgent.AdrianHerasAgent",
    "Agents.AlexPastorAgent.AlexPastorAgent",
    "Agents.AlexPelochoJaimeAgent.AlexPelochoJaimeAgent",
    "Agents.CarlesZaidaAgent.CarlesZaidaAgent",
    "Agents.CrabisaAgent.CrabisaAgent",
    "Agents.EdoAgent.EdoAgent",
    "Agents.PabloAleixAlexAgent.PabloAleixAlexAgent",
    "Agents.SigmaAgent.SigmaAgent",
    "Agents.TristanAgent.TristanAgent",
]

AGENT_EXCLUDE_NAMES = {
    "HeuristicAgent",
    "HybridLLMAgent",
}

n_matches_per_permutation = 10 
porcentaje_workers = 0.95
random_seed_base = 54321

MATCH_FIELDNAMES = [
    "benchmark",
    "run_id",
    "agent_name",
    "provider",
    "model",
    "prompt",
    "permutation_index",
    "match_index",
    "seed",
    "position",
    "seat",
    "opponent_1",
    "opponent_2",
    "opponent_3",
    "opponent_key",
    "victory",
    "points",
    "rank",
    "winner_player",
    "winner_agent",
    "rounds_played",
    "last_turn",
    "final_points_J0",
    "final_points_J1",
    "final_points_J2",
    "final_points_J3",
    "error",
]


def final_state_from_trace(game_trace):
    last_round = max(game_trace["game"].keys(), key=lambda r: int(r.split("_")[-1]))
    last_turn = max(game_trace["game"][last_round].keys(), key=lambda t: int(t.split("_")[-1].lstrip("P")))
    victory_points = game_trace["game"][last_round][last_turn]["end_turn"]["victory_points"]
    rounds_played = int(last_round.split("_")[-1])
    return victory_points, rounds_played, last_turn


def write_match_results_csv(path, rows):
    with open(path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=MATCH_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def selected_agent_names():
    raw_value = os.getenv("BENCHMARK_STANDARD_AGENT_NAMES", "").strip()
    if not raw_value:
        return set()
    return {name.strip() for name in raw_value.split(",") if name.strip()}

def resolve_benchmark_agents():
    available = []
    missing = []
    seen = set()
    selected_names = selected_agent_names()

    for agent_path in BENCHMARK_AGENT_PATHS:
        try:
            agent_class = load_agent_class(agent_path)
            if selected_names and agent_class.__name__ not in selected_names:
                seen.add(agent_path)
                continue
            available.append(agent_class)
            seen.add(agent_path)
        except Exception:
            missing.append(agent_path)

    agents_dir = Path(PROJECT_ROOT) / "Agents"
    for file_path in sorted(agents_dir.glob("*Agent.py")):
        if file_path.name in {"HeuristicAgent.py", "HybridLLMAgent.py", "RandomAgent.py"}:
            continue
        module_name = file_path.stem
        agent_path = f"Agents.{module_name}.{module_name}"
        if agent_path in seen:
            continue
        try:
            agent_class = load_agent_class(agent_path)
            if agent_class.__name__ not in AGENT_EXCLUDE_NAMES:
                if selected_names and agent_class.__name__ not in selected_names:
                    continue
                available.append(agent_class)
        except Exception:
            missing.append(agent_path)
    return available, missing

def simulate_match(opponents, position, agente_alumno_clase, params=None, match_index=0, permutation_index=0):
    try:
        seed = random_seed_base + permutation_index * 1000000 + position * 100000 + match_index
        random.seed(seed)
        agente_alumno_class = configured_agent_class(agente_alumno_clase, params)
        metadata = agent_metadata(agente_alumno_clase, params)

        match_agents = list(opponents)
        match_agents.insert(position, agente_alumno_class)
        opponent_names = [opponent.__name__ for opponent in opponents]
        seat_agents = list(opponent_names)
        seat_agents.insert(position, metadata["agent_name"])

        game_director = GameDirector(agents=match_agents, max_rounds=200, store_trace=False)
        game_trace = game_director.game_start(print_outcome=False)

        victory_points, rounds_played, last_turn = final_state_from_trace(game_trace)
        agent_id = f"J{position}"
        points = int(victory_points[agent_id])
        winner = max(victory_points, key=lambda player: int(victory_points[player]))
        winner_index = int(winner.lstrip("J"))
        victory = 1 if winner == agent_id else 0

        ordenados = sorted(victory_points.items(), key=lambda item: int(item[1]), reverse=True)
        rank = 4  # Default rank if agent not found
        for idx, (jugador, _) in enumerate(ordenados, start=1):
            if jugador == agent_id:
                rank = idx
                break

        return {
            "benchmark": "standard",
            "run_id": os.getenv("BENCHMARK_RUN_ID", ""),
            "victory": victory,
            "points": points,
            "rank": rank,
            "position": position,
            "seat": f"J{position}",
            "seed": seed,
            "match_index": match_index,
            "permutation_index": permutation_index,
            "opponents": opponent_names,
            "opponent_1": opponent_names[0],
            "opponent_2": opponent_names[1],
            "opponent_3": opponent_names[2],
            "opponent_key": "|".join(opponent_names),
            "winner_player": winner,
            "winner_agent": seat_agents[winner_index],
            "rounds_played": rounds_played,
            "last_turn": last_turn,
            "final_points_J0": int(victory_points.get("J0", 0)),
            "final_points_J1": int(victory_points.get("J1", 0)),
            "final_points_J2": int(victory_points.get("J2", 0)),
            "final_points_J3": int(victory_points.get("J3", 0)),
            **metadata,
        }
    except Exception as e:
        print("Exception:", repr(e))
        print(traceback.format_exc())
        opponent_names = [getattr(opponent, "__name__", str(opponent)) for opponent in opponents]
        metadata = agent_metadata(agente_alumno_clase, params)
        return {
            "benchmark": "standard",
            "run_id": os.getenv("BENCHMARK_RUN_ID", ""),
            "victory": 0,
            "points": 0,
            "rank": 4,
            "position": position,
            "seat": f"J{position}",
            "seed": random_seed_base + permutation_index * 1000000 + position * 100000 + match_index,
            "match_index": match_index,
            "permutation_index": permutation_index,
            "opponents": opponent_names,
            "opponent_1": opponent_names[0] if len(opponent_names) > 0 else "",
            "opponent_2": opponent_names[1] if len(opponent_names) > 1 else "",
            "opponent_3": opponent_names[2] if len(opponent_names) > 2 else "",
            "opponent_key": "|".join(opponent_names),
            "winner_player": "",
            "winner_agent": "",
            "rounds_played": 0,
            "last_turn": "",
            "final_points_J0": 0,
            "final_points_J1": 0,
            "final_points_J2": 0,
            "final_points_J3": 0,
            **metadata,
            "error": repr(e),
        }

if __name__ == '__main__':
    quick_mode = os.getenv("BENCHMARK_QUICK", "0") == "1"
    load_env()
    agentes_a_evaluar = benchmark_targets_from_env()
    if quick_mode:
        n_matches_per_permutation = 1
    n_matches_per_permutation = int(os.getenv("BENCHMARK_STANDARD_MATCHES", str(n_matches_per_permutation)))
    benchmark_agents, missing_agents = resolve_benchmark_agents()
    if missing_agents:
        print("Aviso: faltan agentes estándar y se omiten del benchmark:")
        for agent_path in missing_agents:
            print(f" - {agent_path}")

    if len(benchmark_agents) < 3:
        raise RuntimeError("No hay suficientes agentes benchmark disponibles para generar oponentes")

    results = {agent+str(params) if params is not None else agent: {'wins': 0, 'points': 0, 'rank_sum': 0} for agent, params in agentes_a_evaluar}

    total_workers = os.cpu_count() or 1
    worker_fraction = float(os.getenv("BENCHMARK_WORKER_FRACTION", str(porcentaje_workers)))
    explicit_workers = os.getenv("BENCHMARK_WORKERS")
    if explicit_workers is not None:
        workers_a_utilizar = max(1, int(explicit_workers))
    else:
        workers_a_utilizar = max(1, int(total_workers * worker_fraction))
    print(f"Workers a utilizar: {workers_a_utilizar}")

    start_time = time.time()

    permutations = list(itertools.permutations(benchmark_agents, 3))
    max_permutations = int(os.getenv("BENCHMARK_STANDARD_MAX_PERMUTATIONS", "0"))
    if quick_mode and max_permutations == 0:
        max_permutations = 8
    if max_permutations > 0:
        permutations = permutations[:max_permutations]
    total_matches = len(agentes_a_evaluar) * len(permutations) * 4 * n_matches_per_permutation
    coste_medio_partida_segundos = 0.004
    print(f"Total de partidas a simular: {total_matches}. Tiempo estimado: {total_matches * coste_medio_partida_segundos / 60:.2f} minutos")

    matches_done = 0
    batch_size = 10000
    futures_batch = []
    resumen_csv = []
    all_match_results = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers_a_utilizar) as executor:
        def task_generator():
            for agente_path, params in agentes_a_evaluar:
                agente_cls = load_agent_class(agente_path)
                for permutation_index, perm in enumerate(permutations):
                    for pos in range(4):
                        for match_index in range(n_matches_per_permutation):
                            yield (list(perm), pos, agente_cls, params, agente_path, match_index, permutation_index)


        for perm, pos, agente_cls, params, agente_path, match_index, permutation_index in task_generator():
            fut = executor.submit(
                simulate_match,
                perm,
                pos,
                agente_cls,
                params=params,
                match_index=match_index,
                permutation_index=permutation_index,
            )
            futures_batch.append((fut, agente_path+str(params) if params is not None else agente_path))


            if len(futures_batch) >= batch_size:
                futures_dict = {fut: agente_alumno for fut, agente_alumno in futures_batch}
                for fut in concurrent.futures.as_completed(futures_dict):
                    result = fut.result()
                    victory = result["victory"]
                    points = result["points"]
                    rank = result["rank"]
                    agent = futures_dict[fut]
                    results[agent]['wins'] += victory
                    results[agent]['points'] += points
                    results[agent]['rank_sum'] += rank
                    matches_done += 1
                    all_match_results.append(result)
                    if matches_done % 10000 == 0 or matches_done == total_matches:
                        print(f"Progreso: {matches_done}/{total_matches} partidas completadas ({matches_done/total_matches:.2%})")
                futures_batch = []

        if futures_batch:
            futures_dict = {fut: agente_alumno for fut, agente_alumno in futures_batch}
            for fut in concurrent.futures.as_completed(futures_dict):
                result = fut.result()
                victory = result["victory"]
                points = result["points"]
                rank = result["rank"]
                agent = futures_dict[fut]
                results[agent]['wins'] += victory
                results[agent]['points'] += points
                results[agent]['rank_sum'] += rank
                matches_done += 1
                all_match_results.append(result)
                if matches_done % 10000 == 0 or matches_done == total_matches:
                    print(f"Progreso: {matches_done}/{total_matches} partidas completadas ({matches_done/total_matches:.2%})")

    partidas_por_agente = len(permutations) * 4 * n_matches_per_permutation
    print("\nResultados ordenados por ratio de victorias:")

    resumen = []
    metadata_by_name = {
        (agent + str(params) if params is not None else agent): agent_metadata(load_agent_class(agent), params)
        for agent, params in agentes_a_evaluar
    }
    for agente, stats in results.items():
        nombre = agente
        wins = stats['wins']
        points = stats['points']
        rank_sum = stats['rank_sum']
        ratio = wins / partidas_por_agente
        avg_points = points / partidas_por_agente
        puesto_medio = rank_sum / partidas_por_agente
        metadata = metadata_by_name.get(nombre, {"provider": "heuristic", "model": "", "prompt": ""})
        provider = metadata["provider"]
        model = metadata["model"]
        prompt = metadata["prompt"]
        resumen.append((nombre, provider, model, prompt, wins, points, partidas_por_agente, ratio, avg_points, puesto_medio))

    resumen.sort(key=lambda x: x[7], reverse=True)

    for nombre, provider, model, prompt, wins, points, total, ratio, avg_points, puesto_medio in resumen:
        print(f"{nombre}: {wins} victorias, {points} puntos en {total} partidas — "
              f"Ratio: {ratio:.2%}, Media puntos: {avg_points:.2f}, Puesto medio: {puesto_medio:.2f}")
        resumen_csv.append([nombre, provider, model, prompt, wins, points, total, f"{ratio:.4f}", f"{avg_points:.2f}", f"{puesto_medio:.2f}"])

    # Guardar CSV
    csv_filename = "benchmark_vs_estandar_resultados.csv"
    with open(csv_filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Agente", "Provider", "Model", "Prompt", "Victorias", "Puntos", "Partidas", "Ratio Victorias", "Media Puntos", "Puesto Medio"])
        writer.writerows(resumen_csv)

    print(f"\n Resultados guardados en: {csv_filename}")

    json_filename = "benchmark_vs_estandar_resultados.json"
    with open(json_filename, mode="w", encoding="utf-8") as jsonfile:
        json.dump(
            {
                "missing_benchmark_agents": missing_agents,
                "available_benchmark_agents": [agent.__name__ for agent in benchmark_agents],
                "results": all_match_results,
            },
            jsonfile,
            indent=2,
            ensure_ascii=True,
        )
    print(f"Resultados detallados guardados en: {json_filename}")

    matches_csv_filename = "benchmark_vs_estandar_partidas.csv"
    write_match_results_csv(matches_csv_filename, all_match_results)
    print(f"Resultados por partida guardados en: {matches_csv_filename}")

    end_time = time.time()
    horas, resto = divmod(end_time - start_time, 3600)
    minutos, segundos = divmod(resto, 60)
    print(f"\n Tiempo total: {int(horas)}h {int(minutos)}m {int(segundos)}s")
