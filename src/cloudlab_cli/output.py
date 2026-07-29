"""Terminal and JSON output helpers."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from typing import Any


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def print_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    materialized = [
        [str(value if value is not None else "-") for value in row] for row in rows
    ]
    if not materialized:
        print("No results.")
        return
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in materialized))
        for index in range(len(headers))
    ]
    print(
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    )
    print("  ".join("-" * width for width in widths))
    for row in materialized:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
