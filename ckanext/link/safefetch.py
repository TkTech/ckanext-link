import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests

from ckanext.link import config

log = logging.getLogger(__name__)


class SSRFError(Exception):
    pass


class PrivateIPError(SSRFError):
    pass


class BlockedDomainError(SSRFError):
    pass


class InvalidURLError(SSRFError):
    pass


class TooManyRedirectsError(SSRFError):
    pass


def _validate_url(url: str) -> str:
    """Validate URL scheme and return the hostname."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(f"Invalid URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise InvalidURLError(f"No hostname in URL: {url!r}")
    return parsed.hostname


def _check_hostname(hostname: str):
    """Resolve hostname and reject private/internal IPs."""
    blocked = config.blocked_domains()
    if hostname.lower() in blocked:
        raise BlockedDomainError(f"Blocked domain: {hostname}")

    try:
        addrinfos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise InvalidURLError(
            f"DNS resolution failed for {hostname}: {exc}"
        ) from exc

    for family, _, _, _, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise PrivateIPError(
                f"Hostname {hostname} resolves to private/reserved IP: {ip}"
            )


def safe_check_url(url: str) -> dict:
    """
    Check a URL for availability with SSRF protection.

    Returns dict with keys: status_code, error, is_broken.
    """
    try:
        return _do_check(url)
    except SSRFError as exc:
        return {"status_code": None, "error": str(exc), "is_broken": True}
    except requests.RequestException as exc:
        return {"status_code": None, "error": str(exc), "is_broken": True}
    except Exception as exc:
        log.exception("Unexpected error checking URL %s", url)
        return {"status_code": None, "error": str(exc), "is_broken": True}


def _do_check(url: str) -> dict:
    hostname = _validate_url(url)
    _check_hostname(hostname)

    timeout = (config.connect_timeout(), config.timeout())
    headers = {"User-Agent": config.user_agent()}
    max_redirects = config.max_redirects()

    current_url = url
    for _ in range(max_redirects + 1):
        method = "HEAD" if config.check_head_first() else "GET"
        resp = _make_request(method, current_url, headers, timeout)

        # Fall back to GET on 405 Method Not Allowed
        if resp.status_code == 405 and method == "HEAD":
            resp.close()
            resp = _make_request("GET", current_url, headers, timeout)

        status_code = resp.status_code

        if resp.is_redirect or status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                return {
                    "status_code": status_code,
                    "error": "Redirect with no Location header",
                    "is_broken": True,
                }
            # Validate redirect target
            redirect_host = _validate_url(location)
            _check_hostname(redirect_host)
            current_url = location
            continue

        resp.close()
        is_broken = status_code >= 400
        return {
            "status_code": status_code,
            "error": None if not is_broken else f"HTTP {status_code}",
            "is_broken": is_broken,
        }

    raise TooManyRedirectsError(
        f"Too many redirects (>{max_redirects}) for {url}"
    )


def _make_request(
    method: str, url: str, headers: dict, timeout: tuple
) -> requests.Response:
    return requests.request(
        method,
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=False,
        stream=True,
        verify=config.verify_ssl(),
    )
