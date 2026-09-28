#!/usr/bin/env python3
"""CLI for Narodowy Bank Polski (NBP) official exchange rates and gold prices.

Official API docs: http://api.nbp.pl/
Zero external dependencies (Python 3.8+ stdlib only).

Copyright (c) 2026 Michell Hoduń <mhodun@gmail.com> (https://github.com/b44x)
Licensed under the MIT License.
"""

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_BASE_URL = "https://api.nbp.pl/api"
TROY_OUNCE_GRAMS = 31.1034768


def error_exit(message: str, error_type: str = "error", code: int = 64) -> None:
    """Print error JSON to stderr and exit."""
    json.dump({"error": message, "type": error_type}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    sys.exit(code)


def fetch_api(endpoint: str) -> Any:
    """Execute GET request against NBP API."""
    url = f"{API_BASE_URL}/{endpoint}?format=json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Antigravity-AI-Skills/1.0 (NBP)",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if e.code == 404:
            error_exit(
                f"Brak danych w NBP dla podanych parametrów (błędna waluta, data lub dzień wolny): {body}",
                "not_found",
                2,
            )
        elif e.code == 400:
            error_exit(f"Nieprawidłowe zapytanie do API NBP: {body}", "bad_request", 64)
        else:
            error_exit(f"Błąd serwera NBP (HTTP {e.code}): {body}", "server_error", 69)
    except urllib.error.URLError as e:
        error_exit(f"Błąd połączenia z serwerem NBP: {e.reason}", "network_error", 69)
    except Exception as e:
        error_exit(f"Nieoczekiwany błąd: {str(e)}", "unknown_error", 69)
    return None


def get_single_rate(currency: str, date_str: Optional[str] = None) -> Dict[str, Any]:
    """Fetch rate for currency from Table A, fallback to Table B."""
    curr = currency.upper().strip()
    path = f"exchangerates/rates/A/{curr}/"
    if date_str:
        path += f"{date_str}/"

    try:
        data = fetch_api(path)
        table_letter = "A"
    except SystemExit:
        # Try table B for less common currencies
        path_b = f"exchangerates/rates/B/{curr}/"
        if date_str:
            path_b += f"{date_str}/"
        try:
            data = fetch_api(path_b)
            table_letter = "B"
        except SystemExit:
            error_exit(f"Waluta '{curr}' nie została znaleziona w tabelach A ani B NBP.", "not_found", 2)

    rate_info = data["rates"][0]
    return {
        "currency": curr,
        "currencyName": data.get("currency"),
        "table": table_letter,
        "tableNumber": rate_info.get("no"),
        "effectiveDate": rate_info.get("effectiveDate"),
        "mid": rate_info.get("mid"),
    }


def find_preceding_working_day_rate(currency: str, invoice_date: datetime.date) -> Dict[str, Any]:
    """Find the NBP exchange rate published on the last business day preceding the invoice date (Art. 31a VAT)."""
    curr = currency.upper().strip()
    current = invoice_date - datetime.timedelta(days=1)

    # Search backwards up to 14 days to skip long weekends / holidays
    for _ in range(14):
        d_str = current.isoformat()
        for table in ["A", "B"]:
            url = f"{API_BASE_URL}/exchangerates/rates/{table}/{curr}/{d_str}/?format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Antigravity-AI-Skills/1.0 (NBP)"})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    rate_info = data["rates"][0]
                    return {
                        "currency": curr,
                        "currencyName": data.get("currency"),
                        "table": table,
                        "tableNumber": rate_info.get("no"),
                        "taxEffectiveDate": rate_info.get("effectiveDate"),
                        "rate": rate_info.get("mid"),
                    }
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                else:
                    raise
        current -= datetime.timedelta(days=1)

    error_exit(
        f"Nie znaleziono kursu NBP dla {curr} w okresie 14 dni przed {invoice_date.isoformat()}.",
        "not_found",
        2,
    )
    return {}


