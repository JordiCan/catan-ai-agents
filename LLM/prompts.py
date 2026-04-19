from pathlib import Path

from LLM.base import safe_json_dumps


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


class PromptBuilder:
    def __init__(self, prompt_name="strict_json"):
        self.prompt_name = prompt_name

    def _load_template(self):
        prompt_path = PROMPT_DIR / f"{self.prompt_name}.txt"
        return prompt_path.read_text(encoding="utf-8")

    def build(self, decision_type, game_state, candidate_actions):
        template = self._load_template()
        return template.format(
            decision_type=decision_type,
            game_state=safe_json_dumps(game_state),
            candidate_actions=safe_json_dumps(candidate_actions),
        )
