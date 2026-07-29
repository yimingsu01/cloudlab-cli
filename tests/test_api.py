from __future__ import annotations

import json

import httpx

from cloudlab_cli.api import PortalClient


def test_create_uses_small_lan_ubuntu_2404_and_best_effort() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["token"] = request.headers["X-Api-Token"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            201, json={"id": "exp-id", "name": "demo", "status": "provisioning"}
        )

    with PortalClient(
        "secret",
        base_url="https://portal.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.create_experiment(
            name="demo",
            project="my-project",
            node_type="c6525-25g",
            count=3,
            duration=24,
        )

    assert result["id"] == "exp-id"
    assert seen["method"] == "POST"
    assert seen["path"] == "/experiments"
    assert seen["token"] == "secret"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["profile_name"] == "small-lan"
    assert body["profile_project"] == "PortalProfiles"
    assert body["bindings"] == {
        "nodeCount": "3",
        "phystype": "c6525-25g",
        "osImage": "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU24-64-STD",
        "bestEffort": "true",
    }


def test_extend_is_always_seven_days() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "exp-id", "expires_at": "later"})

    with PortalClient(
        "secret",
        base_url="https://portal.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        client.extend_experiment("exp-id", reason="finishing evaluation")

    assert seen == {
        "method": "PUT",
        "path": "/experiments/exp-id",
        "body": {"extend_by": 168, "reason": "finishing evaluation"},
    }


def test_list_requests_elaborated_experiments() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Api-Elaborate"] == "true"
        return httpx.Response(200, json={"experiments": [{"id": "one"}]})

    with PortalClient(
        "secret",
        base_url="https://portal.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.list_experiments() == [{"id": "one"}]
