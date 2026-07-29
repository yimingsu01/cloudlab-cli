"""Build a standalone CloudLab executable for the current platform."""

from __future__ import annotations

import argparse
from pathlib import Path

import PyInstaller.__main__


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-name",
        default="cloudlab",
        help="Executable name without the automatic Windows .exe suffix",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Directory in which to place the executable (default: dist)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    build_dir = project_root / "build" / "pyinstaller"
    dist_dir = project_root / args.dist_dir
    entrypoint = project_root / "scripts" / "cloudlab_entry.py"

    PyInstaller.__main__.run(
        [
            "--name",
            args.output_name,
            "--onefile",
            "--clean",
            "--noconfirm",
            "--paths",
            str(project_root / "src"),
            "--workpath",
            str(build_dir),
            "--specpath",
            str(build_dir),
            "--distpath",
            str(dist_dir),
            str(entrypoint),
        ]
    )


if __name__ == "__main__":
    main()
