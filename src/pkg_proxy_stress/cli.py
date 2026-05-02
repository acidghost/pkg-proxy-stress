import argparse
import logging
import sys
from collections.abc import Sequence
from typing import cast

from pkg_proxy_stress.commands import (
    Command,
    CommonOptions,
    LogLevelName,
    MixedCommand,
    PipCommand,
    RawCommand,
    ResolveCommand,
)
from pkg_proxy_stress.runner import run_mixed, run_pip, run_raw, run_resolve
from pkg_proxy_stress.settings import (
    DEFAULT_PIP_SCENARIOS,
    DEFAULT_RAW_PACKAGES,
    DEFAULT_RESOLVE_SCENARIOS,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
)
from pkg_proxy_stress.utils import configure_logging

LOGGER = logging.getLogger("pkg_proxy_stress")


class ArgumentParser(argparse.ArgumentParser):
    def parse_command(self, argv: Sequence[str] | None = None) -> Command:
        namespace = self.parse_args(argv)
        try:
            return namespace_to_command(namespace)
        except ValueError as exc:
            self.error(str(exc))


def make_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Stress-test a PyPI simple proxy with raw HTTP requests and pip workloads."
    )
    parser.add_argument(
        "--index-url",
        required=True,
        help="Base /simple index URL to target.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Maximum number of concurrent worker threads. Default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Per-workload timeout in seconds. Default: %(default)s",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity. Default: %(default)s",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    raw = subparsers.add_parser(
        "raw", help="Make raw GET requests against /simple and package pages."
    )
    raw.add_argument(
        "packages",
        nargs="*",
        default=DEFAULT_RAW_PACKAGES,
        help="Package names to request under /simple. If omitted, uses the built-in package set.",
    )
    raw.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Number of times to request each package page. Default: %(default)s",
    )

    resolve = subparsers.add_parser(
        "resolve",
        help="Simulate a package manager choosing a version that satisfies all requirements.",
    )
    resolve.add_argument(
        "package",
        nargs="?",
        help="Custom package name to resolve. If omitted, built-in scenarios are used.",
    )
    resolve.add_argument(
        "--requirement",
        action="append",
        default=[],
        help="Version constraint for a custom resolve run. Repeat to add multiple constraints.",
    )
    resolve.add_argument(
        "--scenario",
        action="append",
        choices=sorted(DEFAULT_RESOLVE_SCENARIOS),
        default=[],
        help="Run one of the built-in resolver scenarios.",
    )
    resolve.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Number of times to run each resolver workload. Default: %(default)s",
    )

    pip_command = subparsers.add_parser(
        "pip", help="Run pip commands against the proxy."
    )
    pip_command.add_argument(
        "--scenario",
        action="append",
        choices=sorted(DEFAULT_PIP_SCENARIOS),
        default=[],
        help="Run one of the built-in pip scenarios. Defaults to all.",
    )
    pip_command.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to run each selected pip scenario. Default: %(default)s",
    )
    pip_command.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create ad-hoc venvs and run `python -m pip`.",
    )

    mixed = subparsers.add_parser(
        "mixed", help="Run raw, resolver, and pip workloads together."
    )
    mixed.add_argument(
        "--raw-repeat",
        type=int,
        default=3,
        help="Number of times to run each built-in raw HTTP workload. Default: %(default)s",
    )
    mixed.add_argument(
        "--resolve-repeat",
        type=int,
        default=3,
        help="Number of times to run each built-in resolver workload. Default: %(default)s",
    )
    mixed.add_argument(
        "--pip-repeat",
        type=int,
        default=1,
        help="Number of times to run each built-in pip workload. Default: %(default)s",
    )
    mixed.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create ad-hoc venvs and run `python -m pip`.",
    )

    return parser


def _common_options(namespace: argparse.Namespace) -> CommonOptions:
    return CommonOptions(
        index_url=cast(str, namespace.index_url),
        workers=cast(int, namespace.workers),
        timeout=cast(float, namespace.timeout),
        log_level=cast(LogLevelName, namespace.log_level),
    )


def namespace_to_command(namespace: argparse.Namespace) -> Command:
    command_name = cast(str, namespace.command)
    common = _common_options(namespace)

    if command_name == "raw":
        return RawCommand(
            kind="raw",
            common=common,
            packages=tuple(cast(list[str], namespace.packages)),
            repeat=cast(int, namespace.repeat),
        )

    if command_name == "resolve":
        return ResolveCommand(
            kind="resolve",
            common=common,
            package=cast(str | None, namespace.package),
            requirements=tuple(cast(list[str], namespace.requirement)),
            scenarios=tuple(cast(list[str], namespace.scenario)),
            repeat=cast(int, namespace.repeat),
        )

    if command_name == "pip":
        return PipCommand(
            kind="pip",
            common=common,
            scenarios=tuple(cast(list[str], namespace.scenario)),
            repeat=cast(int, namespace.repeat),
            python_executable=cast(str, namespace.python),
        )

    if command_name == "mixed":
        return MixedCommand(
            kind="mixed",
            common=common,
            raw_repeat=cast(int, namespace.raw_repeat),
            resolve_repeat=cast(int, namespace.resolve_repeat),
            pip_repeat=cast(int, namespace.pip_repeat),
            python_executable=cast(str, namespace.python),
        )

    raise ValueError(f"unknown command: {command_name}")


def dispatch(command: Command) -> int:
    match command:
        case RawCommand():
            return run_raw(command)
        case ResolveCommand():
            return run_resolve(command)
        case PipCommand():
            return run_pip(command)
        case MixedCommand():
            return run_mixed(command)


def main() -> None:
    parser = make_parser()
    command = parser.parse_command()
    configure_logging(command.common.log_level)
    LOGGER.debug("parsed command=%s", command)
    raise SystemExit(dispatch(command))
