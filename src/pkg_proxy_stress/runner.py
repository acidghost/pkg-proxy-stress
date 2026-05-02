import concurrent.futures
import logging

from pkg_proxy_stress.commands import (
    MixedCommand,
    PipCommand,
    RawCommand,
    ResolveCommand,
)
from pkg_proxy_stress.http_ops import run_http_job, run_resolve_job
from pkg_proxy_stress.models import (
    CompletedJob,
    HttpCompleted,
    HttpJob,
    PipCompleted,
    PipJob,
    ResolveCompleted,
    ResolveJob,
)
from pkg_proxy_stress.pip_ops import run_pip_job
from pkg_proxy_stress.reporting import (
    print_http_summary,
    print_pip_summary,
    print_resolve_summary,
)
from pkg_proxy_stress.utils import matched_expectation
from pkg_proxy_stress.workloads import (
    build_default_pip_jobs,
    build_default_raw_jobs,
    build_default_resolve_jobs,
    build_pip_jobs,
    build_raw_jobs,
    build_resolve_jobs,
)

LOGGER = logging.getLogger("pkg_proxy_stress")


def _worker_count(requested_workers: int, job_count: int) -> int:
    return min(requested_workers, job_count or 1)


def run_raw(command: RawCommand) -> int:
    jobs = build_raw_jobs(
        command.common.index_url,
        command.packages,
        command.repeat,
    )
    worker_count = _worker_count(command.common.workers, len(jobs))
    LOGGER.info("running raw workload jobs=%s workers=%s", len(jobs), worker_count)

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(run_http_job, job, command.common.timeout) for job in jobs
        ]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    print_http_summary(results)
    return 0 if all(result.ok for result in results) else 1


def run_resolve(command: ResolveCommand) -> int:
    jobs = build_resolve_jobs(
        scenario_names=command.scenarios,
        repeat=command.repeat,
        package=command.package,
        requirements=command.requirements,
    )
    worker_count = _worker_count(command.common.workers, len(jobs))
    LOGGER.info("running resolver workload jobs=%s workers=%s", len(jobs), worker_count)

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                run_resolve_job,
                command.common.index_url,
                job,
                command.common.timeout,
            )
            for job in jobs
        ]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    print_resolve_summary(results)
    return (
        0
        if all(matched_expectation(result.ok, result.expected_ok) for result in results)
        else 1
    )


def run_pip(command: PipCommand) -> int:
    jobs = build_pip_jobs(command.scenarios, command.repeat)
    worker_count = _worker_count(command.common.workers, len(jobs))
    LOGGER.info("running pip workload jobs=%s workers=%s", len(jobs), worker_count)

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                run_pip_job,
                command.common.index_url,
                command.python_executable,
                job,
                command.common.timeout,
            )
            for job in jobs
        ]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    print_pip_summary(results)
    return (
        0
        if all(matched_expectation(result.ok, result.expected_ok) for result in results)
        else 1
    )


def _run_completed_raw_job(job: HttpJob, timeout: float) -> CompletedJob:
    return HttpCompleted(result=run_http_job(job, timeout))


def _run_completed_resolve_job(
    index_url: str, timeout: float, job: ResolveJob
) -> CompletedJob:
    return ResolveCompleted(result=run_resolve_job(index_url, job, timeout))


def _run_completed_pip_job(
    index_url: str,
    python_executable: str,
    timeout: float,
    job: PipJob,
) -> CompletedJob:
    return PipCompleted(result=run_pip_job(index_url, python_executable, job, timeout))


def run_mixed(command: MixedCommand) -> int:
    raw_jobs = build_default_raw_jobs(command.common.index_url, command.raw_repeat)
    resolve_jobs = build_default_resolve_jobs(command.resolve_repeat)
    pip_jobs = build_default_pip_jobs(command.pip_repeat)
    worker_count = _worker_count(
        command.common.workers,
        len(raw_jobs) + len(resolve_jobs) + len(pip_jobs),
    )

    LOGGER.info(
        "running mixed workload raw_jobs=%s resolve_jobs=%s pip_jobs=%s workers=%s",
        len(raw_jobs),
        len(resolve_jobs),
        len(pip_jobs),
        worker_count,
    )

    http_results = []
    resolve_results = []
    pip_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures: list[concurrent.futures.Future[CompletedJob]] = []
        futures.extend(
            executor.submit(_run_completed_raw_job, job, command.common.timeout)
            for job in raw_jobs
        )
        futures.extend(
            executor.submit(
                _run_completed_resolve_job,
                command.common.index_url,
                command.common.timeout,
                job,
            )
            for job in resolve_jobs
        )
        futures.extend(
            executor.submit(
                _run_completed_pip_job,
                command.common.index_url,
                command.python_executable,
                command.common.timeout,
                job,
            )
            for job in pip_jobs
        )

        for future in concurrent.futures.as_completed(futures):
            completed = future.result()
            if isinstance(completed, HttpCompleted):
                http_results.append(completed.result)
            elif isinstance(completed, ResolveCompleted):
                resolve_results.append(completed.result)
            else:
                pip_results.append(completed.result)

    print_http_summary(http_results)
    print()
    print_resolve_summary(resolve_results)
    print()
    print_pip_summary(pip_results)

    ok = all(result.ok for result in http_results)
    ok = ok and all(
        matched_expectation(result.ok, result.expected_ok) for result in resolve_results
    )
    ok = ok and all(
        matched_expectation(result.ok, result.expected_ok) for result in pip_results
    )
    return 0 if ok else 1
