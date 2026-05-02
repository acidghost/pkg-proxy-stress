from dataclasses import dataclass
from typing import Literal


type LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


@dataclass(slots=True, frozen=True)
class CommonOptions:
    index_url: str
    workers: int
    timeout: float
    log_level: LogLevelName

    def __post_init__(self) -> None:
        if not self.index_url:
            raise ValueError("index_url must not be empty")
        if self.workers < 1:
            raise ValueError("workers must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")


@dataclass(slots=True, frozen=True)
class RawCommand:
    kind: Literal["raw"]
    common: CommonOptions
    packages: tuple[str, ...]
    repeat: int

    def __post_init__(self) -> None:
        if self.repeat < 1:
            raise ValueError("repeat must be at least 1")


@dataclass(slots=True, frozen=True)
class ResolveCommand:
    kind: Literal["resolve"]
    common: CommonOptions
    package: str | None
    requirements: tuple[str, ...]
    scenarios: tuple[str, ...]
    repeat: int

    def __post_init__(self) -> None:
        if self.repeat < 1:
            raise ValueError("repeat must be at least 1")
        if self.package is not None and not self.requirements:
            raise ValueError("custom resolve runs require at least one requirement")


@dataclass(slots=True, frozen=True)
class PipCommand:
    kind: Literal["pip"]
    common: CommonOptions
    scenarios: tuple[str, ...]
    repeat: int
    python_executable: str

    def __post_init__(self) -> None:
        if self.repeat < 1:
            raise ValueError("repeat must be at least 1")
        if not self.python_executable:
            raise ValueError("python_executable must not be empty")


@dataclass(slots=True, frozen=True)
class MixedCommand:
    kind: Literal["mixed"]
    common: CommonOptions
    raw_repeat: int
    resolve_repeat: int
    pip_repeat: int
    python_executable: str

    def __post_init__(self) -> None:
        if self.raw_repeat < 1:
            raise ValueError("raw_repeat must be at least 1")
        if self.resolve_repeat < 1:
            raise ValueError("resolve_repeat must be at least 1")
        if self.pip_repeat < 1:
            raise ValueError("pip_repeat must be at least 1")
        if not self.python_executable:
            raise ValueError("python_executable must not be empty")


type Command = RawCommand | ResolveCommand | PipCommand | MixedCommand
