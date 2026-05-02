from dataclasses import dataclass
from packaging.version import Version


@dataclass(slots=True, frozen=True)
class ResolveScenario:
    package: str
    requirements: tuple[str, ...]
    expected_ok: bool = True


@dataclass(slots=True, frozen=True)
class PipScenario:
    pip_args: tuple[str, ...]
    expected_ok: bool = True


@dataclass(slots=True, frozen=True)
class HttpJob:
    name: str
    url: str


@dataclass(slots=True, frozen=True)
class ResolveJob:
    name: str
    package: str
    requirements: tuple[str, ...]
    expected_ok: bool = True


@dataclass(slots=True, frozen=True)
class PipJob:
    name: str
    pip_args: tuple[str, ...]
    expected_ok: bool = True


@dataclass(slots=True)
class HttpResult:
    name: str
    method: str
    url: str
    ok: bool
    status_code: int | None
    duration_s: float
    size_bytes: int
    detail: str = ""


@dataclass(slots=True)
class ResolveResult:
    name: str
    package: str
    requirements: tuple[str, ...]
    ok: bool
    duration_s: float
    selected_version: str | None
    candidate_count: int
    detail: str = ""
    expected_ok: bool = True


@dataclass(slots=True)
class PipResult:
    name: str
    command: list[str]
    ok: bool
    exit_code: int
    duration_s: float
    detail: str = ""
    expected_ok: bool = True


@dataclass(slots=True, frozen=True)
class ArtifactLink:
    url: str
    filename: str
    version: Version | None


@dataclass(slots=True, frozen=True)
class HttpCompleted:
    result: HttpResult


@dataclass(slots=True, frozen=True)
class ResolveCompleted:
    result: ResolveResult


@dataclass(slots=True, frozen=True)
class PipCompleted:
    result: PipResult


type CompletedJob = HttpCompleted | ResolveCompleted | PipCompleted
