import os

from Agents.HybridLLMAgent import HybridLLMAgent
from Classes.Board import Board
from Classes.Constants import BuildConstants, MaterialConstants
from LLM.parser import parse_json_response, validate_build_response


class TestLLMIntegration:
    def setup_method(self):
        os.environ["CATAN_LLM_ENABLED"] = "1"
        os.environ["CATAN_LLM_PROVIDER"] = "mock"
        os.environ["CATAN_LLM_PROMPT"] = "strict_json"

    def test_parse_and_validate_build_response(self):
        parsed = parse_json_response('{"building": "road", "node_id": 0, "road_to": 1}')
        validated = validate_build_response(parsed)
        assert validated["building"] == BuildConstants.ROAD
        assert validated["node_id"] == 0
        assert validated["road_to"] == 1

    def test_hybrid_agent_uses_mock_decision_for_start(self):
        os.environ["CATAN_LLM_MODEL"] = "mock-rule"
        agent = HybridLLMAgent(0)
        board = Board()

        node_id, road_to = agent.on_game_start(board)

        assert node_id in board.valid_starting_nodes()
        assert road_to in board.nodes[node_id]["adjacent"]

    def test_hybrid_agent_falls_back_when_provider_returns_invalid_json(self):
        os.environ["CATAN_LLM_ENABLED"] = "1"
        agent = HybridLLMAgent(0)
        agent.llm_client.provider.generate = lambda *args, **kwargs: {
            "text": "not-json",
            "latency_ms": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
        }

        board = Board()
        board.nodes[0]["player"] = 0
        agent.hand.add_material([MaterialConstants.CEREAL, MaterialConstants.MINERAL], 3)
        response = agent.on_build_phase(board)

        assert response["building"] == BuildConstants.CITY
