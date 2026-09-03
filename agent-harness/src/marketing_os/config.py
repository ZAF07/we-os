"""Runtime configuration for the Marketing OS harness.

Everything that varies between deployments resolves here from environment
variables with sensible defaults: which provider and model are active, where the
Marketing OS repo root lives, and the loop and QA limits. The same code therefore
runs locally, in CI, and in a backend by changing environment only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from marketing_os.errors import ConfigError

_CLAUDE_DIR_NAME = ".claude"


class WebBackend(StrEnum):
    """A selectable web-search backend for the fallback chain.

    Attributes:
        TAVILY: The Tavily JSON-API retrieval backend.
        GOOGLE: The Google-scraping Playwright backend.
        DUCKDUCKGO: The DuckDuckGo-scraping Playwright backend.
        NOOP: The no-op backend reporting that web search is unavailable.
    """

    TAVILY = "tavily"
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    NOOP = "noop"


_DEFAULT_WEB_BACKENDS = (WebBackend.TAVILY, WebBackend.GOOGLE, WebBackend.DUCKDUCKGO)

_VALID_SEARCH_DEPTHS = ("basic", "advanced")
_DEFAULT_SEARCH_DEPTH = "basic"


def _parse_search_depth(raw: str) -> str:
    """Validate the Tavily search-depth selector.

    Args:
        raw: The ``MARKETING_OS_TAVILY_SEARCH_DEPTH`` value.

    Returns:
        The lowercased depth (``basic`` or ``advanced``); the default when the
        value is empty.

    Raises:
        ConfigError: If the value is neither ``basic`` nor ``advanced``.
    """
    token = raw.strip().lower()
    if not token:
        return _DEFAULT_SEARCH_DEPTH
    if token not in _VALID_SEARCH_DEPTHS:
        known = ", ".join(_VALID_SEARCH_DEPTHS)
        raise ConfigError(
            f"Unknown Tavily search depth '{token}' in MARKETING_OS_TAVILY_SEARCH_DEPTH. "
            f"Known: {known}."
        )
    return token


def _parse_web_backends(raw: str) -> list[WebBackend]:
    """Parse the ordered web-backend selector into validated backends.

    Args:
        raw: The comma-separated ``MARKETING_OS_WEB_BACKENDS`` value.

    Returns:
        The selected backends in priority order, empty entries dropped; the
        default order (Google then DuckDuckGo) when nothing usable is given.

    Raises:
        ConfigError: If the value names a backend that does not exist.
    """
    tokens = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not tokens:
        return list(_DEFAULT_WEB_BACKENDS)
    backends: list[WebBackend] = []
    for token in tokens:
        try:
            backends.append(WebBackend(token))
        except ValueError as exc:
            known = ", ".join(member.value for member in WebBackend)
            raise ConfigError(
                f"Unknown web backend '{token}' in MARKETING_OS_WEB_BACKENDS. Known: {known}."
            ) from exc
    return backends


def _parse_human_gate_stages(raw: str | None) -> list[str] | None:
    """Parse which pipeline stages halt at an Approval Gate.

    An unset variable means "keep the shipped defaults", which is different from
    an empty one: setting ``MARKETING_OS_HUMAN_GATES=`` deliberately turns every
    gate off, and that must not be silently read as "no configuration given".

    Args:
        raw: The comma-separated ``MARKETING_OS_HUMAN_GATES`` value, or ``None``
            when the variable is unset.

    Returns:
        The stage keys requiring human approval, or ``None`` when unset.

    Raises:
        ConfigError: If the value names a stage the pipeline does not have.
    """
    if raw is None:
        return None
    from marketing_os.governance.pipeline import PIPELINE_BY_KEY

    keys = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [key for key in keys if key not in PIPELINE_BY_KEY]
    if unknown:
        known = ", ".join(PIPELINE_BY_KEY)
        raise ConfigError(
            f"Unknown stage(s) in MARKETING_OS_HUMAN_GATES: {', '.join(unknown)}. Known: {known}."
        )
    return keys


_DEFAULT_TOKEN_RATE = 0.000002


def _parse_token_rates(raw: str) -> dict[str, float]:
    """Parse the per-model token price list the ledger costs calls with.

    Prices belong in configuration rather than in code because a provider
    changes them without asking, and a stale hard-coded rate makes the whole
    Usage Ledger quietly wrong (ADR-0020).

    Args:
        raw: The ``MARKETING_OS_TOKEN_RATES`` value, as comma-separated
            ``model=price-per-token`` pairs.

    Returns:
        The rate per model, empty when nothing usable is given — in which case
        the ledger falls back to :data:`_DEFAULT_TOKEN_RATE`.

    Raises:
        ConfigError: If a pair is malformed or its price is not a number.
    """
    rates: dict[str, float] = {}
    for item in raw.split(","):
        pair = item.strip()
        if not pair:
            continue
        model, separator, price = pair.partition("=")
        if not separator or not model.strip():
            raise ConfigError(
                f"Malformed entry '{pair}' in MARKETING_OS_TOKEN_RATES. "
                "Use model=price-per-token, comma-separated."
            )
        try:
            rates[model.strip()] = float(price.strip())
        except ValueError as exc:
            raise ConfigError(
                f"Price '{price.strip()}' for model '{model.strip()}' in "
                "MARKETING_OS_TOKEN_RATES is not a number."
            ) from exc
    return rates


class Role(StrEnum):
    """A model role whose per-role overrides the settings may resolve.

    Attributes:
        REVIEWER: The QA judge role, which may use a cheaper model.
        DEFAULT: The default specialist role.
    """

    REVIEWER = "reviewer"
    DEFAULT = "default"


def _discover_root() -> Path:
    """Locate the Marketing OS repository root.

    Resolution order: the ``MARKETING_OS_ROOT`` environment variable if set,
    otherwise the nearest ancestor directory that contains a ``.claude/`` folder,
    otherwise the current working directory as a last resort.

    Returns:
        The resolved absolute path to the repository root.
    """
    env = os.environ.get("MARKETING_OS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / _CLAUDE_DIR_NAME).is_dir():
            return parent
    return Path.cwd().resolve()


@dataclass
class ProviderConfig:
    """Connection details for one chat-model provider.

    Attributes:
        model: The model identifier passed to the LangChain chat model.
        api_key: The API key, or ``None`` to fall back to the provider SDK default.
        base_url: An override base URL, or ``None`` for the provider default.
    """

    model: str
    api_key: str | None = None
    base_url: str | None = None


_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "model_env": "DEEPSEEK_MODEL",
        "reviewer_model_default": "deepseek-v4-flash",
        "model_default": "deepseek-v4-pro",
        "key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com",
    },
    "anthropic": {
        "model_env": "ANTHROPIC_MODEL",
        "model_default": "claude-opus-4-8",
        "key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "base_url_default": "",
    },
    "openai": {
        "model_env": "OPENAI_MODEL",
        "model_default": "",
        "key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "base_url_default": "",
    },
}


@dataclass
class Settings:
    """Top-level harness configuration resolved from the environment.

    Attributes:
        provider: The active provider name (``deepseek`` | ``anthropic`` | ``openai``).
        root: The Marketing OS repository root.
        max_steps: The tool-call budget bounding each specialist's inner loop.
        max_qa_iterations: The revision budget for the per-stage QA loop.
        human_gate_stages: The stage keys that halt at an Approval Gate, or
            ``None`` to keep each stage's shipped policy. The approval policy is
            data, so tightening or loosening the gates is a configuration change
            rather than a rewrite (ADR-0015).
        max_revisions: How many times one deliverable may be sent back with
            written feedback, so a single item cannot burn a whole allowance.
        max_runs_per_campaign: How many runs one campaign may accumulate. The
            companion cap to ``max_revisions``: that bounds re-working one
            deliverable, this bounds re-running the whole campaign (ADR-0020).
        usage_allowance: What a tenant may spend before billable work is
            refused, in the platform's accounting currency. The platform-wide
            default; a tenant may carry its own override, so raising one
            business's cap is a row rather than a deploy. How the allowance is
            *presented* — credits, fair use, metered billing — is deliberately
            not decided here (ADR-0020).
        token_rates: The price per token per model the Usage Ledger costs calls
            with, from ``MARKETING_OS_TOKEN_RATES`` as ``model=price`` pairs. A
            model with no configured rate is costed at the default rate.
        stream: Whether the CLI streams progress events.
        enable_web: Whether web-search tools are wired for agents that declare them.
        web_backends: The ordered web-search backends to try when web is enabled
            (``tavily`` / ``google`` / ``duckduckgo`` / ``noop``); the resolver
            builds a fallback chain in this order. Defaults to Tavily, then
            Google, then DuckDuckGo.
        tavily_api_key: The Tavily API key, or ``None`` when unset; the fallback
            builder skips the Tavily backend and warns when it is absent.
        tavily_search_depth: The Tavily depth (``basic`` | ``advanced``) driving
            both ``search_depth`` and ``extract_depth``. Defaults to ``basic``.
        log_level: The console logging level (``DEBUG`` | ``INFO`` | ``WARNING`` | …).
        run_logs: Whether to write a per-run JSONL trace under ``logs/``.
        reviewer_thinking: Whether the QA reviewer runs in thinking mode. Off by
            default because DeepSeek V4 thinking mode rejects the forced
            ``tool_choice`` that structured output uses.
        auth_issuer: The OIDC issuer whose tokens the API accepts, or ``None``
            when unset. The API refuses every request while it is unset rather
            than falling open, so a missing configuration cannot silently
            disable tenancy.
        auth_audience: The expected ``aud`` claim, or ``None`` to skip the
            audience check when the IdP does not set one.
        tenant_id: The tenant the **CLI** operates as. The CLI is a local
            operator tool with no request to carry a token, so its tenant comes
            from configuration — never from a command-line argument, which would
            be a caller-supplied business identity (ADR-0013).
        postgres_dsn: The Postgres connection string, or ``None`` to keep
            documents on the filesystem and run state in memory. Setting it
            makes Postgres the system of record (ADR-0014): documents, the
            tenant directory, the run registry and the LangGraph checkpointer
            all move there together, because they are one durability decision.
    """

    provider: str = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_PROVIDER", "deepseek")
    )
    root: Path = field(default_factory=_discover_root)
    max_steps: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_STEPS", "20"))
    )
    max_qa_iterations: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_QA", "3"))
    )
    human_gate_stages: list[str] | None = field(
        default_factory=lambda: _parse_human_gate_stages(os.environ.get("MARKETING_OS_HUMAN_GATES"))
    )
    max_revisions: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_REVISIONS", "5"))
    )
    max_runs_per_campaign: int = field(
        default_factory=lambda: int(os.environ.get("MARKETING_OS_MAX_RUNS", "20"))
    )
    usage_allowance: float = field(
        default_factory=lambda: float(os.environ.get("MARKETING_OS_ALLOWANCE", "25"))
    )
    token_rates: dict[str, float] = field(
        default_factory=lambda: _parse_token_rates(os.environ.get("MARKETING_OS_TOKEN_RATES", ""))
    )
    stream: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_STREAM", "1") != "0")
    enable_web: bool = field(default_factory=lambda: os.environ.get("MARKETING_OS_WEB", "0") == "1")
    web_backends: list[WebBackend] = field(
        default_factory=lambda: _parse_web_backends(os.environ.get("MARKETING_OS_WEB_BACKENDS", ""))
    )
    tavily_api_key: str | None = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_TAVILY_API_KEY") or None
    )
    tavily_search_depth: str = field(
        default_factory=lambda: _parse_search_depth(
            os.environ.get("MARKETING_OS_TAVILY_SEARCH_DEPTH", "")
        )
    )
    log_level: str = field(default_factory=lambda: os.environ.get("MARKETING_OS_LOG_LEVEL", "INFO"))
    run_logs: bool = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_RUN_LOGS", "1") != "0"
    )
    reviewer_thinking: bool = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_REVIEWER_THINKING", "0") != "0"
    )
    auth_issuer: str | None = field(
        default_factory=lambda: (
            os.environ.get("MARKETING_OS_AUTH_ISSUER") or os.environ.get("CLERK_ISSUER_URL") or None
        )
    )
    auth_audience: str | None = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_AUTH_AUDIENCE") or None
    )
    tenant_id: str | None = field(
        default_factory=lambda: os.environ.get("MARKETING_OS_TENANT_ID") or None
    )
    postgres_dsn: str | None = field(
        default_factory=lambda: (
            os.environ.get("MARKETING_OS_POSTGRES_DSN") or os.environ.get("DATABASE_URL") or None
        )
    )

    @property
    def claude_dir(self) -> Path:
        """Return the ``.claude/`` governance directory under the repo root."""
        return self.root / _CLAUDE_DIR_NAME

    @property
    def agents_dir(self) -> Path:
        """Return the directory holding the specialist agent specs."""
        return self.claude_dir / "agents"

    @property
    def rules_dir(self) -> Path:
        """Return the directory holding the canonical governance rules."""
        return self.claude_dir / "rules"

    @property
    def templates_dir(self) -> Path:
        """Return the directory holding the DNA and goal templates."""
        return self.root / "templates"

    @property
    def tenants_dir(self) -> Path:
        """Return the directory the filesystem store keeps tenant-owned documents under.

        Every document a tenant owns — its Brand DNA and all campaign
        deliverables — lives beneath ``tenants/<tenant_id>/``. Nothing else in
        the repository is tenant data, which is what lets the read sandbox deny
        this prefix wholesale (ADR-0013).
        """
        return self.root / "tenants"

    def tenant_dir(self, tenant: str) -> Path:
        """Return one tenant's document directory.

        Args:
            tenant: The tenant whose directory to locate.

        Returns:
            The ``tenants/<tenant>/`` directory path.
        """
        return self.tenants_dir / tenant

    @property
    def knowledge_dir(self) -> Path:
        """Return the central domain-knowledge library directory."""
        return self.root / "knowledge"

    @property
    def guardrails_dir(self) -> Path:
        """Return the directory holding the per-stage review rubrics."""
        return self.root / "guardrails"

    @property
    def logs_dir(self) -> Path:
        """Return the root directory where per-run JSONL traces are written."""
        return self.root / "logs"

    def tenant_logs_dir(self, tenant: str) -> Path:
        """Return the directory holding one tenant's run traces.

        Traces are partitioned by tenant for the same reason documents are: a
        run id belonging to another business must be unfindable, not merely
        unauthorised, so cross-tenant lookups answer 404 (ADR-0013).

        Args:
            tenant: The tenant whose traces to locate.

        Returns:
            The ``logs/<tenant>/`` directory path.
        """
        return self.logs_dir / tenant

    def provider_config(
        self, name: str | None = None, *, role: str | None = None
    ) -> ProviderConfig:
        """Resolve connection details for a provider, optionally for a named role.

        A role (for example ``"reviewer"``) may override the model via a
        ``MARKETING_OS_<ROLE>_MODEL`` environment variable so a cheaper judge model
        can be used without changing the active provider.

        Args:
            name: The provider name to resolve; defaults to the active provider.
            role: An optional role whose per-role model override takes precedence.

        Returns:
            The resolved :class:`ProviderConfig`.

        Raises:
            ConfigError: If the provider is unknown or no model is configured.
        """
        name = name or self.provider
        spec = _PROVIDER_DEFAULTS.get(name)
        if spec is None:
            raise ConfigError(f"Unknown provider '{name}'. Known: {', '.join(_PROVIDER_DEFAULTS)}.")

        if role == Role.REVIEWER:
            role_model = os.environ.get(f"MARKETING_OS_{role.upper()}_MODEL") if role else None
            model = role_model or os.environ.get(spec["model_env"], spec["reviewer_model_default"])
        else:
            model = os.environ.get(spec["model_env"], spec["model_default"])

        if not model:
            raise ConfigError(
                f"No model configured for provider '{name}'. Set {spec['model_env']}."
            )
        base_url = os.environ.get(spec["base_url_env"], spec["base_url_default"]) or None
        return ProviderConfig(
            model=model,
            api_key=os.environ.get(spec["key_env"]),
            base_url=base_url,
        )

    def token_rate(self, model: str) -> float:
        """Return the price per token to cost a model's call at.

        Args:
            model: The model identifier the provider billed for.

        Returns:
            That model's configured rate, or the default rate when it has none —
            an unpriced model is costed rather than treated as free, so a
            forgotten rate under-reports spend instead of hiding it entirely.
        """
        return self.token_rates.get(model, _DEFAULT_TOKEN_RATE)

    def validate_root(self) -> None:
        """Ensure the resolved repository root contains a ``.claude/`` directory.

        Raises:
            ConfigError: If the root is missing its ``.claude/`` directory.
        """
        if not self.claude_dir.is_dir():
            raise ConfigError(
                f"Marketing OS root not found at {self.root} (no .claude/ directory). "
                "Set MARKETING_OS_ROOT."
            )


def load_settings() -> Settings:
    """Build :class:`Settings` from the environment and validate the repo root.

    Returns:
        A validated :class:`Settings` instance.
    """
    settings = Settings()
    settings.validate_root()
    return settings
