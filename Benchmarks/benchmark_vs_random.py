import os
import sys
import time
import concurrent.futures
import csv
import json
import random
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Agents.RandomAgent import RandomAgent as ra
from Benchmarks.helpers import (
    agent_metadata,
    benchmark_targets_from_env,
    configured_agent_class,
    load_agent_class,
)
from LLM.config import load_env
from Managers.GameDirector import GameDirector

n_matches = 1000
porcentaje_workers = 0.95
random_seed_base = 12345

MATCH_FIELDNAMES = [
    "benchmark",
    "run_id",
    "agent_name",
    "provider",
    "model",
    "prompt",
    "match_index",
    "seed",
    "position",
    "seat",
    "opponent_1",
    "opponent_2",
    "opponent_3",
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


def simulate_match(position, agente_alumno_clase, params=None, match_index=0):
    try:
        seed = random_seed_base + position * 100000 + match_index
        random.seed(seed)
        agente_final = configured_agent_class(agente_alumno_clase, params)
        metadata = agent_metadata(agente_alumno_clase, params)

        match_agents = [ra, ra, ra]
        match_agents.insert(position, agente_final)
        seat_agents = ["RandomAgent", "RandomAgent", "RandomAgent", "RandomAgent"]
        seat_agents[position] = metadata["agent_name"]

        game_director = GameDirector(agents=match_agents, max_rounds=200, store_trace=False)
        game_trace = game_director.game_start(print_outcome=False)

        victory_points, rounds_played, last_turn = final_state_from_trace(game_trace)
        agent_id = f"J{position}"
        points = int(victory_points[agent_id])
        winner = max(victory_points, key=lambda player: int(victory_points[player]))
        winner_index = int(winner.lstrip("J"))
        victory = 1 if winner == agent_id else 0

        ordenados = sorted(victory_points.items(), key=lambda item: int(item[1]), reverse=True)
        rank = 4  # Default rank if player not found
        for idx, (jugador, _) in enumerate(ordenados, start=1):
            if jugador == agent_id:
                rank = idx
                break

        return {
            "benchmark": "random",
            "run_id": os.getenv("BENCHMARK_RUN_ID", ""),
            "victory": victory,
            "points": points,
            "rank": rank,
            "position": position,
            "seat": f"J{position}",
            "seed": seed,
            "match_index": match_index,
            "opponent_1": "RandomAgent",
            "opponent_2": "RandomAgent",
            "opponent_3": "RandomAgent",
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
        print("\n=== EXCEPCIÓN EN simulate_match ===")
        print("Agente clase:", agente_alumno_clase, "name:", getattr(agente_alumno_clase, "__name__", None))
        print("Posición:", position, "params type:", type(params), "params:", params)
        print("Exception:", repr(e))
        print(traceback.format_exc())
        metadata = agent_metadata(agente_alumno_clase, params)
        return {
            "benchmark": "random",
            "run_id": os.getenv("BENCHMARK_RUN_ID", ""),
            "victory": 0,
            "points": 0,
            "rank": 4,
            "position": position,
            "seat": f"J{position}",
            "seed": random_seed_base + position * 100000 + match_index,
            "match_index": match_index,
            "opponent_1": "RandomAgent",
            "opponent_2": "RandomAgent",
            "opponent_3": "RandomAgent",
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
    load_env()
    agentes_a_evaluar = benchmark_targets_from_env()
    if os.getenv("BENCHMARK_QUICK", "0") == "1":
        n_matches = 5
    n_matches = int(os.getenv("BENCHMARK_RANDOM_MATCHES", str(n_matches)))
    if n_matches <= 0:
        raise SystemExit("BENCHMARK_RANDOM_MATCHES debe ser mayor que 0 para benchmark_vs_random.py")
    total_workers = os.cpu_count() or 1
    worker_fraction = float(os.getenv("BENCHMARK_WORKER_FRACTION", str(porcentaje_workers)))
    explicit_workers = os.getenv("BENCHMARK_WORKERS")
    if explicit_workers is not None:
        workers_a_utilizar = max(1, int(explicit_workers))
    else:
        workers_a_utilizar = max(1, int(total_workers * worker_fraction))
    print(f"Workers a utilizar: {workers_a_utilizar}\n")

    start_time = time.time()
    resumen_csv = []
    all_match_results = []

    for ruta_agente, params_agente in agentes_a_evaluar:
        agente_alumno = load_agent_class(ruta_agente)
        agent_name = agente_alumno.__name__
        metadata = agent_metadata(agente_alumno, params_agente)
        print(f"\n==== Evaluando agente: {agent_name} ====\n")

        partial_start_time = time.time()
        position_results = {pos: 0 for pos in range(4)}
        total_wins = 0
        total_points = 0
        total_rank = 0

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers_a_utilizar) as executor:
            for pos in range(4):
                futures = [
                    executor.submit(simulate_match, pos, agente_alumno, params_agente, match_index)
                    for match_index in range(n_matches)
                ]
                for f in concurrent.futures.as_completed(futures):
                    result = f.result()
                    victory = result["victory"]
                    points = result["points"]
                    rank = result["rank"]
                    position_results[pos] += victory
                    total_wins += victory
                    total_points += points
                    total_rank += rank
                    all_match_results.append(result)

        for pos in range(4):
            wins = position_results[pos]
            percentage = 100 * wins / n_matches
            print(f"- Posición {pos+1}: {wins} victorias de {n_matches} partidas ({percentage:.2f}%)")

        total_partidas = n_matches * 4
        ratio_victorias = total_wins / total_partidas
        media_puntos = total_points / total_partidas
        puesto_medio = total_rank / total_partidas

        print(f"\nTotal para {agent_name}: {total_wins} victorias de {total_partidas} partidas ({ratio_victorias:.2%})")
        print(f"Media de puntos: {media_puntos:.2f}")
        print(f"Puesto medio: {puesto_medio:.2f}")

        resumen_csv.append([
            agent_name,
            metadata["provider"],
            metadata["model"],
            metadata["prompt"],
            total_wins,
            total_points,
            total_partidas,
            f"{ratio_victorias:.4f}",
            f"{media_puntos:.2f}",
            f"{puesto_medio:.2f}",
        ])

        partial_end_time = time.time()
        horas, resto = divmod(partial_end_time - partial_start_time, 3600)
        minutos, segundos = divmod(resto, 60)
        print(f"Tiempo parcial: {int(horas)}h {int(minutos)}m {int(segundos)}s\n")

    # Guardar CSV
    csv_filename = "benchmark_vs_random_resultados.csv"
    with open(csv_filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Agente", "Provider", "Model", "Prompt", "Victorias", "Puntos", "Partidas", "Ratio Victorias", "Media Puntos", "Puesto Medio"])
        for row in resumen_csv:
            writer.writerow(row)

    print(f"\nResultados guardados en: {csv_filename}")

    json_filename = "benchmark_vs_random_resultados.json"
    with open(json_filename, mode="w", encoding="utf-8") as jsonfile:
        json.dump(all_match_results, jsonfile, indent=2, ensure_ascii=True)
    print(f"Resultados detallados guardados en: {json_filename}")

    matches_csv_filename = "benchmark_vs_random_partidas.csv"
    write_match_results_csv(matches_csv_filename, all_match_results)
    print(f"Resultados por partida guardados en: {matches_csv_filename}")

    end_time = time.time()
    horas, resto = divmod(end_time - start_time, 3600)
    minutos, segundos = divmod(resto, 60)
    print(f"\nTiempo total: {int(horas)}h {int(minutos)}m {int(segundos)}s\n")
