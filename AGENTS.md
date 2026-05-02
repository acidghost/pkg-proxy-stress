# INSTRUCTIONS FOR AGENTS

- Use `uv` for all commands.
- Run before finishing: `uv run ruff format . && uv run ruff check . && uv run ty check && uv run pytest -q`
- Source code lives in `src/pkg_proxy_stress/`.
- Keep CLI parsing in `cli.py`; keep runtime logic typed and argparse-free.
- Prefer small, focused modules and dataclasses.
