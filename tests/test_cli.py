import pytest

from pkg_proxy_stress.cli import make_parser
from pkg_proxy_stress.commands import (
    MixedCommand,
    PipCommand,
    RawCommand,
    ResolveCommand,
)

INDEX_URL = "https://proxy.example/simple"


def test_parse_raw_command_returns_typed_command() -> None:
    parser = make_parser()

    command = parser.parse_command(
        ["--index-url", INDEX_URL, "raw", "requests", "urllib3", "--repeat", "2"]
    )

    assert isinstance(command, RawCommand)
    assert command.packages == ("requests", "urllib3")
    assert command.repeat == 2
    assert command.common.index_url


def test_parse_resolve_command_returns_typed_command() -> None:
    parser = make_parser()

    command = parser.parse_command(
        [
            "--index-url",
            INDEX_URL,
            "resolve",
            "urllib3",
            "--requirement",
            ">=1.26",
            "--requirement",
            "<3",
        ]
    )

    assert isinstance(command, ResolveCommand)
    assert command.package == "urllib3"
    assert command.requirements == (">=1.26", "<3")
    assert command.scenarios == ()


def test_parse_pip_command_returns_typed_command() -> None:
    parser = make_parser()

    command = parser.parse_command(
        [
            "--index-url",
            INDEX_URL,
            "pip",
            "--scenario",
            "download-wheel",
            "--repeat",
            "2",
        ]
    )

    assert isinstance(command, PipCommand)
    assert command.scenarios == ("download-wheel",)
    assert command.repeat == 2
    assert command.python_executable


def test_parse_mixed_command_returns_typed_command() -> None:
    parser = make_parser()

    command = parser.parse_command(
        [
            "--index-url",
            INDEX_URL,
            "mixed",
            "--raw-repeat",
            "2",
            "--resolve-repeat",
            "4",
        ]
    )

    assert isinstance(command, MixedCommand)
    assert command.raw_repeat == 2
    assert command.resolve_repeat == 4
    assert command.pip_repeat == 1


def test_parse_command_rejects_custom_resolve_without_requirements() -> None:
    parser = make_parser()

    with pytest.raises(SystemExit):
        parser.parse_command(["--index-url", INDEX_URL, "resolve", "urllib3"])


def test_parse_command_rejects_non_positive_workers() -> None:
    parser = make_parser()

    with pytest.raises(SystemExit):
        parser.parse_command(["--index-url", INDEX_URL, "--workers", "0", "raw"])
