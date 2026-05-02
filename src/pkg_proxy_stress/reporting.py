from pkg_proxy_stress.models import HttpResult, PipResult, ResolveResult
from pkg_proxy_stress.utils import (
    expectation_label,
    indent,
    matched_expectation,
    print_latency_summary,
)


def print_http_summary(results: list[HttpResult]) -> None:
    total = len(results)
    ok = sum(1 for result in results if result.ok)
    print(f"raw requests: {ok}/{total} ok")

    durations = [result.duration_s for result in results]
    if durations:
        print_latency_summary(durations)

    failures = sorted(
        (result for result in results if not result.ok), key=lambda result: result.name
    )
    for result in failures[:5]:
        suffix = f" detail={result.detail}" if result.detail else ""
        print(f"  FAIL {result.name} status={result.status_code}{suffix}")


def print_resolve_summary(results: list[ResolveResult]) -> None:
    total = len(results)
    passed = sum(
        1 for result in results if matched_expectation(result.ok, result.expected_ok)
    )
    print(f"resolver runs: {passed}/{total} matched expectation")

    durations = [result.duration_s for result in results]
    if durations:
        print_latency_summary(durations)

    failures = sorted(
        (
            result
            for result in results
            if not matched_expectation(result.ok, result.expected_ok)
        ),
        key=lambda result: result.name,
    )
    for result in failures[:5]:
        print(
            "  FAIL "
            f"{result.name} package={result.package} requirements={','.join(result.requirements)} "
            f"expectation={expectation_label(result.expected_ok)} detail={result.detail}"
        )

    successes = sorted(
        (
            result
            for result in results
            if matched_expectation(result.ok, result.expected_ok)
        ),
        key=lambda result: result.name,
    )
    for result in successes[:5]:
        outcome = "OK" if result.ok else "EXPECTED-FAIL"
        print(
            f"  {outcome:<13} {result.name} package={result.package} "
            f"selected={result.selected_version} candidates={result.candidate_count}"
        )


def print_pip_summary(results: list[PipResult]) -> None:
    total = len(results)
    passed = sum(
        1 for result in results if matched_expectation(result.ok, result.expected_ok)
    )
    print(f"pip runs: {passed}/{total} matched expectation")

    durations = [result.duration_s for result in results]
    if durations:
        print_latency_summary(durations)

    for result in sorted(results, key=lambda result: result.name)[
        : min(8, len(results))
    ]:
        status = "OK" if matched_expectation(result.ok, result.expected_ok) else "FAIL"
        outcome = "ok" if result.ok else "fail"
        print(
            f"  {status:<4} {result.name} outcome={outcome} "
            f"expectation={expectation_label(result.expected_ok)} exit={result.exit_code} {result.duration_s:.2f}s"
        )
        if result.detail:
            print(indent(result.detail, "      "))
