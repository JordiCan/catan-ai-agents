from Experiments.runner import run_heuristic_benchmark, run_llm_probe


class TestExperimentRunner:
    def test_heuristic_benchmark_smoke(self):
        results = run_heuristic_benchmark(games=1, max_rounds=10, seed=7)
        assert len(results) == 1
        assert "winner" in results[0]
        assert "victory_points" in results[0]

    def test_llm_probe_smoke(self):
        results = run_llm_probe(games=1, max_rounds=10, seed=9)
        assert len(results) == 1
        assert "winner" in results[0]
