"""The cloudlab command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .api import DEFAULT_PORTAL_URL, CloudLabError, PortalClient
from .availability import fetch_availability
from .output import error, print_json, print_table


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudlab",
        description="Manage CloudLab experiments from the command line.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--portal-url",
        default=os.getenv(
            "CLOUDLAB_PORTAL_URL", os.getenv("PORTAL_HTTP", DEFAULT_PORTAL_URL)
        ),
        help="Portal REST API base URL (env: CLOUDLAB_PORTAL_URL or PORTAL_HTTP)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("CLOUDLAB_TOKEN", os.getenv("PORTAL_TOKEN")),
        help="Portal API token (env: CLOUDLAB_TOKEN or PORTAL_TOKEN)",
    )
    parser.add_argument(
        "--token-file",
        default=os.getenv("CLOUDLAB_TOKEN_FILE"),
        help="Read the Portal API token from a file (env: CLOUDLAB_TOKEN_FILE)",
    )
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="HTTP timeout in seconds"
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (not recommended)",
    )

    commands = parser.add_subparsers(dest="command", required=True)
    availability = commands.add_parser(
        "availability",
        aliases=["nodes"],
        help="Show free node counts by cluster and type",
    )
    availability.add_argument("--json", action="store_true", help="Print JSON")

    experiments = commands.add_parser(
        "experiments", aliases=["list"], help="Show experiments on your account"
    )
    experiments.add_argument("--json", action="store_true", help="Print JSON")

    create = commands.add_parser(
        "create", help="Create an Ubuntu 24.04 small-lan experiment"
    )
    create.add_argument("name", help="New experiment name")
    create.add_argument("--project", required=True, help="CloudLab project")
    create.add_argument(
        "--type", required=True, dest="node_type", help="Physical node type"
    )
    create.add_argument("--count", required=True, type=int, help="Number of nodes")
    create.add_argument(
        "--duration",
        type=int,
        default=24,
        metavar="HOURS",
        help="Initial duration in hours (default: 24)",
    )
    create.add_argument("--json", action="store_true", help="Print JSON")

    extend = commands.add_parser(
        "extend", help="Choose an experiment and request a seven-day extension"
    )
    extend.add_argument(
        "--experiment", help="Experiment name or ID; omit to choose interactively"
    )
    extend.add_argument("--reason", help="Reason included with the extension request")
    extend.add_argument("--json", action="store_true", help="Print JSON")

    hostnames = commands.add_parser(
        "hostnames", aliases=["hosts"], help="Show node hostnames in your experiments"
    )
    hostnames.add_argument("--experiment", help="Filter by experiment name or ID")
    hostnames.add_argument("--json", action="store_true", help="Print JSON")
    return parser


def _token(args: argparse.Namespace) -> str:
    if args.token_file:
        try:
            return (
                Path(args.token_file).expanduser().read_text(encoding="utf-8").strip()
            )
        except OSError as exc:
            raise CloudLabError(
                f"Could not read token file {args.token_file}: {exc}"
            ) from exc
    return args.token or ""


def _experiments_table(experiments: list[dict[str, Any]]) -> None:
    print_table(
        ("NAME", "STATUS", "PROJECT", "PROFILE", "EXPIRES", "ID"),
        (
            (
                item.get("name"),
                item.get("status"),
                item.get("project"),
                item.get("profile_name"),
                item.get("expires_at"),
                item.get("id"),
            )
            for item in experiments
        ),
    )


def _match_experiment(
    experiments: list[dict[str, Any]], selector: str
) -> dict[str, Any]:
    exact = [
        item
        for item in experiments
        if selector in {str(item.get("id", "")), str(item.get("name", ""))}
    ]
    if not exact:
        raise CloudLabError(f"No experiment named or identified by {selector!r}")
    if len(exact) > 1:
        raise CloudLabError(f"Experiment name {selector!r} is ambiguous; use its ID")
    return exact[0]


def _choose_experiment(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    if not experiments:
        raise CloudLabError("There are no experiments to extend")
    print("Choose an experiment to extend by 7 days:")
    print_table(
        ("#", "NAME", "STATUS", "EXPIRES", "PROJECT"),
        (
            (
                index,
                item.get("name"),
                item.get("status"),
                item.get("expires_at"),
                item.get("project"),
            )
            for index, item in enumerate(experiments, start=1)
        ),
    )
    try:
        answer = input("Experiment number (blank to cancel): ").strip()
    except EOFError as exc:
        raise CloudLabError(
            "Interactive selection needs a terminal; use --experiment NAME_OR_ID"
        ) from exc
    if not answer:
        raise CloudLabError("Extension cancelled")
    try:
        index = int(answer)
    except ValueError as exc:
        raise CloudLabError("Selection must be an experiment number") from exc
    if index < 1 or index > len(experiments):
        raise CloudLabError(f"Selection must be between 1 and {len(experiments)}")
    return experiments[index - 1]


def _nodes(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    aggregates = experiment.get("aggregates") or {}
    if isinstance(aggregates, dict):
        aggregate_items = aggregates.items()
    elif isinstance(aggregates, list):
        aggregate_items = (
            (str(item.get("urn", "")), item)
            for item in aggregates
            if isinstance(item, dict)
        )
    else:
        aggregate_items = ()
    for urn, aggregate in aggregate_items:
        if not isinstance(aggregate, dict):
            continue
        for node in aggregate.get("nodes") or []:
            if isinstance(node, dict):
                result.append(
                    {
                        "experiment": experiment.get("name"),
                        "experiment_id": experiment.get("id"),
                        "node": node.get("client_id"),
                        "hostname": node.get("hostname"),
                        "ipv4": node.get("ipv4"),
                        "cluster": aggregate.get("name") or urn,
                    }
                )
    return result


def run(args: argparse.Namespace) -> int:
    if args.command in {"availability", "nodes"}:
        rows = fetch_availability(timeout=args.timeout, verify=not args.insecure)
        if args.json:
            print_json(rows)
        else:
            print_table(
                ("CLUSTER", "TYPE", "AVAILABLE"),
                ((row["cluster"], row["type"], row["available"]) for row in rows),
            )
        return 0

    with PortalClient(
        _token(args),
        base_url=args.portal_url,
        timeout=args.timeout,
        verify=not args.insecure,
    ) as client:
        if args.command in {"experiments", "list"}:
            experiments = client.list_experiments()
            print_json(experiments) if args.json else _experiments_table(experiments)
            return 0

        if args.command == "create":
            if args.count < 1:
                raise CloudLabError("--count must be at least 1")
            if args.duration < 1:
                raise CloudLabError("--duration must be at least 1 hour")
            created = client.create_experiment(
                name=args.name,
                project=args.project,
                node_type=args.node_type,
                count=args.count,
                duration=args.duration,
            )
            if args.json:
                print_json(created)
            else:
                print(f"Created experiment {created.get('name', args.name)}")
                print(f"ID: {created.get('id', '-')}")
                print(f"Status: {created.get('status', '-')}")
                if created.get("url"):
                    print(f"URL: {created['url']}")
            return 0

        if args.command == "extend":
            experiments = client.list_experiments()
            selected = (
                _match_experiment(experiments, args.experiment)
                if args.experiment
                else _choose_experiment(experiments)
            )
            result = client.extend_experiment(str(selected["id"]), reason=args.reason)
            if args.json:
                print_json(result)
            else:
                print(f"Requested a 7-day extension for {selected.get('name')}.")
                print(f"Expiration: {result.get('expires_at', 'pending approval')}")
            return 0

        if args.command in {"hostnames", "hosts"}:
            experiments = client.list_experiments()
            if args.experiment:
                experiments = [_match_experiment(experiments, args.experiment)]
            rows: list[dict[str, Any]] = []
            for experiment in experiments:
                found = _nodes(experiment)
                if not found and experiment.get("id"):
                    found = _nodes(client.get_experiment(str(experiment["id"])))
                rows.extend(found)
            if args.json:
                print_json(rows)
            else:
                print_table(
                    ("EXPERIMENT", "NODE", "HOSTNAME", "IPV4", "CLUSTER"),
                    (
                        (
                            row["experiment"],
                            row["node"],
                            row["hostname"],
                            row["ipv4"],
                            row["cluster"],
                        )
                        for row in rows
                    ),
                )
            return 0

    raise CloudLabError(f"Unknown command {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (CloudLabError, KeyboardInterrupt) as exc:
        error(str(exc) if str(exc) else "cancelled")
        return 2


if __name__ == "__main__":
    sys.exit(main())
