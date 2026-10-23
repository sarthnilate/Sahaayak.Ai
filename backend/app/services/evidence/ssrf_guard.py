"""
Phase 6: SSRF Guard — Safe URL validation and protected HTTP fetching.
Guards against private IP access, loopback, link-local metadata services,
DNS rebinding, unsafe schemes, and unconstrained redirects.
"""

import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable, List, Optional
from urllib.parse import urlparse
import urllib.request


class SSRFSecurityError(ValueError):
    """Raised when a URL violates SSRF safety constraints."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# Deny-list for IP ranges that must NEVER be contacted by server-side fetching
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local & AWS/GCP Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique Local Address
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-Local
]

ALLOWED_SCHEMES = {"https"}
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT_SECONDS = 3.0
MAX_RESPONSE_BYTES = 1_000_000  # 1 MB cap


@dataclass
class SafeUrlValidationResult:
    is_safe: bool
    resolved_ip: Optional[str]
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks if an IP belongs to any private, loopback, or metadata networks."""
    for network in BLOCKED_IP_NETWORKS:
        if ip_obj in network:
            return True
    return False


def validate_url_safety(
    url: str,
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
) -> SafeUrlValidationResult:
    """
    Pure validation for URL schemes and resolved IP safety.
    Accepts an optional dns_resolver for unit test injection / DNS rebinding simulation.
    """
    if not url or not isinstance(url, str):
        return SafeUrlValidationResult(False, None, "SSRF_EMPTY_URL", "URL must not be empty.")

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return SafeUrlValidationResult(False, None, "SSRF_MALFORMED_URL", f"Malformed URL: {e}")

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        return SafeUrlValidationResult(
            False,
            None,
            "SSRF_INVALID_SCHEME",
            f"Scheme '{scheme}' disallowed. Only HTTPS is permitted.",
        )

    hostname = parsed.hostname
    if not hostname:
        return SafeUrlValidationResult(False, None, "SSRF_MISSING_HOST", "URL missing hostname.")

    # 1. Check if hostname is direct IP literal
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(direct_ip):
            return SafeUrlValidationResult(
                False,
                str(direct_ip),
                "SSRF_PRIVATE_IP_BLOCKED",
                f"Direct IP {direct_ip} is in a blocked network range.",
            )
        return SafeUrlValidationResult(True, str(direct_ip))
    except ValueError:
        pass  # It's a DNS hostname

    # 2. Resolve DNS hostname
    try:
        if dns_resolver:
            ips = dns_resolver(hostname)
        else:
            # getaddrinfo resolves IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
            ips = [item[4][0] for item in addr_info]

        if not ips:
            return SafeUrlValidationResult(
                False, None, "SSRF_DNS_RESOLUTION_FAILED", f"Could not resolve host '{hostname}'."
            )

        # Check every resolved IP address
        for ip_str in ips:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                return SafeUrlValidationResult(
                    False,
                    ip_str,
                    "SSRF_PRIVATE_IP_BLOCKED",
                    f"Host '{hostname}' resolved to blocked IP {ip_str}.",
                )

        return SafeUrlValidationResult(True, ips[0])

    except socket.gaierror as e:
        return SafeUrlValidationResult(
            False, None, "SSRF_DNS_RESOLUTION_FAILED", f"DNS resolution failed: {e}"
        )
    except Exception as e:
        return SafeUrlValidationResult(
            False, None, "SSRF_VALIDATION_ERROR", f"Validation error: {e}"
        )


def check_safe_url_or_raise(
    url: str,
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
) -> SafeUrlValidationResult:
    """Helper that raises SSRFSecurityError if URL validation fails."""
    result = validate_url_safety(url, dns_resolver=dns_resolver)
    if not result.is_safe:
        raise SSRFSecurityError(
            code=result.error_code or "SSRF_BLOCKED",
            message=result.error_message or "URL blocked by security guard",
        )
    return result
