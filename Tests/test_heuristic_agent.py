from Agents.HeuristicAgent import HeuristicAgent
from Classes.Board import Board
from Classes.Constants import BuildConstants, MaterialConstants


class TestHeuristicAgent:
    def test_prefers_high_value_start(self):
        agent = HeuristicAgent(0)
        board = Board()

        node_id, road_to = agent.on_game_start(board)

        assert node_id in board.valid_starting_nodes()
        assert road_to in board.nodes[node_id]["adjacent"]
        high_value_score = agent.evaluator.score_node(board, node_id)
        assert high_value_score >= 10

    def test_build_phase_prioritizes_city(self):
        agent = HeuristicAgent(0)
        board = Board()
        board.nodes[0]["player"] = 0
        agent.hand.add_material([MaterialConstants.CEREAL, MaterialConstants.MINERAL], 3)

        response = agent.on_build_phase(board)

        assert response["building"] == BuildConstants.CITY
        assert response["node_id"] == 0

    def test_commerce_phase_uses_bank_trade_when_missing_key_resource(self):
        agent = HeuristicAgent(0)
        board = Board()
        board.nodes[0]["player"] = 0
        board.nodes[0]["roads"].append({"player_id": 0, "node_id": 1})
        board.nodes[1]["roads"].append({"player_id": 0, "node_id": 0})
        agent.board = board
        agent.hand.add_material(MaterialConstants.WOOD, 4)

        response = agent.on_commerce_phase()

        assert response is not None
        assert response["gives"] == MaterialConstants.WOOD
        assert response["receives"] != MaterialConstants.WOOD
