from collections.abc import Sequence

from pkg_proxy_stress.models import HttpJob, PipJob, ResolveJob
from pkg_proxy_stress.settings import (
    DEFAULT_PIP_SCENARIOS,
    DEFAULT_RAW_PACKAGES,
    DEFAULT_RESOLVE_SCENARIOS,
)
from pkg_proxy_stress.utils import simple_package_url, simple_root_url


def build_raw_jobs(
    index_url: str, packages: Sequence[str], repeat: int
) -> list[HttpJob]:
    jobs = [HttpJob(name="simple-root", url=simple_root_url(index_url))]
    for iteration in range(1, repeat + 1):
        for package in packages:
            jobs.append(
                HttpJob(
                    name=f"raw:{package}:#{iteration}",
                    url=simple_package_url(index_url, package),
                )
            )
    return jobs


def build_default_raw_jobs(index_url: str, repeat: int) -> list[HttpJob]:
    return build_raw_jobs(
        index_url=index_url, packages=DEFAULT_RAW_PACKAGES, repeat=repeat
    )


def build_resolve_jobs(
    scenario_names: Sequence[str],
    repeat: int,
    package: str | None = None,
    requirements: Sequence[str] | None = None,
) -> list[ResolveJob]:
    jobs: list[ResolveJob] = []

    selected_names = scenario_names or (
        () if package is not None else DEFAULT_RESOLVE_SCENARIOS
    )
    for scenario_name in selected_names:
        scenario = DEFAULT_RESOLVE_SCENARIOS[scenario_name]
        for iteration in range(1, repeat + 1):
            jobs.append(
                ResolveJob(
                    name=f"resolve:{scenario_name}:#{iteration}",
                    package=scenario.package,
                    requirements=scenario.requirements,
                    expected_ok=scenario.expected_ok,
                )
            )

    if package is not None:
        if not requirements:
            raise SystemExit("custom resolve runs require at least one --requirement")
        for iteration in range(1, repeat + 1):
            jobs.append(
                ResolveJob(
                    name=f"resolve:{package}:#{iteration}",
                    package=package,
                    requirements=tuple(requirements),
                )
            )

    return jobs


def build_default_resolve_jobs(repeat: int) -> list[ResolveJob]:
    return build_resolve_jobs(
        scenario_names=list(DEFAULT_RESOLVE_SCENARIOS), repeat=repeat
    )


def build_pip_jobs(scenario_names: Sequence[str], repeat: int) -> list[PipJob]:
    selected_names = scenario_names or list(DEFAULT_PIP_SCENARIOS)
    jobs: list[PipJob] = []
    for scenario_name in selected_names:
        scenario = DEFAULT_PIP_SCENARIOS[scenario_name]
        for iteration in range(1, repeat + 1):
            jobs.append(
                PipJob(
                    name=f"pip:{scenario_name}:#{iteration}",
                    pip_args=scenario.pip_args,
                    expected_ok=scenario.expected_ok,
                )
            )
    return jobs


def build_default_pip_jobs(repeat: int) -> list[PipJob]:
    return build_pip_jobs(scenario_names=list(DEFAULT_PIP_SCENARIOS), repeat=repeat)
