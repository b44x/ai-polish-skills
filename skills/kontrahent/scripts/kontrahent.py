#!/usr/bin/env python3
"""Compare a contractor's VAT registration with an official current KRS extract."""

import argparse
import datetime as dt
import http.client
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


MF = "https://wykazpodatnikowvat.mf.gov.pl/api"
KRS = "https://api-krs.ms.gov.pl/api/krs/OdpisAktualny"
MAX_BODY = 2 * 1024 * 1024


class SourceError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def fetch(url):
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "PolskieSkille-kontrahent/1.0"
    })
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
            body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise SourceError("response_too_large")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise SourceError("invalid_response")
        return value
    except urllib.error.HTTPError as exc:
        with exc:
            if exc.code == 404:
                return None
            raise SourceError("http_" + str(exc.code)) from None
    except (OSError, http.client.HTTPException):
        raise SourceError("network_error") from None
    except (ValueError, RecursionError):
        raise SourceError("invalid_response") from None


def nip_number(value):
    number = re.sub(r"[ -]", "", value.strip().upper())
    if number.startswith("PL"):
        number = number[2:]
    if (not re.fullmatch(r"[0-9]{10}", number) or len(set(number)) == 1
            or sum(int(n) * w for n, w in zip(number, (6, 5, 7, 2, 3, 4, 5, 6, 7))) % 11 != int(number[-1])):
        raise ValueError("Invalid NIP checksum")
    return number


def krs_number(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value) or not int(value):
        raise ValueError("Invalid KRS number")
    return value.zfill(10)


def bank_number(value):
    number = value.strip().upper().replace(" ", "")
    if number.startswith("PL"):
        number = number[2:]
    if not re.fullmatch(r"[0-9]{26}", number) or int(number[2:] + "2521" + number[:2]) % 97 != 1:
        raise ValueError("Invalid Polish bank account checksum")
    return number


def text_or_none(value):
    return value if isinstance(value, str) and value else None


def mf_result(url):
    payload = fetch(url)
    result = payload.get("result") if payload is not None else None
    if not isinstance(result, dict) or not all(text_or_none(result.get(k)) for k in ("requestId", "requestDateTime")):
        raise SourceError("invalid_response")
    return result


def vat_lookup(nip, day):
    result = mf_result(MF + "/search/nip/" + nip + "?date=" + day)
    subject = result.get("subject")
    receipt = {k: result[k] for k in ("requestId", "requestDateTime")}
    if subject is None and "subject" in result:
        return dict(receipt, status="not_found", as_of=day)
    if (not isinstance(subject, dict) or subject.get("nip") != nip
            or subject.get("statusVat") not in ("Czynny", "Zwolniony", "Niezarejestrowany")):
        raise SourceError("invalid_response")
    raw_krs = subject.get("krs")
    try:
        identifier = krs_number(raw_krs) if raw_krs not in (None, "") else None
    except ValueError:
        raise SourceError("invalid_response") from None
    return dict(receipt, status="ok", as_of=day, name=text_or_none(subject.get("name")),
                statusVat=subject["statusVat"], krs=identifier)


def current_extract(identifier, registry):
    for register in (registry,) if registry else ("P", "S"):
        payload = fetch(KRS + "/" + identifier + "?" + urllib.parse.urlencode(
            {"rejestr": register, "format": "json"}))
        if payload is None:
            continue
        try:
            extract = payload["odpis"]
            header = extract["naglowekA"]
            entity = extract["dane"]["dzial1"]["danePodmiotu"]
            if header["numerKRS"] != identifier or header.get("rejestr") not in (None, register, "Rej" + register):
                raise ValueError("Mismatched extract")
            if not text_or_none(header.get("dataCzasOdpisu") or header.get("dataOdpisu")):
                raise ValueError("Missing extract date")
            representation = extract["dane"].get("dzial2", {}).get("reprezentacja", {})
            return dict(status="ok", number=identifier, registry=register,
                        nip=text_or_none(entity.get("identyfikatory", {}).get("nip")),
                        name=text_or_none(entity.get("nazwa")),
                        extracted_at=header.get("dataCzasOdpisu") or header.get("dataOdpisu"),
                        as_of=text_or_none(header.get("stanZDnia")),
                        last_entry_date=text_or_none(header.get("dataOstatniegoWpisu")),
                        representation=text_or_none(representation.get("sposobReprezentacji")))
        except (KeyError, TypeError, ValueError, AttributeError):
            raise SourceError("invalid_response") from None
    return dict(status="not_found", number=identifier)


def account_check(nip, account, day):
    result = mf_result(MF + "/check/nip/" + nip + "/bank-account/" + account + "?date=" + day)
    if result.get("accountAssigned") not in ("TAK", "NIE"):
        raise SourceError("invalid_response")
    return dict(status="ok", account_last4=account[-4:], as_of=day,
                accountAssigned=result["accountAssigned"], requestId=result["requestId"],
                requestDateTime=result["requestDateTime"])


def optional_check(operation, *args):
    try:
        return operation(*args)
    except SourceError as exc:
        return dict(status="unavailable", error=str(exc))


def report(nip, day, identifier, register, account):
    vat = vat_lookup(nip, day)
    vat_identifier = vat.get("krs")
    selected = identifier or vat_identifier
    extract = optional_check(current_extract, selected, register) if selected else dict(status="no_krs_number")
    bank = optional_check(account_check, nip, account, day) if account else dict(status="not_requested")
    krs_nip = extract.get("nip")
    return {
        "nip": nip, "vat": vat, "krs": extract, "bank": bank,
        "comparison": {
            "vat_krs_number_matches_input": vat_identifier == identifier if identifier and vat_identifier else None,
            "current_krs_nip_matches_input": krs_nip == nip if krs_nip else None,
        },
        "sources": {
            "vat": "https://www.gov.pl/web/kas/api-wykazu-podatnikow-vat",
            "krs": "https://prs.ms.gov.pl/krs/openApi",
        },
    }


def main(argv=None):
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check one contractor by NIP")
    check.add_argument("nip")
    check.add_argument("--date", required=True, help="VAT reference date in YYYY-MM-DD")
    check.add_argument("--krs", help="Optional explicit KRS number")
    check.add_argument("--registry", choices=("P", "S"))
    check.add_argument("--account", help="Optional Polish NRB or PL IBAN")
    try:
        args = parser.parse_args(argv)
        nip = nip_number(args.nip)
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", args.date):
            raise ValueError("Use YYYY-MM-DD for --date")
        day = dt.date.fromisoformat(args.date).isoformat()
        identifier = krs_number(args.krs) if args.krs is not None else None
        account = bank_number(args.account) if args.account is not None else None
        result = report(nip, day, identifier, args.registry, account)
    except ValueError as exc:
        print(json.dumps({"error": str(exc), "type": "validation_error"}), file=sys.stderr)
        return 64
    except SourceError as exc:
        print(json.dumps({"error": str(exc), "type": "vat_source_unavailable"}), file=sys.stderr)
        return 69
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