def cmd_rate(args: argparse.Namespace) -> None:
    res = get_single_rate(args.currency, args.date)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_invoice(args: argparse.Namespace) -> None:
    try:
        inv_date = datetime.date.fromisoformat(args.date)
    except ValueError:
        error_exit(f"Nieprawidłowy format daty '{args.date}'. Oczekiwano RRRR-MM-DD.", "validation_error", 64)

    amount = float(args.amount)
    curr = args.currency.upper().strip()

    if curr == "PLN":
        output = {
            "amount": amount,
            "currency": "PLN",
            "invoiceDate": args.date,
            "taxEffectiveDate": args.date,
            "tableNumber": "BRAK (waluta krajowa)",
            "exchangeRate": 1.0,
            "amountPln": amount,
            "legalBasis": "Brak konieczności przeliczenia (waluta krajowa PLN)",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    rate_data = find_preceding_working_day_rate(curr, inv_date)
    rate = rate_data["rate"]
    amount_pln = round(amount * rate, 2)
    amount_pln_exact = amount * rate

    output = {
        "amount": amount,
        "currency": curr,
        "currencyName": rate_data.get("currencyName"),
        "invoiceDate": args.date,
        "taxEffectiveDate": rate_data["taxEffectiveDate"],
        "tableNumber": rate_data["tableNumber"],
        "exchangeRate": rate,
        "amountPln": amount_pln,
        "amountPlnExact": round(amount_pln_exact, 4),
        "legalBasis": "Art. 31a ust. 1 ustawy o VAT / Art. 11a ust. 1 ustawy o PIT (ostatni dzień roboczy poprzedzający dzień powstania obowiązku podatkowego lub wystawienia faktury)",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_convert(args: argparse.Namespace) -> None:
    amount = float(args.amount)
    from_curr = args.from_currency.upper().strip()
    to_curr = args.to_currency.upper().strip()
    date_str = args.date

    # Get rate in PLN
    from_rate = 1.0 if from_curr == "PLN" else get_single_rate(from_curr, date_str)["mid"]
    to_rate = 1.0 if to_curr == "PLN" else get_single_rate(to_curr, date_str)["mid"]

    # Convert: from_curr -> PLN -> to_curr
    in_pln = amount * from_rate
    converted = in_pln / to_rate

    output = {
        "amount": amount,
        "fromCurrency": from_curr,
        "toCurrency": to_curr,
        "convertedAmount": round(converted, 2),
        "convertedAmountExact": round(converted, 4),
        "rateFromPln": from_rate,
        "rateToPln": to_rate,
        "effectiveRate": round(from_rate / to_rate, 4),
        "date": date_str or datetime.date.today().isoformat(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_table(args: argparse.Namespace) -> None:
    table_type = args.table.upper().strip()
    path = f"exchangerates/tables/{table_type}/"
    if args.date:
        path += f"{args.date}/"

    data = fetch_api(path)
    if isinstance(data, list) and data:
        table_obj = data[0]
        rates = table_obj.get("rates", [])
        output = {
            "table": table_obj.get("table"),
            "tableNumber": table_obj.get("no"),
            "effectiveDate": table_obj.get("effectiveDate"),
            "ratesCount": len(rates),
            "rates": rates,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        error_exit("Nieoczekiwana odpowiedź API NBP.", "server_error", 69)


def cmd_gold(args: argparse.Namespace) -> None:
    path = "cenyzlota"
    if args.date:
        path += f"/{args.date}"

    data = fetch_api(path)
    if isinstance(data, list) and data:
        item = data[0]
        price_per_gram = float(item.get("cena", 0))
        price_per_ounce = round(price_per_gram * TROY_OUNCE_GRAMS, 2)
        output = {
            "date": item.get("data"),
            "pricePerGramPln": price_per_gram,
            "pricePerTroyOuncePln": price_per_ounce,
            "priceFormatted": f"{price_per_gram:.2f} zł / g",
            "priceOunceFormatted": f"{price_per_ounce:.2f} zł / oz",
            "purity": "1000 (czyste złoto)",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        error_exit("Brak danych o cenie złota.", "not_found", 2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pobieraj oficjalne kursy walut i ceny złota z Narodowego Banku Polskiego (NBP)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # rate
    p_rate = subparsers.add_parser("rate", help="Pobierz aktualny lub historyczny kurs średni waluty")
    p_rate.add_argument("currency", help="Kod waluty (np. EUR, USD, GBP, CHF)")
    p_rate.add_argument("--date", help="Data w formacie RRRR-MM-DD (domyślnie ostatnio opublikowany)")
    p_rate.set_defaults(func=cmd_rate)

    # invoice
    p_inv = subparsers.add_parser(
        "invoice",
        help="Przelicz kwotę faktury walutowej na PLN wg zasad podatkowych (kurs NBP z dnia poprzedzającego)",
    )
    p_inv.add_argument("amount", type=float, help="Kwota w walucie obcej")
    p_inv.add_argument("currency", help="Kod waluty (np. EUR, USD)")
    p_inv.add_argument("date", help="Data wystawienia faktury lub powstania obowiązku podatkowego (RRRR-MM-DD)")
    p_inv.set_defaults(func=cmd_invoice)

    # convert
    p_conv = subparsers.add_parser("convert", help="Przelicz kwotę między dowolnymi walutami wg kursów NBP")
    p_conv.add_argument("amount", type=float, help="Kwota źródłowa")
    p_conv.add_argument("from_currency", help="Waluta źródłowa (np. EUR, USD, PLN)")
    p_conv.add_argument("to_currency", help="Waluta docelowa (np. PLN, EUR, USD)")
    p_conv.add_argument("--date", help="Data kursu w formacie RRRR-MM-DD (domyślnie ostatni kurs)")
    p_conv.set_defaults(func=cmd_convert)

    # table
    p_table = subparsers.add_parser("table", help="Pobierz pełną tabelę kursów NBP (A, B lub C)")
    p_table.add_argument("table", choices=["A", "B", "C"], default="A", nargs="?", help="Typ tabeli (A, B lub C)")
    p_table.add_argument("--date", help="Data w formacie RRRR-MM-DD")
    p_table.set_defaults(func=cmd_table)

    # gold
    p_gold = subparsers.add_parser("gold", help="Pobierz oficjalną cenę złota NBP w PLN za 1g i 1oz")
    p_gold.add_argument("--date", help="Data w formacie RRRR-MM-DD")
    p_gold.set_defaults(func=cmd_gold)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
