import os

from Agents.HeuristicAgent import HeuristicAgent
from LLM.client import CatanLLMClient
from LLM.config import env_bool, load_env
from LLM.logger import ExperimentLogger
from Strategy.HeuristicEvaluator import BUILD_PRIORITY


class HybridLLMAgent(HeuristicAgent):
    """Heuristic agent with pluggable LLM decisions and safe fallback."""

    def __init__(
        self,
        agent_id,
        provider_name=None,
        model_name=None,
        prompt_name=None,
        timeout_seconds=None,
        llm_enabled=None,
        log_path=None,
    ):
        super().__init__(agent_id)
        load_env()
        resolved_timeout = timeout_seconds or int(os.getenv("CATAN_LLM_TIMEOUT_SECONDS", "20"))
        logger = ExperimentLogger(log_path or os.getenv("CATAN_LLM_LOG_PATH"))
        self.llm_client = CatanLLMClient(
            provider_name=provider_name,
            model_name=model_name,
            prompt_name=prompt_name,
            timeout_seconds=resolved_timeout,
            logger=logger,
        )
        if llm_enabled is None:
            self.llm_enabled = env_bool("CATAN_LLM_ENABLED", default=True)
        else:
            self.llm_enabled = bool(llm_enabled)

    def _candidate_start_actions(self, board):
        valid_nodes = board.valid_starting_nodes()
        candidates = []
        for node_id in valid_nodes:
            road_to = self.evaluator.choose_starting_road(board, node_id, self.id)
            if road_to is not None:
                candidates.append(
                    {
                        "node_id": node_id,
                        "road_to": road_to,
                        "score": round(self.evaluator.score_node(board, node_id), 2),
                    }
                )
        return sorted(candidates, key=lambda item: item["score"], reverse=True)[:5]

    def _candidate_build_actions(self, board):
        candidates = []

        city = self.evaluator.choose_best_city_node(board, self.id)
        if city is not None:
            candidates.append(
                {
                    "building": "city",
                    "node_id": city,
                    "road_to": None,
                    "score": round(self.evaluator.score_node(board, city), 2),
                }
            )

        town = self.evaluator.choose_best_town_node(board, self.id)
        if town is not None:
            candidates.append(
                {
                    "building": "town",
                    "node_id": town,
                    "road_to": None,
                    "score": round(self.evaluator.score_node(board, town), 2),
                }
            )

        road = self.evaluator.choose_best_road(board, self.id)
        if road is not None:
            candidates.append(
                {
                    "building": "road",
                    "node_id": road["starting_node"],
                    "road_to": road["finishing_node"],
                    "score": round(
                        self.evaluator.score_road_extension(
                            board,
                            self.id,
                            road["starting_node"],
                            road["finishing_node"],
                        ),
                        2,
                    ),
                }
            )

        candidates.append({"building": "card", "node_id": None, "road_to": None, "score": 0.0})
        return sorted(
            candidates,
            key=lambda item: (BUILD_PRIORITY.index(item["building"]) if item["building"] in BUILD_PRIORITY else 99, -item["score"]),
        )

    def _serialize_common_state(self):
        summary = self.evaluator.summarize_player_state(self.board, self.id)
        return {
            "player_id": self.id,
            "resources": self.hand.resources.__to_object__(),
            "towns": summary["towns"],
            "cities": summary["cities"],
            "roads": summary["roads"],
        }

    def _serialize_start_state(self):
        data = self._serialize_common_state()
        data["valid_nodes"] = self.board.valid_starting_nodes()
        data["node_scores"] = {
            str(node_id): round(self.evaluator.score_node(self.board, node_id), 2)
            for node_id in self.board.valid_starting_nodes()
        }
        return data

    def _serialize_build_state(self):
        data = self._serialize_common_state()
        data["valid_city_nodes"] = self.board.valid_city_nodes(self.id)
        data["valid_town_nodes"] = self.board.valid_town_nodes(self.id)
        data["valid_road_count"] = len(self.board.valid_road_nodes(self.id))
        return data

    def on_game_start(self, board_instance):
        self.board = board_instance
        heuristic = super().on_game_start(board_instance)
        if not self.llm_enabled:
            return heuristic

        record = self.llm_client.decide(
            "on_game_start",
            self._serialize_start_state(),
            self._candidate_start_actions(self.board),
            fallback_hint={"node_id": heuristic[0], "road_to": heuristic[1]},
        )
        if record.parsed_response is not None:
            return record.parsed_response["node_id"], record.parsed_response["road_to"]
        return heuristic

    def on_build_phase(self, board_instance):
        self.board = board_instance
        heuristic = super().on_build_phase(board_instance)
        if not self.llm_enabled or heuristic is None:
            return heuristic

        record = self.llm_client.decide(
            "on_build_phase",
            self._serialize_build_state(),
            self._candidate_build_actions(self.board),
            fallback_hint=heuristic,
        )
        if record.parsed_response is not None:
            return record.parsed_response
        return heuristic
