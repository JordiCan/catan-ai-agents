import argparse
import json
import os
import random
from pathlib import Path

from Agents.HeuristicAgent import HeuristicAgent
from Agents.HybridLLMAgent import HybridLLMAgent
from Agents.RandomAgent import RandomAgent
from LLM.config import load_env
from Managers.GameDirector import GameDirector


def summarize_game(game_director):
    players = game_director.game_manager.get_players()
    summary = {
        "winner": max(players, key=lambda player: player["victory_points"])["id"],
        "victory_points": {f"P{player['id']}": player["victory_points"] for player in players},
        "largest_army_player": game_director.game_manager.largest_army_player.get("id")
        if game_director.game_manager.largest_army_player
        else None,
        "longest_road_player": game_director.game_manager.longest_road["player"],
        "rounds_played": game_director.game_manager.get_round(),
    }
    return summary


def play_games(agent_classes, games=5, max_rounds=200, seed=0, store_trace=False):
    results = []
    for game_index in range(games):
        random.seed(seed + game_index)
        director = GameDirector(agents=agent_classes, max_rounds=max_rounds, store_trace=store_trace)
        director.game_start(game_index, False)
        summary = summarize_game(director)
        summary["seed"] = seed + game_index
        results.append(summary)
    return results


def run_heuristic_benchmark(games=20, max_rounds=200, seed=0):
    return play_games((HeuristicAgent, RandomAgent, RandomAgent, RandomAgent), games=games, max_rounds=max_rounds, seed=seed)


def run_llm_probe(games=5, max_rounds=150, seed=0):
    return play_games((HybridLLMAgent, RandomAgent, RandomAgent, RandomAgent), games=games, max_rounds=max_rounds, seed=seed)


def save_results(results, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=True), encoding="utf-8")


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Run Catan agent experiments")
    parser.add_argument("--mode", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", default="artifacts/experiment_results.json")
    return parser


def main():
    load_env()
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.mode == "heuristic":
        results = run_heuristic_benchmark(games=args.games, max_rounds=args.max_rounds, seed=args.seed)
    else:
        os.environ.setdefault("CATAN_LLM_ENABLED", "1")
        os.environ.setdefault("CATAN_LLM_PROVIDER", "mock")
        results = run_llm_probe(games=args.games, max_rounds=args.max_rounds, seed=args.seed)

    save_results(results, args.output)
    print(json.dumps(results, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
