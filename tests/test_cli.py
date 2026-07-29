from cloudlab_cli.cli import _match_experiment, _nodes


def test_match_experiment_by_name_or_id() -> None:
    experiments = [
        {"id": "abc", "name": "demo"},
        {"id": "def", "name": "other"},
    ]
    assert _match_experiment(experiments, "demo")["id"] == "abc"
    assert _match_experiment(experiments, "def")["name"] == "other"


def test_extract_hostnames_from_aggregates() -> None:
    experiment = {
        "id": "abc",
        "name": "demo",
        "aggregates": {
            "urn:utah": {
                "name": "Utah",
                "nodes": [
                    {
                        "client_id": "node0",
                        "hostname": "node0.demo.project.utah.cloudlab.us",
                        "ipv4": "192.0.2.1",
                    }
                ],
            }
        },
    }
    assert _nodes(experiment) == [
        {
            "experiment": "demo",
            "experiment_id": "abc",
            "node": "node0",
            "hostname": "node0.demo.project.utah.cloudlab.us",
            "ipv4": "192.0.2.1",
            "cluster": "Utah",
        }
    ]
