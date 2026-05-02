import logging
import os
import statistics
import time
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

LOGGER = logging.getLogger("pkg_proxy_stress")


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
    )


def normalize_index_url(index_url: str) -> str:
    return index_url.rstrip("/")


def simple_root_url(index_url: str) -> str:
    return normalize_index_url(index_url) + "/"


def simple_package_url(index_url: str, package: str) -> str:
    from packaging.utils import canonicalize_name

    return normalize_index_url(index_url) + f"/{canonicalize_name(package)}/"


def is_install_command(pip_args: tuple[str, ...]) -> bool:
    return bool(pip_args) and pip_args[0] == "install"


def venv_python_path(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def remaining_timeout(start_time: float, timeout: float) -> float:
    return max(0.001, timeout - (time.perf_counter() - start_time))


def coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def matched_expectation(ok: bool, expected_ok: bool) -> bool:
    return ok == expected_ok


def expectation_label(expected_ok: bool) -> str:
    return "expected-ok" if expected_ok else "expected-fail"


def summarize_output(output: str, max_lines: int = 8, max_chars: int = 800) -> str:
    if not output:
        return ""

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) > max_lines:
        lines = [*lines[:max_lines], "..."]

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def print_latency_summary(durations: list[float]) -> None:
    avg = sum(durations) / len(durations)
    median = statistics.median(durations)
    p95 = percentile(durations, 95)
    print(
        f"  latency avg={avg:.3f}s p50={median:.3f}s p95={p95:.3f}s max={max(durations):.3f}s"
    )


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def version_satisfies(version: Version, specifier_set: SpecifierSet) -> bool:
    return specifier_set.contains(version, prereleases=True)
