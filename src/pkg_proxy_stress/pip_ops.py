import logging
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

from pkg_proxy_stress.cleanup import cleanup_path
from pkg_proxy_stress.models import PipJob, PipResult
from pkg_proxy_stress.utils import (
    coerce_text,
    expectation_label,
    is_install_command,
    matched_expectation,
    remaining_timeout,
    summarize_output,
    venv_python_path,
)

LOGGER = logging.getLogger("pkg_proxy_stress")


def build_pip_command(
    python_executable: str,
    index_url: str,
    pip_args: tuple[str, ...],
    download_dir: Path,
) -> list[str]:
    command = [
        python_executable,
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--no-input",
    ]

    if pip_args and pip_args[0] == "download":
        command.extend(
            [
                "download",
                "--dest",
                str(download_dir),
                "--progress-bar",
                "off",
                "--no-cache-dir",
                "--index-url",
                index_url,
            ]
        )
        command.extend(pip_args[1:])
        return command

    if pip_args and pip_args[0] == "install":
        command.extend(
            [
                "install",
                "--progress-bar",
                "off",
                "--no-cache-dir",
                "--index-url",
                index_url,
            ]
        )
        command.extend(pip_args[1:])
        return command

    if pip_args and pip_args[0] == "index":
        command.extend(
            [
                "index",
                "--index-url",
                index_url,
            ]
        )
        command.extend(pip_args[1:])
        return command

    command.extend(pip_args)
    return command


def _subprocess_detail(exc: subprocess.TimeoutExpired) -> str:
    output = "\n".join([coerce_text(exc.stdout), coerce_text(exc.stderr)]).strip()
    return summarize_output(output)


def _run_subprocess(
    command: list[str],
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _create_install_runner(
    python_executable: str,
    temp_path: Path,
    env: dict[str, str],
    start_time: float,
    timeout: float,
    name: str,
    expected_ok: bool,
) -> tuple[str, PipResult | None]:
    venv_dir = temp_path / "venv"
    venv_command = [python_executable, "-m", "venv", str(venv_dir)]
    LOGGER.info("creating ad-hoc venv for pip install name=%s path=%s", name, venv_dir)
    LOGGER.debug("venv command name=%s command=%s", name, shlex.join(venv_command))

    try:
        completed = _run_subprocess(
            venv_command,
            env=env,
            timeout=remaining_timeout(start_time, timeout),
        )
    except subprocess.TimeoutExpired as exc:
        duration_s = time.perf_counter() - start_time
        detail = (
            _subprocess_detail(exc) or f"venv creation timed out after {timeout:.1f}s"
        )
        LOGGER.warning(
            "pip scenario venv creation timed out name=%s duration=%.3fs timeout=%.1fs command=%s",
            name,
            duration_s,
            timeout,
            shlex.join(venv_command),
        )
        return python_executable, PipResult(
            name=name,
            command=venv_command,
            ok=False,
            exit_code=124,
            duration_s=duration_s,
            detail=detail,
            expected_ok=expected_ok,
        )

    output = "\n".join(
        [coerce_text(completed.stdout), coerce_text(completed.stderr)]
    ).strip()
    if completed.returncode != 0:
        duration_s = time.perf_counter() - start_time
        detail = summarize_output(output) or "venv creation failed"
        LOGGER.warning(
            "pip scenario venv creation failed name=%s exit=%s duration=%.3fs command=%s",
            name,
            completed.returncode,
            duration_s,
            shlex.join(venv_command),
        )
        return python_executable, PipResult(
            name=name,
            command=venv_command,
            ok=False,
            exit_code=completed.returncode,
            duration_s=duration_s,
            detail=detail,
            expected_ok=expected_ok,
        )

    runner_python = str(venv_python_path(venv_dir))
    LOGGER.info(
        "created ad-hoc venv for pip install name=%s python=%s", name, runner_python
    )
    return runner_python, None


def run_pip_job(
    index_url: str,
    python_executable: str,
    job: PipJob,
    timeout: float,
) -> PipResult:
    start_time = time.perf_counter()
    temp_path = Path(tempfile.mkdtemp(prefix="pkg-proxy-stress-"))
    LOGGER.debug("created temporary directory name=%s path=%s", job.name, temp_path)

    try:
        download_dir = temp_path / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
        env.setdefault("PIP_NO_INPUT", "1")

        runner_python = python_executable
        if is_install_command(job.pip_args):
            runner_python, early_result = _create_install_runner(
                python_executable=python_executable,
                temp_path=temp_path,
                env=env,
                start_time=start_time,
                timeout=timeout,
                name=job.name,
                expected_ok=job.expected_ok,
            )
            if early_result is not None:
                return early_result

        command = build_pip_command(
            runner_python, index_url, job.pip_args, download_dir
        )
        LOGGER.info(
            "starting pip scenario name=%s expectation=%s",
            job.name,
            expectation_label(job.expected_ok),
        )
        LOGGER.debug("pip command name=%s command=%s", job.name, shlex.join(command))

        try:
            completed = _run_subprocess(
                command,
                env=env,
                timeout=remaining_timeout(start_time, timeout),
            )
        except subprocess.TimeoutExpired as exc:
            duration_s = time.perf_counter() - start_time
            detail = _subprocess_detail(exc) or f"timed out after {timeout:.1f}s"
            log_fn = LOGGER.warning if job.expected_ok else LOGGER.info
            log_fn(
                "pip scenario timed out name=%s duration=%.3fs timeout=%.1fs expectation=%s command=%s",
                job.name,
                duration_s,
                timeout,
                expectation_label(job.expected_ok),
                shlex.join(command),
            )
            return PipResult(
                name=job.name,
                command=command,
                ok=False,
                exit_code=124,
                duration_s=duration_s,
                detail=detail,
                expected_ok=job.expected_ok,
            )

        duration_s = time.perf_counter() - start_time
        output = "\n".join(
            [coerce_text(completed.stdout), coerce_text(completed.stderr)]
        ).strip()
        result = PipResult(
            name=job.name,
            command=command,
            ok=completed.returncode == 0,
            exit_code=completed.returncode,
            duration_s=duration_s,
            detail=summarize_output(output),
            expected_ok=job.expected_ok,
        )

        if matched_expectation(result.ok, result.expected_ok):
            LOGGER.info(
                "pip scenario finished name=%s exit=%s duration=%.3fs outcome=%s expectation=%s",
                job.name,
                result.exit_code,
                result.duration_s,
                "ok" if result.ok else "fail",
                expectation_label(result.expected_ok),
            )
        else:
            LOGGER.warning(
                "pip scenario finished name=%s exit=%s duration=%.3fs outcome=%s expectation=%s command=%s",
                job.name,
                result.exit_code,
                result.duration_s,
                "ok" if result.ok else "fail",
                expectation_label(result.expected_ok),
                shlex.join(command),
            )
        return result
    finally:
        cleaned = cleanup_path(temp_path, name=job.name)
        if not cleaned:
            LOGGER.error(
                "temporary directory cleanup deferred name=%s path=%s",
                job.name,
                temp_path,
            )
