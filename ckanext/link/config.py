from __future__ import annotations

import ckan.plugins.toolkit as tk

PREFIX = "ckanext.link."


def timeout() -> int:
    return tk.config.get(PREFIX + "timeout", 30)


def connect_timeout() -> int:
    return tk.config.get(PREFIX + "connect_timeout", 10)


def max_redirects() -> int:
    return tk.config.get(PREFIX + "max_redirects", 5)


def user_agent() -> str:
    return tk.config.get(PREFIX + "user_agent", "CKAN Link Checker/1.0")


def blocked_domains() -> list[str]:
    raw = tk.config.get(PREFIX + "blocked_domains", "")
    if not raw:
        return []
    return raw.split()


def check_head_first() -> bool:
    return tk.config.get(PREFIX + "check_head_first", True)


def batch_delay() -> float:
    return float(tk.config.get(PREFIX + "batch_delay", 0.5))


def verify_ssl() -> bool:
    return tk.config.get(PREFIX + "verify_ssl", False)
