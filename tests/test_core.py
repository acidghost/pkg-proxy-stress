from pathlib import Path

import pytest

from pkg_proxy_stress.http_ops import run_resolve_job
from pkg_proxy_stress.models import ResolveJob
from pkg_proxy_stress.pip_ops import build_pip_command
from pkg_proxy_stress.workloads import build_resolve_jobs

INDEX_URL = "https://proxy.example/simple"


def test_build_resolve_jobs_custom_package_does_not_pull_in_defaults() -> None:
    jobs = build_resolve_jobs(
        scenario_names=(),
        repeat=2,
        package="urllib3",
        requirements=(">=1.26", "<3"),
    )

    assert [(job.name, job.package, job.requirements) for job in jobs] == [
        ("resolve:urllib3:#1", "urllib3", (">=1.26", "<3")),
        ("resolve:urllib3:#2", "urllib3", (">=1.26", "<3")),
    ]


def test_run_resolve_job_selects_highest_matching_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "pkg_proxy_stress.http_ops.fetch_text",
        lambda _url, *, timeout: (
            """
        <html><body>
          <a href=\"urllib3-3.0.0-py3-none-any.whl\">3.0.0</a>
          <a href=\"urllib3-2.0.7-py3-none-any.whl\">2.0.7</a>
          <a href=\"urllib3-1.26.18-py3-none-any.whl\">1.26.18</a>
        </body></html>
        """
        ),
    )

    result = run_resolve_job(
        INDEX_URL,
        ResolveJob(
            name="resolve:urllib3:#1",
            package="urllib3",
            requirements=(">=1.26", "<3"),
        ),
        timeout=1.0,
    )

    assert result.ok is True
    assert result.selected_version == "2.0.7"
    assert result.candidate_count == 3


@pytest.mark.parametrize(
    ("pip_args", "expected_suffix"),
    [
        (
            ("download", "--no-deps", "requests==2.31.0"),
            [
                "download",
                "--dest",
                "/tmp/downloads",
                "--progress-bar",
                "off",
                "--no-cache-dir",
                "--index-url",
                INDEX_URL,
                "--no-deps",
                "requests==2.31.0",
            ],
        ),
        (
            ("install", "requests==2.31.0"),
            [
                "install",
                "--progress-bar",
                "off",
                "--no-cache-dir",
                "--index-url",
                INDEX_URL,
                "requests==2.31.0",
            ],
        ),
        (
            ("index", "versions", "requests"),
            ["index", "--index-url", INDEX_URL, "versions", "requests"],
        ),
    ],
)
def test_build_pip_command_injects_mode_specific_flags(
    pip_args: tuple[str, ...], expected_suffix: list[str]
) -> None:
    command = build_pip_command("python", INDEX_URL, pip_args, Path("/tmp/downloads"))

    assert command[:5] == [
        "python",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--no-input",
    ]
    assert command[5:] == expected_suffix
