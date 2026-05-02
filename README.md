# pkg-proxy-stress

Stress-test a PyPI proxy via raw `/simple` requests, lightweight resolver simulation, and real `pip` traffic.

## Install

```bash
uv sync
```

## Usage

Use the CLI help for the full surface area:

```bash
uv run pkg-proxy-stress --help
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple raw --help
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple resolve --help
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple pip --help
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple mixed --help
```

Common commands:

```bash
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple mixed
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple --workers 16 --log-level INFO mixed

uv run pkg-proxy-stress --index-url https://your-proxy.example/simple raw
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple raw requests urllib3 fastapi --repeat 20

uv run pkg-proxy-stress --index-url https://your-proxy.example/simple resolve
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple resolve urllib3 --requirement '>=1.26' --requirement '<3'

uv run pkg-proxy-stress --index-url https://your-proxy.example/simple pip
uv run pkg-proxy-stress --index-url https://your-proxy.example/simple pip --scenario resolve-web-stack --repeat 5
```

## Notes

- `--index-url` is required. This tool does not default to any public index.
- Exit code is non-zero if any workload result does not match its expectation.
- Some built-in conflict scenarios are intentionally unsatisfiable and are treated as expected failures.
- `pip install` workloads run in a fresh temporary virtualenv.
