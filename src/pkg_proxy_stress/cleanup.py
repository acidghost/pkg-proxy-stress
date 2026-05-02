import atexit
import logging
import shutil
import threading
import time
from pathlib import Path

LOGGER = logging.getLogger("pkg_proxy_stress")
_CLEANUP_LOCK = threading.Lock()
_DEFERRED_CLEANUP_PATHS: set[Path] = set()


def register_deferred_cleanup(path: Path) -> None:
    with _CLEANUP_LOCK:
        _DEFERRED_CLEANUP_PATHS.add(path)


def cleanup_path(
    path: Path, name: str, attempts: int = 8, base_delay_s: float = 0.1
) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            shutil.rmtree(path)
            LOGGER.debug("cleaned temporary directory name=%s path=%s", name, path)
            return True
        except FileNotFoundError:
            return True
        except OSError as exc:
            if attempt == attempts:
                LOGGER.error(
                    "failed to clean temporary directory name=%s path=%s attempts=%s detail=%s",
                    name,
                    path,
                    attempts,
                    exc,
                )
                register_deferred_cleanup(path)
                return False

            delay_s = min(1.0, base_delay_s * attempt)
            LOGGER.warning(
                "retrying temporary directory cleanup name=%s path=%s attempt=%s/%s delay=%.2fs detail=%s",
                name,
                path,
                attempt,
                attempts,
                delay_s,
                exc,
            )
            time.sleep(delay_s)

    return False


def cleanup_deferred_paths() -> None:
    with _CLEANUP_LOCK:
        paths = tuple(sorted(_DEFERRED_CLEANUP_PATHS, key=lambda path: str(path)))
        _DEFERRED_CLEANUP_PATHS.clear()

    for path in paths:
        if cleanup_path(path, name="atexit", attempts=3, base_delay_s=0.2):
            LOGGER.info("cleaned deferred temporary directory path=%s", path)
        else:
            LOGGER.error("deferred temporary directory still present path=%s", path)


atexit.register(cleanup_deferred_paths)
