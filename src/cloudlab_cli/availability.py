"""Fetch live node counts from CloudLab's public cluster homepages."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import Any

import httpx

from .api import CloudLabError

CLUSTERS = {
    "Utah": "https://www.utah.cloudlab.us/",
    "Wisconsin": "https://www.wisc.cloudlab.us/",
    "Clemson": "https://www.clemson.cloudlab.us/",
}


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None:
            assert self._row is not None
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            assert self._table is not None
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def parse_cluster_status(html: str, cluster: str) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(html)
    for table in parser.tables:
        header_index = next(
            (
                index
                for index, row in enumerate(table)
                if len(row) >= 2 and row[0] == "Type" and row[1] == "Free"
            ),
            None,
        )
        if header_index is None:
            continue
        result: list[dict[str, Any]] = []
        for row in table[header_index + 1 :]:
            if len(row) < 2:
                continue
            try:
                available = int(row[1])
            except ValueError:
                continue
            result.append({"cluster": cluster, "type": row[0], "available": available})
        if result:
            return result
    raise CloudLabError(
        f"Could not find node availability on the {cluster} status page"
    )


def fetch_availability(
    *, timeout: float = 30.0, verify: bool = True
) -> list[dict[str, Any]]:
    def request(url: str, verify_request: bool) -> httpx.Response:
        return httpx.get(
            url,
            timeout=timeout,
            verify=verify_request,
            follow_redirects=True,
            headers={"User-Agent": "cloudlab-cli/0.1.0"},
        )

    def fetch(cluster: str, url: str) -> tuple[list[dict[str, Any]], bool]:
        certificate_fallback = False
        try:
            response = request(url, verify)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # CloudLab's three status-only hosts sometimes omit their intermediate
            # CA certificate. Retry only these fixed, public pages; no token or other
            # user data is included in an availability request.
            if verify and "CERTIFICATE_VERIFY_FAILED" in str(exc):
                certificate_fallback = True
                try:
                    response = request(url, False)
                    response.raise_for_status()
                except httpx.HTTPError as fallback_exc:
                    raise CloudLabError(
                        f"Could not fetch {cluster} cluster status: {fallback_exc}"
                    ) from fallback_exc
            else:
                raise CloudLabError(
                    f"Could not fetch {cluster} cluster status: {exc}"
                ) from exc
        return parse_cluster_status(response.text, cluster), certificate_fallback

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    used_certificate_fallback = False
    with ThreadPoolExecutor(max_workers=len(CLUSTERS)) as executor:
        futures = {
            executor.submit(fetch, cluster, url): cluster
            for cluster, url in CLUSTERS.items()
        }
        for future in as_completed(futures):
            try:
                fetched, used_fallback = future.result()
                rows.extend(fetched)
                used_certificate_fallback = used_certificate_fallback or used_fallback
            except CloudLabError as exc:
                errors.append(str(exc))
    if errors:
        raise CloudLabError("; ".join(errors))
    if used_certificate_fallback:
        print(
            "warning: CloudLab's public cluster status certificate chain could not "
            "be verified; retried those unauthenticated status pages only",
            file=sys.stderr,
        )
    order = {name: index for index, name in enumerate(CLUSTERS)}
    return sorted(rows, key=lambda row: (order[row["cluster"]], row["type"]))
