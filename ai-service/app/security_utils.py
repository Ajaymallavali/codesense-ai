import ipaddress
import re
from pathlib import Path
from urllib.parse import urlparse
import zipfile

# Secret pattern definitions
SECRET_REGEXES = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[AWS_ACCESS_KEY_REDACTED]"),
    (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "[GITHUB_PAT_REDACTED]"),
    (re.compile(r"github_pat_[0-9a-zA-Z_]{82}"), "[GITHUB_FINE_GRAINED_PAT_REDACTED]"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "[SLACK_TOKEN_REDACTED]"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "[PRIVATE_KEY_REDACTED]"),
    (re.compile(r"(?i)(?:password|secret|passwd|api_key|apikey|access_token|auth_token)\s*[:=]\s*['\"][^\s'\"]{6,}['\"]"), "[SECRET_CREDENTIAL_REDACTED]"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "0:0:0:0:0:0:0:1",
    "metadata.google.internal",
    "169.254.169.254",
}

ALLOWED_GIT_HOSTS = {
    "github.com",
    "api.github.com",
    "codeload.github.com",
    "gitlab.com",
    "bitbucket.org",
}


def validate_repository_url(url: str) -> str:
    """
    Validates repository URL to prevent SSRF and unsafe protocols.
    Supports 'owner/repo' or 'https://github.com/owner/repo[.git]'.
    """
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("Repository URL cannot be empty")

    # If format is owner/repo
    if re.match(r"^[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+$", cleaned):
        return f"https://github.com/{cleaned}"

    parsed = urlparse(cleaned)
    if parsed.scheme != "https":
        raise ValueError("Only secure HTTPS repository URLs are permitted")

    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname in BLOCKED_HOSTNAMES:
        raise ValueError(f"Access to hostname '{hostname}' is not permitted")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Access to private/loopback/internal IP addresses is prohibited")
    except ValueError:
        pass  # Hostname is a domain name, not a raw IP

    if hostname not in ALLOWED_GIT_HOSTS:
        raise ValueError("Only verified Git hosting providers (GitHub, GitLab, Bitbucket) are supported")

    return cleaned


def validate_redirect_url(url: str) -> str:
    """
    Validates redirect targets to block redirect-based SSRF into private networks or metadata endpoints.
    """
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("Redirect URL cannot be empty")

    parsed = urlparse(cleaned)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"Prohibited redirect protocol: '{parsed.scheme}'")

    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname in BLOCKED_HOSTNAMES:
        raise ValueError(f"Prohibited redirect hostname: '{hostname}'")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"Redirect to private or internal IP '{ip}' is blocked")
    except ValueError:
        pass

    return cleaned


def safe_extract_zip(zip_path: str | Path, target_dir: str | Path) -> None:
    """
    Safely extracts zip archive contents, verifying all destination paths reside
    strictly within target_dir to prevent Zip-slip / directory traversal attacks.
    """
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_dest = (target_path / member.filename).resolve()
            if not is_safe_path(target_path, member_dest):
                raise ValueError(f"Archive entry '{member.filename}' violates extraction boundary (Zip-slip attempt)")
        zip_ref.extractall(target_path)


def redact_secrets(content: str) -> str:
    """
    Scans content and redacts detected secrets and credentials.
    """
    if not content:
        return ""
    result = content
    for pattern, replacement in SECRET_REGEXES:
        result = pattern.sub(replacement, result)
    return result


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """
    Verifies target_path resides safely within base_dir (prevents directory traversal).
    """
    try:
        base_resolved = base_dir.resolve()
        target_resolved = target_path.resolve()
        return target_resolved.is_relative_to(base_resolved)
    except Exception:
        return False
