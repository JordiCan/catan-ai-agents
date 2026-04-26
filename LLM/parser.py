import json
import re


JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text):
    if text is None:
        raise ValueError("Empty model response")

    candidate = text.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate

    match = JSON_OBJECT_RE.search(candidate)
    if match is None:
        raise ValueError("No JSON object found in model response")
    return match.group(0)


def parse_json_response(text):
    payload = extract_json_object(text)
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")
    return data


def unwrap_action_object(data):
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")

    for key in ("action", "result", "response"):
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
    return data


def validate_start_response(data):
    data = unwrap_action_object(data)
    if not isinstance(data.get("node_id"), int):
        raise ValueError("node_id must be an int")
    if not isinstance(data.get("road_to"), int):
        raise ValueError("road_to must be an int")
    return {"node_id": data["node_id"], "road_to": data["road_to"]}


def validate_build_response(data):
    data = unwrap_action_object(data)
    building = data.get("building")
    if building not in {"town", "city", "road", "card", None}:
        raise ValueError("Invalid building type")

    normalized = {
        "building": building,
        "node_id": data.get("node_id"),
        "road_to": data.get("road_to"),
    }

    if building in {"town", "city"} and not isinstance(normalized["node_id"], int):
        raise ValueError("node_id is required for town/city")
    if building == "road":
        if not isinstance(normalized["node_id"], int) or not isinstance(normalized["road_to"], int):
            raise ValueError("node_id and road_to are required for road")
    return normalized
