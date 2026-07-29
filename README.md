# cloudlab-cli

A focused CLI for [CloudLab](https://www.cloudlab.us/) experiment management.

It can:

- show currently available node counts for each of the Utah, Wisconsin, and
  Clemson CloudLab clusters;
- create a `small-lan` experiment using a requested physical node type and
  count, Ubuntu 24.04, and best-effort links;
- list your experiments;
- interactively choose an experiment to extend by exactly seven days; and
- show the hostnames of nodes in your experiments.

## Install a standalone binary

Standalone executables do not require Python. Download the file for your
operating system and CPU from the
[GitHub Releases](https://github.com/yimingsu01/cloudlab-cli/releases) page:

- `cloudlab-linux-x86_64`
- `cloudlab-linux-arm64`
- `cloudlab-macos-x86_64`
- `cloudlab-macos-arm64`
- `cloudlab-windows-x86_64.exe`

On Linux or macOS, make the download executable and place it on your path:

```shell
chmod +x cloudlab-linux-x86_64
sudo install cloudlab-linux-x86_64 /usr/local/bin/cloudlab
cloudlab --version
```

Replace the filename with the matching macOS download when appropriate. On
Windows, rename the download to `cloudlab.exe` and place it in a directory in
`PATH`. The macOS and Windows binaries are currently unsigned, so those systems
may ask you to confirm that you trust the download.

Each executable is platform-specific. It can be copied to other machines with
the same operating system and CPU architecture.

## Install as a Python package

Python 3.10 or newer is required.

```shell
python -m pip install .
```

For development:

```shell
python -m pip install -e '.[dev]'
pytest
```

## Build standalone binaries

Build a one-file executable for the current platform:

```shell
uv sync --extra binary
uv run python scripts/build_binary.py
./dist/cloudlab --version
```

PyInstaller is not a cross-compiler. Run that command on each target platform,
or use the included `Standalone binaries` GitHub Actions workflow. A manual
workflow run stores the five executables as workflow artifacts. Pushing a tag
also creates a GitHub release containing them:

```shell
git tag v0.1.0
git push origin v0.1.0
```

## Authentication

Log in to CloudLab, click your name in the upper-right corner, choose
**Portal API Token**, and download a token. The token is an unencrypted secret:
do not commit or share it.

Pass it through an environment variable:

```shell
export CLOUDLAB_TOKEN='your_token_string'
```

The official client also uses `PORTAL_TOKEN`, so this CLI accepts that name
too. You can instead save the token in a private file:

```shell
export CLOUDLAB_TOKEN_FILE="$HOME/.config/cloudlab/token"
chmod 600 "$CLOUDLAB_TOKEN_FILE"
```

The Portal API defaults to `https://boss.emulab.net:43794`. Override it with
`CLOUDLAB_PORTAL_URL`, `PORTAL_HTTP`, or `--portal-url` if the token download
page gives you a different service URL.

## Usage

Show live availability. This command reads the three public cluster status
pages and does not require a token:

```shell
cloudlab availability
# Short alias:
cloudlab nodes
```

List account experiments:

```shell
cloudlab experiments
cloudlab experiments --json
```

Create three nodes of a specific type for 24 hours:

```shell
cloudlab create demo \
  --project my-project \
  --type c6525-25g \
  --count 3
```

Use `--duration HOURS` to change the initial 24-hour duration. Creation always
uses profile `PortalProfiles/small-lan` with these fixed bindings:

- Ubuntu 24.04 (`UBUNTU24-64-STD`)
- `bestEffort=true`
- bare-metal nodes of the type and count supplied on the command line

Choose an experiment from a numbered list and extend it by seven days:

```shell
cloudlab extend
```

For scripts, bypass the prompt by name or ID. The extension remains fixed at
seven days:

```shell
cloudlab extend --experiment demo --reason "Finishing evaluation runs"
```

Show node hostnames:

```shell
cloudlab hostnames
cloudlab hostnames --experiment demo
cloudlab hostnames --json
```

Every data command supports `--json`. Global options must precede the command:

```shell
cloudlab --timeout 60 --portal-url https://example:43794 experiments
```

Use `cloudlab --help` and `cloudlab COMMAND --help` for the full reference.

## Notes

Availability is a live snapshot and can change before an experiment maps.
CloudLab may require administrator approval for extension requests. The CLI
reports the expiration returned by CloudLab; a pending request can also
generate email from CloudLab when it is approved or rejected.
