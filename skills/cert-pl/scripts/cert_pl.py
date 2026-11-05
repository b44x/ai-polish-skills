#!/usr/bin/env python3
"""Check a domain against the active CERT Polska warning list (stdlib only)."""

import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE = "https://hole.cert.pl/domains/v2/domains.txt"
MAX_BYTES = 32 * 1024 * 1024
TTL = 300


class SkillError(Exception):
    def __init__(self, message, kind="validation_error", code=64):
        super().__init__(message)
        self.kind, self.code = kind, code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SkillError(message)


def domain_name(value):
    """Parse locally: never resolve DNS or visit the submitted URL."""
    value = value.strip()
    if not value or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise SkillError("Podaj domenę lub poprawny URL HTTP(S).")
    try:
        parsed = urllib.parse.urlsplit(value if "://" in value else "//" + value)
        if parsed.scheme and parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("scheme")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("userinfo")
        _ = parsed.port
        host = parsed.hostname
        if not host:
            raise ValueError("hostname")
        host = host.encode("idna").decode("ascii").lower().rstrip(".")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP address")
        labels = host.split(".")
        if len(host) > 253 or len(labels) < 2 or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("domain")
        return host
    except (ValueError, UnicodeError):
        raise SkillError("Nieprawidłowa domena; obsługiwane są domeny i URL HTTP(S), bez danych logowania i adresów IP.")


def parse_list(body):
    try:
        lines = body.decode("utf-8").splitlines()
        domains = {domain_name(line) for line in lines if line.strip()}
        if not domains:
            raise ValueError("empty list")
        # A source line must be a domain, not HTML, a URL or a path.
        if any("/" in line or ":" in line for line in lines):
            raise ValueError("invalid list")
        return domains
    except (UnicodeError, ValueError, SkillError):
        raise SkillError("Nieprawidłowy format listy CERT Polska.", "upstream_format", 69)


def cache_path():
    root = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return root / "ai-polish-skills" / "cert-pl" / "active-domains.json"


def load_domains(path=None, now=None):
    path = cache_path() if path is None else Path(path)
    now = time.time() if now is None else now
    try:
        if path.stat().st_size <= MAX_BYTES:
            cached = json.loads(path.read_text(encoding="utf-8"))
            fetched = float(cached["fetched_at"])
            if cached["source"] == SOURCE and 0 <= now - fetched < TTL:
                domains = parse_list(cached["text"].encode("utf-8"))
                return domains, fetched, True
    except (OSError, ValueError, KeyError, TypeError, SkillError):
        pass

    req = urllib.request.Request(SOURCE, headers={"User-Agent": "ai-polish-skills-cert-pl/1.0.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SkillError("Lista CERT przekracza limit rozmiaru.", "upstream_format", 69)
        domains = parse_list(body)
    except (urllib.error.URLError, OSError) as exc:
        raise SkillError("Nie udało się pobrać aktualnej listy CERT: " + str(exc), "network_error", 69)

    # Cache failure must not discard a successfully fetched, current list.
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent), delete=False) as out:
            temporary = out.name
            json.dump({"source": SOURCE, "fetched_at": now, "text": body.decode("utf-8")}, out)
        os.replace(temporary, str(path))
    except OSError:
        pass
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return domains, now, False


def check(value):
    domain = domain_name(value)
    domains, fetched, cached = load_domains()
    labels = domain.split(".")
    match = next((".".join(labels[i:]) for i in range(len(labels) - 1)
                  if ".".join(labels[i:]) in domains), None)
    return {
        "domain": domain,
        "listed": match is not None,
        "matched_domain": match,
        "status": "listed" if match else "not_listed",
        "message": "Domena figuruje na liście ostrzeżeń CERT Polska." if match else
                   "Nie znaleziono na liście CERT Polska. Nie jest to potwierdzenie bezpieczeństwa.",
        "source": SOURCE,
        "list_fetched_at": dt.datetime.fromtimestamp(fetched, dt.timezone.utc).isoformat(),
        "cached": cached,
    }


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        command = commands.add_parser("check", help="Sprawdź domenę lub URL w CERT Polska")
        command.add_argument("address")
        args = parser.parse_args(argv)
        print(json.dumps(check(args.address), ensure_ascii=False, allow_nan=False))
        return 0
    except SkillError as exc:
        print(json.dumps({"error": str(exc), "type": exc.kind}, ensure_ascii=False), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
