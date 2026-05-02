import html.parser
import logging
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from packaging.specifiers import SpecifierSet
from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.version import Version

from pkg_proxy_stress.models import (
    ArtifactLink,
    HttpJob,
    HttpResult,
    ResolveJob,
    ResolveResult,
)
from pkg_proxy_stress.settings import USER_AGENT
from pkg_proxy_stress.utils import (
    expectation_label,
    simple_package_url,
    version_satisfies,
)

LOGGER = logging.getLogger("pkg_proxy_stress")
_VERSION_FALLBACK = re.compile(r"-(\d+(?:\.\d+)*(?:[A-Za-z0-9_.+-]*)?)")


class SimpleIndexParser(html.parser.HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        for key, value in attrs:
            if key == "href" and value:
                self.links.append(urljoin(self.base_url, value))
                return


def http_get(url: str, timeout: float, name: str) -> HttpResult:
    LOGGER.debug(
        "starting http request name=%s url=%s timeout=%.1fs", name, url, timeout
    )
    request = Request(url, headers={"User-Agent": USER_AGENT})
    start_time = time.perf_counter()

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            duration_s = time.perf_counter() - start_time
            result = HttpResult(
                name=name,
                method="GET",
                url=url,
                ok=200 <= response.status < 400,
                status_code=response.status,
                duration_s=duration_s,
                size_bytes=len(body),
            )
            LOGGER.info(
                "http request finished name=%s status=%s duration=%.3fs bytes=%s",
                name,
                result.status_code,
                result.duration_s,
                result.size_bytes,
            )
            return result
    except HTTPError as exc:
        duration_s = time.perf_counter() - start_time
        body = exc.read()
        result = HttpResult(
            name=name,
            method="GET",
            url=url,
            ok=False,
            status_code=exc.code,
            duration_s=duration_s,
            size_bytes=len(body),
            detail=str(exc),
        )
        LOGGER.warning(
            "http request failed name=%s status=%s duration=%.3fs detail=%s",
            name,
            result.status_code,
            result.duration_s,
            result.detail,
        )
        return result
    except URLError as exc:
        duration_s = time.perf_counter() - start_time
        result = HttpResult(
            name=name,
            method="GET",
            url=url,
            ok=False,
            status_code=None,
            duration_s=duration_s,
            size_bytes=0,
            detail=str(exc.reason),
        )
        LOGGER.warning(
            "http request failed name=%s duration=%.3fs detail=%s",
            name,
            result.duration_s,
            result.detail,
        )
        return result
    except Exception as exc:  # pragma: no cover - defensive
        duration_s = time.perf_counter() - start_time
        result = HttpResult(
            name=name,
            method="GET",
            url=url,
            ok=False,
            status_code=None,
            duration_s=duration_s,
            size_bytes=0,
            detail=repr(exc),
        )
        LOGGER.exception(
            "http request crashed name=%s duration=%.3fs", name, result.duration_s
        )
        return result


def run_http_job(job: HttpJob, timeout: float) -> HttpResult:
    return http_get(job.url, timeout, job.name)


def fetch_text(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_version_from_filename(filename: str) -> Version | None:
    try:
        if filename.endswith(".whl"):
            _, version, _, _ = parse_wheel_filename(filename)
            return version
    except Exception:
        pass

    try:
        if any(
            filename.endswith(suffix)
            for suffix in (".zip", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz")
        ):
            _, version = parse_sdist_filename(filename)
            return version
    except Exception:
        pass

    match = _VERSION_FALLBACK.search(filename)
    if not match:
        return None

    try:
        return Version(match.group(1))
    except Exception:
        return None


def parse_simple_page(page_url: str, html_text: str) -> list[ArtifactLink]:
    parser = SimpleIndexParser(page_url)
    parser.feed(html_text)

    links: list[ArtifactLink] = []
    for url in parser.links:
        filename = Path(urlparse(url).path).name
        if not filename:
            continue

        links.append(
            ArtifactLink(
                url=url,
                filename=filename,
                version=parse_version_from_filename(filename),
            )
        )

    LOGGER.debug("parsed simple page url=%s links=%s", page_url, len(links))
    return links


def choose_version(
    links: Iterable[ArtifactLink], requirements: tuple[str, ...]
) -> tuple[Version | None, int]:
    specifier_set = SpecifierSet(",".join(requirements))
    versions = sorted(
        {link.version for link in links if link.version is not None}, reverse=True
    )

    for version in versions:
        if version_satisfies(version, specifier_set):
            return version, len(versions)

    return None, len(versions)


def run_resolve_job(index_url: str, job: ResolveJob, timeout: float) -> ResolveResult:
    url = simple_package_url(index_url, job.package)
    LOGGER.debug(
        "starting resolve scenario name=%s package=%s requirements=%s timeout=%.1fs expectation=%s",
        job.name,
        job.package,
        job.requirements,
        timeout,
        expectation_label(job.expected_ok),
    )
    start_time = time.perf_counter()

    try:
        html_text = fetch_text(url, timeout=timeout)
        links = parse_simple_page(url, html_text)
        version, candidate_count = choose_version(links, job.requirements)
        duration_s = time.perf_counter() - start_time

        if version is None:
            result = ResolveResult(
                name=job.name,
                package=job.package,
                requirements=job.requirements,
                ok=False,
                duration_s=duration_s,
                selected_version=None,
                candidate_count=candidate_count,
                detail="no version satisfied all requirements",
                expected_ok=job.expected_ok,
            )
            log_fn = LOGGER.warning if job.expected_ok else LOGGER.info
            log_fn(
                "resolve scenario finished name=%s package=%s candidates=%s duration=%.3fs outcome=fail expectation=%s detail=%s",
                job.name,
                job.package,
                candidate_count,
                duration_s,
                expectation_label(job.expected_ok),
                result.detail,
            )
            return result

        result = ResolveResult(
            name=job.name,
            package=job.package,
            requirements=job.requirements,
            ok=True,
            duration_s=duration_s,
            selected_version=str(version),
            candidate_count=candidate_count,
            expected_ok=job.expected_ok,
        )
        log_fn = LOGGER.info if job.expected_ok else LOGGER.warning
        log_fn(
            "resolve scenario finished name=%s package=%s selected=%s candidates=%s duration=%.3fs outcome=ok expectation=%s",
            job.name,
            job.package,
            result.selected_version,
            candidate_count,
            duration_s,
            expectation_label(job.expected_ok),
        )
        return result
    except HTTPError as exc:
        duration_s = time.perf_counter() - start_time
        result = ResolveResult(
            name=job.name,
            package=job.package,
            requirements=job.requirements,
            ok=False,
            duration_s=duration_s,
            selected_version=None,
            candidate_count=0,
            detail=f"HTTP {exc.code}",
            expected_ok=job.expected_ok,
        )
        log_fn = LOGGER.warning if job.expected_ok else LOGGER.info
        log_fn(
            "resolve scenario finished name=%s package=%s duration=%.3fs outcome=fail expectation=%s detail=%s",
            job.name,
            job.package,
            duration_s,
            expectation_label(job.expected_ok),
            result.detail,
        )
        return result
    except Exception as exc:
        duration_s = time.perf_counter() - start_time
        result = ResolveResult(
            name=job.name,
            package=job.package,
            requirements=job.requirements,
            ok=False,
            duration_s=duration_s,
            selected_version=None,
            candidate_count=0,
            detail=repr(exc),
            expected_ok=job.expected_ok,
        )
        LOGGER.exception(
            "resolve scenario crashed name=%s package=%s duration=%.3fs expectation=%s",
            job.name,
            job.package,
            duration_s,
            expectation_label(job.expected_ok),
        )
        return result
