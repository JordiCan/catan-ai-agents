from copy import copy

from Classes.Constants import BuildConstants, HarborConstants, MaterialConstants, TerrainConstants
from Classes.Materials import Materials


PIP_WEIGHTS = {
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    8: 5,
    9: 4,
    10: 3,
    11: 2,
    12: 1,
}

RESOURCE_SCARCITY = {
    TerrainConstants.CEREAL: 1.1,
    TerrainConstants.MINERAL: 1.25,
    TerrainConstants.CLAY: 1.0,
    TerrainConstants.WOOD: 1.0,
    TerrainConstants.WOOL: 0.95,
}

BUILD_PRIORITY = [
    BuildConstants.CITY,
    BuildConstants.TOWN,
    BuildConstants.ROAD,
    BuildConstants.CARD,
]


class HeuristicEvaluator:
    """Centralized strategic scoring used by the heuristic and hybrid agents."""

    def score_node(self, board, node_id):
        node = board.nodes[node_id]
        score = 0.0
        resources = set()

        for terrain_id in node["contacting_terrain"]:
            terrain = board.terrain[terrain_id]
            if terrain["terrain_type"] == TerrainConstants.DESERT:
                continue
            pip_score = PIP_WEIGHTS.get(terrain["probability"], 0)
            resource_weight = RESOURCE_SCARCITY.get(terrain["terrain_type"], 1.0)
            score += pip_score * resource_weight
            resources.add(terrain["terrain_type"])

        score += len(resources) * 1.75

        harbor = node["harbor"]
        if harbor == HarborConstants.ALL:
            score += 1.25
        elif harbor != HarborConstants.NONE:
            if harbor in resources:
                score += 2.0
            else:
                score += 0.75

        if board.is_coastal_node(node_id):
            score -= 0.35

        return score

    def score_road_extension(self, board, player_id, start_node, end_node):
        if end_node not in board.nodes[start_node]["adjacent"]:
            return float("-inf")

        if any(road["node_id"] == end_node for road in board.nodes[start_node]["roads"]):
            return float("-inf")

        next_node = board.nodes[end_node]
        score = 0.0

        if next_node["player"] == -1 and board.empty_adjacent_nodes(end_node):
            score += self.score_node(board, end_node) * 0.65
        elif next_node["player"] not in [-1, player_id]:
            score -= 4.0

        if board.is_coastal_node(end_node) and next_node["harbor"] != HarborConstants.NONE:
            score += 2.5

        unseen_frontier = 0
        for adjacent in next_node["adjacent"]:
            if adjacent == start_node:
                continue
            if next_node["player"] not in [-1, player_id]:
                continue
            if not any(road["node_id"] == adjacent for road in next_node["roads"]):
                unseen_frontier += 1
        score += unseen_frontier * 0.75

        return score

    def choose_starting_settlement(self, board):
        valid_nodes = board.valid_starting_nodes()
        if not valid_nodes:
            return None

        return max(valid_nodes, key=lambda node_id: self.score_node(board, node_id))

    def choose_starting_road(self, board, node_id, player_id):
        options = board.nodes[node_id]["adjacent"]
        if not options:
            return None
        return max(
            options,
            key=lambda adjacent: self.score_road_extension(board, player_id, node_id, adjacent),
        )

    def choose_best_city_node(self, board, player_id):
        valid_nodes = board.valid_city_nodes(player_id)
        if not valid_nodes:
            return None
        return max(valid_nodes, key=lambda node_id: self.score_node(board, node_id))

    def choose_best_town_node(self, board, player_id):
        valid_nodes = board.valid_town_nodes(player_id)
        if not valid_nodes:
            return None
        return max(valid_nodes, key=lambda node_id: self.score_node(board, node_id))

    def choose_best_road(self, board, player_id):
        valid_roads = board.valid_road_nodes(player_id)
        if not valid_roads:
            return None
        return max(
            valid_roads,
            key=lambda road: self.score_road_extension(
                board,
                player_id,
                road["starting_node"],
                road["finishing_node"],
            ),
        )

    def choose_build_action(self, board, player_id, hand_resources):
        city_node = self.choose_best_city_node(board, player_id)
        if city_node is not None and hand_resources.has_more(BuildConstants.CITY):
            return {"building": BuildConstants.CITY, "node_id": city_node}

        town_node = self.choose_best_town_node(board, player_id)
        if town_node is not None and hand_resources.has_more(BuildConstants.TOWN):
            return {"building": BuildConstants.TOWN, "node_id": town_node}

        road_choice = self.choose_best_road(board, player_id)
        if road_choice is not None and hand_resources.has_more(BuildConstants.ROAD):
            return {
                "building": BuildConstants.ROAD,
                "node_id": road_choice["starting_node"],
                "road_to": road_choice["finishing_node"],
            }

        if hand_resources.has_more(BuildConstants.CARD):
            return {"building": BuildConstants.CARD}

        return None

    def choose_target_building(self, board, player_id, hand_resources):
        if board.valid_city_nodes(player_id):
            return BuildConstants.CITY
        if board.valid_town_nodes(player_id):
            return BuildConstants.TOWN
        if board.valid_road_nodes(player_id):
            return BuildConstants.ROAD
        if hand_resources.has_more(BuildConstants.CARD):
            return BuildConstants.CARD
        return BuildConstants.CITY

    def materials_missing_for_building(self, hand_resources, building):
        target = Materials.from_building(building)
        return (target - hand_resources).replace_negative()

    def choose_bank_trade(self, board, player_id, hand):
        resources = hand.resources
        target_building = self.choose_target_building(board, player_id, resources)
        missing = self.materials_missing_for_building(resources, target_building)
        wanted = [material_id for material_id in range(5) if missing.get_from_id(material_id) > 0]
        if not wanted:
            return None

        best_trade = None
        for gives in range(5):
            owned = resources.get_from_id(gives)
            harbor_type = board.check_for_player_harbors(player_id, gives)
            ratio = 4
            if harbor_type == gives:
                ratio = 2
            elif board.check_for_player_harbors(player_id) == HarborConstants.ALL:
                ratio = 3

            if owned < ratio:
                continue

            surplus = owned - Materials.from_building(target_building).get_from_id(gives)
            if surplus < ratio - 1:
                continue

            for receives in wanted:
                if receives == gives:
                    continue
                score = surplus + missing.get_from_id(receives) * 3 - ratio
                candidate = {"gives": gives, "receives": receives, "score": score}
                if best_trade is None or candidate["score"] > best_trade["score"]:
                    best_trade = candidate

        if best_trade is None:
            return None
        return {"gives": best_trade["gives"], "receives": best_trade["receives"]}

    def choose_thief_target(self, board, player_id):
        current_terrain = next(
            (terrain["id"] for terrain in board.terrain if terrain["has_thief"]),
            0,
        )
        best_choice = {"terrain": current_terrain, "player": -1, "score": float("-inf")}

        for terrain in board.terrain:
            if terrain["terrain_type"] == TerrainConstants.DESERT:
                continue

            enemy_score = 0.0
            own_penalty = 0.0
            target_player = -1

            for node_id in terrain["contacting_nodes"]:
                node = board.nodes[node_id]
                occupant = node["player"]
                multiplier = 2 if node["has_city"] else 1

                if occupant == player_id:
                    own_penalty += multiplier
                elif occupant != -1:
                    enemy_score += multiplier
                    if target_player == -1:
                        target_player = occupant

            score = PIP_WEIGHTS.get(terrain["probability"], 0) * (enemy_score - own_penalty * 1.5)
            if terrain["id"] == current_terrain:
                score -= 10

            if score > best_choice["score"] and target_player != -1:
                best_choice = {"terrain": terrain["id"], "player": target_player, "score": score}

        if best_choice["score"] == float("-inf"):
            return {"terrain": current_terrain, "player": -1}
        return {"terrain": best_choice["terrain"], "player": best_choice["player"]}

    def summarize_player_state(self, board, player_id):
        towns = 0
        cities = 0
        roads = 0

        for node in board.nodes:
            if node["player"] == player_id:
                if node["has_city"]:
                    cities += 1
                else:
                    towns += 1
            for road in node["roads"]:
                if road["player_id"] == player_id and node["id"] < road["node_id"]:
                    roads += 1

        return {"towns": towns, "cities": cities, "roads": roads}

    def simulate_build_action(self, board, player_id, action):
        board_copy = copy(board)
        if action is None:
            return board_copy

        building = action["building"]
        if building == BuildConstants.CITY and action.get("node_id") is not None:
            board_copy.build_city(player_id, action["node_id"])
        elif building == BuildConstants.TOWN and action.get("node_id") is not None:
            board_copy.build_town(player_id, action["node_id"])
        elif building == BuildConstants.ROAD and action.get("node_id") is not None and action.get("road_to") is not None:
            board_copy.build_road(player_id, action["node_id"], action["road_to"])
        return board_copy
