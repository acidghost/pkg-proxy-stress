from pkg_proxy_stress.models import PipScenario, ResolveScenario

DEFAULT_TIMEOUT = 30.0
DEFAULT_WORKERS = 8
USER_AGENT = "pkg-proxy-stress/0.0.0"

DEFAULT_RAW_PACKAGES = [
    "pip",
    "setuptools",
    "wheel",
    "packaging",
    "requests",
    "urllib3",
    "charset-normalizer",
    "idna",
    "certifi",
    "pydantic",
    "fastapi",
    "numpy",
    "httpx",
    "openai",
    "tiktoken",
    "tokenizers",
    "aiohttp",
    "boto3",
    "litellm",
    "uvicorn",
    "rich",
]

DEFAULT_RESOLVE_SCENARIOS = {
    "urllib3-compatible": ResolveScenario(
        package="urllib3",
        requirements=(">=1.26", "<3", "!=2.0.0", "!=2.0.1", "!=2.0.2"),
    ),
    "requests-2x": ResolveScenario(
        package="requests",
        requirements=(">=2.28", "<3", "!=2.32.0"),
    ),
    "pydantic-v2": ResolveScenario(
        package="pydantic",
        requirements=(">=2", "<3", "!=2.5.0"),
    ),
    "fastapi-stable": ResolveScenario(
        package="fastapi",
        requirements=(">=0.100", "<1"),
    ),
    "httpx-pinned": ResolveScenario(
        package="httpx",
        requirements=("==0.28.1",),
    ),
    "tokenizers-pinned": ResolveScenario(
        package="tokenizers",
        requirements=("==0.22.2",),
    ),
    "openai-v2": ResolveScenario(
        package="openai",
        requirements=(">=2", "<3"),
    ),
    "litellm-current": ResolveScenario(
        package="litellm",
        requirements=(">1.83.0",),
    ),
    "litellm-unsat-self-range": ResolveScenario(
        package="litellm",
        requirements=(">1.83.0", "<1.83.0"),
        expected_ok=False,
    ),
    "litellm-unsat-self-exact": ResolveScenario(
        package="litellm",
        requirements=(">1.83.0", "==1.83.0"),
        expected_ok=False,
    ),
}

DEFAULT_PIP_SCENARIOS = {
    "index-versions-requests": PipScenario(
        pip_args=("index", "versions", "requests"),
    ),
    "index-versions-litellm": PipScenario(
        pip_args=("index", "versions", "litellm"),
    ),
    "download-wheel": PipScenario(
        pip_args=("download", "--no-deps", "requests==2.31.0"),
    ),
    "download-tokenizers-wheel": PipScenario(
        pip_args=("download", "--no-deps", "tokenizers==0.22.2"),
    ),
    "resolve-web-stack": PipScenario(
        pip_args=(
            "install",
            "requests>=2.31,<3",
            "urllib3>=1.26,<3",
            "fastapi>=0.100,<1",
            "httpx>=0.27,<1",
        ),
    ),
    "resolve-aws-stack": PipScenario(
        pip_args=(
            "install",
            "boto3>=1.34,<2",
            "requests>=2.31,<3",
        ),
    ),
    "resolve-async-stack": PipScenario(
        pip_args=(
            "install",
            "aiohttp==3.13.4",
            "httpx==0.28.1",
            "websockets==15.0.1",
        ),
    ),
    "resolve-llm-clients": PipScenario(
        pip_args=(
            "install",
            "openai==2.24.0",
            "anthropic==0.84.0",
            "tiktoken==0.12.0",
            "httpx==0.28.1",
            "pydantic==2.12.5",
        ),
    ),
    "resolve-proxy-basics": PipScenario(
        pip_args=(
            "install",
            "fastapi==0.124.4",
            "uvicorn==0.33.0",
            "orjson==3.11.6",
            "python-multipart==0.0.26",
            "pyyaml==6.0.3",
        ),
    ),
    "resolve-litellm-core": PipScenario(
        pip_args=("install", "litellm>1.83.0"),
    ),
    "conflict-litellm-self-range": PipScenario(
        pip_args=("install", "litellm>1.83.0", "litellm<1.83.0"),
        expected_ok=False,
    ),
    "conflict-litellm-pydantic": PipScenario(
        pip_args=("install", "litellm>1.83.0", "pydantic==1.10.0"),
        expected_ok=False,
    ),
    "conflict-litellm-httpx": PipScenario(
        pip_args=("install", "litellm>1.83.0", "httpx==0.27.0"),
        expected_ok=False,
    ),
}
