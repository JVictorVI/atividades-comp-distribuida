import json
import tempfile
import unittest
from pathlib import Path

from p2p_search import ConfigError, P2PNetwork, build_visualization_html, load_config


def base_config():
    return {
        "num_nodes": 4,
        "min_neighbors": 1,
        "max_neighbors": 2,
        "resources": {
            "n1": ["r1"],
            "n2": ["r2"],
            "n3": ["r3"],
            "n4": ["r4"],
        },
        "edges": [
            ["n1", "n2"],
            ["n2", "n3"],
            ["n3", "n4"],
        ],
    }


class P2PNetworkTest(unittest.TestCase):
    def test_flooding_finds_resource_and_counts_messages(self):
        network = P2PNetwork(base_config())

        result = network.search("n1", "r4", ttl=3, algorithm="flooding")

        self.assertTrue(result.found)
        self.assertEqual(result.holder, "n4")
        self.assertEqual(result.messages, 6)
        self.assertEqual(result.nodes_involved, 4)
        self.assertEqual(result.path, ["n1", "n2", "n3", "n4"])
        self.assertEqual(len(result.events), result.messages)
        self.assertEqual(result.events[0].kind, "request")
        self.assertEqual(result.events[-1].kind, "reply")

    def test_ttl_can_stop_search_before_resource(self):
        network = P2PNetwork(base_config())

        result = network.search("n1", "r4", ttl=2, algorithm="flooding")

        self.assertFalse(result.found)
        self.assertEqual(result.messages, 2)
        self.assertEqual(result.nodes_involved, 3)

    def test_informed_search_uses_cache_learned_from_previous_search(self):
        network = P2PNetwork(base_config())

        network.search("n1", "r4", ttl=3, algorithm="flooding")
        result = network.search("n1", "r4", ttl=3, algorithm="informed_flooding")

        self.assertTrue(result.found)
        self.assertEqual(result.holder, "n4")
        self.assertEqual(result.found_via, "cache")
        self.assertEqual(result.messages, 0)
        self.assertEqual(result.nodes_involved, 1)

    def test_random_walk_is_deterministic_with_seed(self):
        network = P2PNetwork(base_config())

        result = network.search("n1", "r4", ttl=3, algorithm="random_walk", seed=6)

        self.assertTrue(result.found)
        self.assertEqual(result.path, ["n1", "n2", "n3", "n4"])

    def test_rejects_partitioned_network(self):
        config = base_config()
        config["edges"] = [["n1", "n2"], ["n3", "n4"]]

        with self.assertRaisesRegex(ConfigError, "particionada"):
            P2PNetwork(config)

    def test_rejects_degrees_outside_limits(self):
        config = base_config()
        config["min_neighbors"] = 2

        with self.assertRaisesRegex(ConfigError, "vizinhos"):
            P2PNetwork(config)

    def test_rejects_node_without_resources(self):
        config = base_config()
        config["resources"]["n2"] = []

        with self.assertRaisesRegex(ConfigError, "sem recursos"):
            P2PNetwork(config)

    def test_rejects_self_loop(self):
        config = base_config()
        config["edges"].append(["n1", "n1"])

        with self.assertRaisesRegex(ConfigError, "ele mesmo"):
            P2PNetwork(config)

    def test_loads_simple_yaml_format(self):
        text = """
        num_nodes: 3
        min_neighbors: 1
        max_neighbors: 2
        resources:
          n1: r1, a
          n2: r2
          n3: r3
        edges:
          - n1, n2
          - [n2, n3]
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.yaml"
            path.write_text(text, encoding="utf-8")

            config = load_config(path)
            network = P2PNetwork(config)

        self.assertEqual(network.num_nodes, 3)
        self.assertEqual(network.resources["n1"], {"r1", "a"})

    def test_loads_statement_format_without_edge_dashes(self):
        text = """
        num_nodes: 3
        min_neighbors: 1
        max_neighbors: 2
        resources:
        n1: r1, r2
        n2: r3
        n3: r4
        edges:
        n1, n2
        n2, n3
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.txt"
            path.write_text(text, encoding="utf-8")

            config = load_config(path)
            network = P2PNetwork(config)

        self.assertEqual(network.num_nodes, 3)
        self.assertEqual(network.resources["n1"], {"r1", "r2"})
        self.assertEqual(network.edges, {("n1", "n2"), ("n2", "n3")})

    def test_loads_json_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.json"
            path.write_text(json.dumps(base_config()), encoding="utf-8")

            network = P2PNetwork.from_file(path)

        self.assertEqual(network.num_nodes, 4)

    def test_builds_html_visualization_with_animation_data(self):
        network = P2PNetwork(base_config())
        result = network.search("n1", "r4", ttl=3, algorithm="flooding")

        html = build_visualization_html(network, result)

        self.assertIn("<svg id=\"network\"", html)
        self.assertIn("\"events\"", html)
        self.assertIn("Rede P2P - flooding", html)
        self.assertIn("n1", html)


if __name__ == "__main__":
    unittest.main()
