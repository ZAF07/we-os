"""Mailer adapters — how the reminder email leaves the engine (ADR-0028).

Implements the :class:`~marketing_os.ports.Mailer` port. Two adapters, and the
choice between them is a setting:

* :class:`NoopMailer` logs what it would have sent and sends nothing. It is the
  default, so a fresh checkout, the test suite and the e2e stack can never email
  a real address by accident.
* :class:`ResendMailer` posts to Resend's HTTP API over an injected
  :class:`httpx.Client`, so the whole adapter is exercised offline against a
  faked transport, as the Tavily backend is.

:func:`build_mailer` follows the web-search pattern: the real adapter is
constructed only when it is selected, and selecting it without what it needs is
refused with the name of the setting to fix, so a misconfigured deployment
fails at startup rather than at the first reminder a week later.
"""

from __future__ import annotations

import httpx

from marketing_os.adapters.observability import get_logger
from marketing_os.config import MailerName, Settings
from marketing_os.errors import ConfigError, ToolError
from marketing_os.ports import Mailer
from marketing_os.schemas import EmailMessage

_LOGGER = get_logger("marketing_os.mail")

_RESEND_BASE_URL = "https://api.resend.com"
_SEND_ENDPOINT = "/emails"
_DEFAULT_TIMEOUT = 30.0

_INVALID_KEY_STATUS = frozenset({401, 403})


class NoopMailer:
    """Sends nothing, and logs what it would have sent.

    The log line is the whole point: a dev run with the one-minute review
    interval shows a reminder going out for a due business without an inbox
    anywhere in the loop.
    """

    def send(self, message: EmailMessage) -> None:
        """Log the message instead of sending it.

        Args:
            message: The message that would have been sent.
        """
        _LOGGER.info("mail.noop to=%s subject=%r", message.to, message.subject)


class ResendMailer:
    """Sends through Resend's ``POST /emails`` over an injected HTTP client."""

    def __init__(
        self,
        api_key: str,
        *,
        sender: str,
        client: httpx.Client | None = None,
        base_url: str = _RESEND_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """Store the Resend configuration and HTTP client.

        Args:
            api_key: The Resend API key, sent as a bearer token.
            sender: The address the mail goes out as, in the form Resend accepts
                (``Name <address>``), on a domain verified with Resend.
            client: An injected :class:`httpx.Client`; when ``None`` a client
                owned by this mailer is created.
            base_url: The Resend API base URL.
            timeout: The per-request timeout in seconds for an owned client.
        """
        self._api_key = api_key
        self._sender = sender
        self._client = client or httpx.Client(timeout=timeout)
        self._base_url = base_url.rstrip("/")

    def send(self, message: EmailMessage) -> None:
        """Ask Resend to send one message.

        Args:
            message: The message to send.

        Raises:
            ConfigError: If Resend rejected the API key.
            ToolError: If Resend refused the message or could not be reached.
        """
        body = {
            "from": self._sender,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
        }
        try:
            response = self._client.post(
                f"{self._base_url}{_SEND_ENDPOINT}",
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except httpx.HTTPError as exc:
            raise ToolError(f"Resend could not be reached: {exc}") from exc
        if response.status_code in _INVALID_KEY_STATUS:
            raise ConfigError("Resend rejected the API key. Check MARKETING_OS_RESEND_API_KEY.")
        if response.is_error:
            raise ToolError(
                f"Resend refused the message ({response.status_code}): {_reason(response)}"
            )


def _reason(response: httpx.Response) -> str:
    """Return what Resend said about a refused message.

    Args:
        response: The error response.

    Returns:
        Resend's ``message`` field when the body carries one, otherwise the
        raw body text.
    """
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if isinstance(payload, dict) and isinstance(payload.get("message"), str):
        return payload["message"]
    return response.text


def build_mailer(settings: Settings) -> Mailer:
    """Build the mailer the settings select.

    Args:
        settings: The harness settings.

    Returns:
        The no-op mailer unless Resend is selected; the Resend mailer when it
        is, and has what it needs.

    Raises:
        ConfigError: If Resend is selected without an API key or a sender,
            naming the setting to fix.
    """
    if settings.mailer is MailerName.NOOP:
        return NoopMailer()
    if not settings.resend_api_key:
        raise ConfigError(
            "MARKETING_OS_MAILER=resend needs an API key. Set MARKETING_OS_RESEND_API_KEY, "
            "or select the noop mailer."
        )
    if not settings.mail_from:
        raise ConfigError(
            "MARKETING_OS_MAILER=resend needs a sender. Set MARKETING_OS_MAIL_FROM to an "
            "address on a domain verified with Resend, such as 'We-OS <hello@example.com>'."
        )
    return ResendMailer(settings.resend_api_key, sender=settings.mail_from)
