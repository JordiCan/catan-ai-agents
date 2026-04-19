from Classes.Constants import BuildConstants, DevelopmentCardConstants, MaterialConstants
from Interfaces.AgentInterface import AgentInterface
from Strategy.HeuristicEvaluator import HeuristicEvaluator


class HeuristicAgent(AgentInterface):
    """Reference heuristic agent for the coursework deliverable."""

    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.evaluator = HeuristicEvaluator()

    def on_trade_offer(self, board_instance, offer, player_id=int):
        incoming = offer.gives
        outgoing = offer.receives
        if incoming.is_empty():
            return False
        if outgoing.check_negative() or incoming.check_negative():
            return False
        return self.hand.resources.has_more(outgoing) and sum(incoming) >= sum(outgoing)

    def on_turn_start(self):
        knight_cards = self.development_cards_hand.find_card_by_effect(DevelopmentCardConstants.KNIGHT_EFFECT)
        if knight_cards:
            return knight_cards[0]
        return None

    def on_having_more_than_7_materials_when_thief_is_called(self):
        priorities = [
            MaterialConstants.WOOL,
            MaterialConstants.WOOD,
            MaterialConstants.CLAY,
            MaterialConstants.CEREAL,
            MaterialConstants.MINERAL,
        ]
        while self.hand.get_total() > 7:
            for material_id in priorities:
                if self.hand.get_from_id(material_id) > 0 and self.hand.get_total() > 7:
                    self.hand.remove_material(material_id, 1)
        return self.hand

    def on_moving_thief(self):
        return self.evaluator.choose_thief_target(self.board, self.id)

    def on_turn_end(self):
        victory_cards = self.development_cards_hand.find_card_by_effect(DevelopmentCardConstants.VICTORY_POINT_EFFECT)
        if victory_cards:
            return victory_cards[0]
        return None

    def on_commerce_phase(self):
        return self.evaluator.choose_bank_trade(self.board, self.id, self.hand)

    def on_build_phase(self, board_instance):
        self.board = board_instance
        return self.evaluator.choose_build_action(self.board, self.id, self.hand.resources)

    def on_game_start(self, board_instance):
        self.board = board_instance
        node_id = self.evaluator.choose_starting_settlement(self.board)
        if node_id is None:
            return super().on_game_start(board_instance)
        road_to = self.evaluator.choose_starting_road(self.board, node_id, self.id)
        if road_to is None:
            return super().on_game_start(board_instance)
        return node_id, road_to

    def on_monopoly_card_use(self):
        ranked = sorted(range(5), key=lambda material_id: self.hand.get_from_id(material_id))
        return ranked[0]

    def on_road_building_card_use(self):
        first = self.evaluator.choose_best_road(self.board, self.id)
        if first is None:
            return None

        simulated = self.evaluator.simulate_build_action(
            self.board,
            self.id,
            {
                "building": BuildConstants.ROAD,
                "node_id": first["starting_node"],
                "road_to": first["finishing_node"],
            },
        )
        second = self.evaluator.choose_best_road(simulated, self.id)
        return {
            "node_id": first["starting_node"],
            "road_to": first["finishing_node"],
            "node_id_2": None if second is None else second["starting_node"],
            "road_to_2": None if second is None else second["finishing_node"],
        }

    def on_year_of_plenty_card_use(self):
        target = self.evaluator.choose_target_building(self.board, self.id, self.hand.resources)
        missing = self.evaluator.materials_missing_for_building(self.hand.resources, target)
        ordered = sorted(range(5), key=lambda material_id: missing.get_from_id(material_id), reverse=True)
        first = ordered[0]
        second = ordered[1] if missing.get_from_id(ordered[1]) > 0 else first
        return {"material": first, "material_2": second}
