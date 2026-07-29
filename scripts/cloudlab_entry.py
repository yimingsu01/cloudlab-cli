"""PyInstaller entry point for the standalone CloudLab executable."""

from cloudlab_cli.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
