"""Small wrapper around CloudLab's Portal REST API."""

from __future__ import annotations

from typing import Any

import httpx
from typing_extensions import Self

DEFAULT_PORTAL_URL = "https://boss.emulab.net:43794"


class CloudLabError(RuntimeError):
    """A user-facing CloudLab or network error."""


class PortalClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_PORTAL_URL,
        timeout: float = 30.0,
        verify: bool = True,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not token.strip():
            raise CloudLabError(
                "CloudLab API token is required. Set CLOUDLAB_TOKEN or PORTAL_TOKEN, "
                "or pass --token/--token-file."
            )
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "X-Api-Token": token.strip(),
                "Accept": "application/json",
                "User-Agent": "cloudlab-cli/0.1.0",
            },
            timeout=timeout,
            verify=verify,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        elaborate: bool = False,
    ) -> dict[str, Any]:
        headers = {"X-Api-Elaborate": "true"} if elaborate else None
        try:
            response = self._client.request(method, path, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise CloudLabError(
                f"Could not reach the CloudLab Portal API: {exc}"
            ) from exc

        if response.is_error:
            detail: object
            try:
                body = response.json()
                detail = body.get("error") or body.get("message") or body
            except (ValueError, AttributeError):
                detail = response.text.strip() or response.reason_phrase
            if response.status_code == 401:
                detail = "token was rejected; download a fresh Portal API token"
            raise CloudLabError(f"CloudLab API error {response.status_code}: {detail}")

        if response.status_code == 204 or not response.content:
            return {}
        try:
            body = response.json()
        except ValueError as exc:
            raise CloudLabError(
                "CloudLab returned a response that was not valid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise CloudLabError("CloudLab returned an unexpected response shape")
        return body

    def list_experiments(self) -> list[dict[str, Any]]:
        body = self._request("GET", "/experiments", elaborate=True)
        experiments = body.get("experiments", [])
        if not isinstance(experiments, list):
            raise CloudLabError("CloudLab returned an invalid experiment list")
        return [item for item in experiments if isinstance(item, dict)]

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        return self._request("GET", f"/experiments/{experiment_id}", elaborate=True)

    def create_experiment(
        self,
        *,
        name: str,
        project: str,
        node_type: str,
        count: int,
        duration: int,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/experiments",
            json={
                "name": name,
                "project": project,
                "profile_name": "small-lan",
                "profile_project": "PortalProfiles",
                "duration": duration,
                "bindings": {
                    "nodeCount": str(count),
                    "phystype": node_type,
                    "osImage": (
                        "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU24-64-STD"
                    ),
                    "bestEffort": "true",
                },
            },
        )

    def extend_experiment(
        self, experiment_id: str, *, reason: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"extend_by": 7 * 24}
        if reason:
            body["reason"] = reason
        return self._request("PUT", f"/experiments/{experiment_id}", json=body)
