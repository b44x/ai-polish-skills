#!/usr/bin/env python3
"""Shared test contract harness for ai-polish-skills.

Verifies:
1. Standard CLI contract (--help returns 0, outputs help text to stdout).
2. Error handling contract (invalid args return non-zero exit code, error on stderr, clean stdout).
3. Deterministic / offline output contract (outputs valid JSON on stdout).
4. No debug/garbage logs mixed into stdout.

Zero external dependencies (Python 3.8+ standard library only).
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT_DIR / "skills"


class TestFailure(Exception):
    pass


def run_cmd(args: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run command and return CompletedProcess."""
    return subprocess.run(
        args,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_help_contract(script_path: Path) -> None:
    """Every skill script must support --help and exit with 0."""
    res = run_cmd([sys.executable, str(script_path), "--help"])
    if res.returncode != 0:
        raise TestFailure(f"--help failed with code {res.returncode}: {res.stderr.strip()}")
    if not res.stdout.strip():
        raise TestFailure("--help produced empty stdout")


def test_invalid_args_contract(script_path: Path) -> None:
    """Invalid arguments must return non-zero exit code and not pollute stdout."""
    res = run_cmd([sys.executable, str(script_path), "__invalid_command_probe__"])
    if res.returncode == 0:
        raise TestFailure("Expected non-zero exit code on invalid arguments, but got 0")
    if res.stdout.strip():
        # Stdout must not contain regular execution output if error occurred
        # (unless it is a formatted error JSON, but stderr is preferred)
        try:
            val = json.loads(res.stdout)
            if "error" not in val:
                raise TestFailure(f"Stdout polluted on error: {res.stdout[:100]}")
        except Exception:
            raise TestFailure(f"Stray output on stdout during error: {res.stdout[:100]}")


def test_error_contract(
    script_path: Path,
    args: List[str],
    expected_exit: int = 64,
) -> None:
    """Verify command exits with expected error code, clean stdout, and JSON error on stderr."""
    cmd = [sys.executable, str(script_path)] + args
    res = run_cmd(cmd)
    if res.returncode != expected_exit:
        raise TestFailure(f"Command {' '.join(cmd)} exited with {res.returncode}, expected {expected_exit}")
    if res.stdout.strip():
        raise TestFailure(f"Stdout should be empty on error, got: {res.stdout[:100]}")
    stderr_raw = res.stderr.strip()
    if not stderr_raw:
        raise TestFailure("Stderr is empty, expected error JSON")
    try:
        err = json.loads(stderr_raw)
        if "error" not in err:
            raise TestFailure(f"Stderr JSON missing 'error' key: {err}")
    except json.JSONDecodeError:
        raise TestFailure(f"Stderr is not valid JSON: {stderr_raw}")


def test_json_stdout_contract(
    script_path: Path,
    args: List[str],
    validator_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
    expected_exit: int = 0,
) -> None:
    """Command must return expected exit code and emit valid JSON on stdout."""
    cmd = [sys.executable, str(script_path)] + args
    res = run_cmd(cmd)
    if res.returncode != expected_exit:
        raise TestFailure(
            f"Command {' '.join(cmd)} failed with exit {res.returncode} (expected {expected_exit}): {res.stderr.strip()}"
        )

    stdout_raw = res.stdout.strip()
    if not stdout_raw:
        raise TestFailure(f"Command {' '.join(cmd)} emitted empty stdout")

    try:
        data = json.loads(stdout_raw)
    except json.JSONDecodeError as e:
        raise TestFailure(f"Stdout is not valid JSON: {e}\nOutput was: {stdout_raw[:200]}")

    if validator_fn:
        validator_fn(data)


def get_skill_script(skill_dir: Path) -> Optional[Path]:
    """Find primary Python script for a skill."""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return None
    expected_name = skill_dir.name.replace("-", "_") + ".py"
    direct = scripts_dir / expected_name
    if direct.is_file():
        return direct
    alt = scripts_dir / f"{skill_dir.name}.py"
    if alt.is_file():
        return alt
    py_files = sorted(scripts_dir.glob("*.py"))
    return py_files[0] if py_files else None


def main() -> int:
    print("═══════════════════════════════════════════════════════════════")
    print(" ai-polish-skills Test Contract Harness")
    print("═══════════════════════════════════════════════════════════════")

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )

    total_tests = 0
    failed_tests = 0
    start_time = time.time()

    for sdir in skill_dirs:
        skill_name = sdir.name
        script = get_skill_script(sdir)
        if not script:
            print(f"✗ [{skill_name}] No Python script found in scripts/")
            failed_tests += 1
            continue

        print(f"\n▶ Testing skill: {skill_name} ({script.name})")

        # 1. Help contract test
        total_tests += 1
        try:
            test_help_contract(script)
            print("  ✓ --help contract passed (exit 0, stdout non-empty)")
        except TestFailure as e:
            print(f"  ✗ --help contract failed: {e}")
            failed_tests += 1

        # 2. Invalid args contract test
        total_tests += 1
        try:
            test_invalid_args_contract(script)
            print("  ✓ Invalid args contract passed (exit != 0, clean stdout)")
        except TestFailure as e:
            print(f"  ✗ Invalid args contract failed: {e}")
            failed_tests += 1

        # 3. Specific deterministic / offline contract tests
        if skill_name == "biala-lista":
            # Test valid NIP offline validation
            total_tests += 1
            try:
                def check_valid_nip(data):
                    if data.get("valid") is not True or data.get("type") != "nip":
                        raise TestFailure(f"Unexpected NIP validate payload: {data}")

                test_json_stdout_contract(script, ["validate", "5260250274"], check_valid_nip)
                print("  ✓ Offline NIP checksum validation passed (valid=True, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline NIP checksum failed: {e}")
                failed_tests += 1

            # Test invalid NIP offline validation
            total_tests += 1
            try:
                def check_invalid_nip(data):
                    if data.get("valid") is not False:
                        raise TestFailure(f"Expected valid=False for bad NIP, got {data}")

                test_json_stdout_contract(
                    script, ["validate", "1234567890"], check_invalid_nip, expected_exit=64
                )
                print("  ✓ Offline invalid NIP validation passed (valid=False, exit=64, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline invalid NIP checksum failed: {e}")
                failed_tests += 1

        elif skill_name == "filmweb":
            # Test URL ID extraction offline
            total_tests += 1
            try:
                def check_id(data):
                    if data.get("id") != 628:
                        raise TestFailure(f"Expected id 628, got {data.get('id')}")

                test_json_stdout_contract(
                    script,
                    ["id", "https://www.filmweb.pl/film/Matrix-1999-628"],
                    check_id,
                )
                print("  ✓ Offline Filmweb URL ID parser passed (id=628, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline Filmweb URL ID parser failed: {e}")
                failed_tests += 1

        elif skill_name == "imgw":
            # Test offline station search
            total_tests += 1
            try:
                def check_station(data):
                    stations = data.get("stations", [])
                    if not stations or stations[0].get("stationId") != "12375":
                        raise TestFailure(f"Expected station 12375 (Warszawa), got {stations}")
                    if "lat" not in stations[0].get("coordinates", {}):
                        raise TestFailure("Missing coordinates in station info")

                test_json_stdout_contract(
                    script,
                    ["stations", "--search", "Warszawa"],
                    check_station,
                )
                print("  ✓ Offline IMGW station search passed (id=12375, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline IMGW station search failed: {e}")
                failed_tests += 1

            # Test offline nearest station calculation via GPS
            total_tests += 1
            try:
                def check_near(data):
                    closest = data.get("closestStation", {})
                    if closest.get("stationId") != "12375":
                        raise TestFailure(f"Expected closest station 12375 for (52.23, 21.01), got {closest}")
                    if closest.get("distanceKm", 999) > 15.0:
                        raise TestFailure(f"Distance too high: {closest.get('distanceKm')} km")

                test_json_stdout_contract(
                    script,
                    ["near", "52.23", "21.01", "--no-weather"],
                    check_near,
                )
                print("  ✓ Offline IMGW GPS distance calculation passed (Warszawa <15km, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline IMGW GPS distance calculation failed: {e}")
                failed_tests += 1

            # Test invalid GPS coordinates contract
            total_tests += 1
            try:
                test_error_contract(
                    script,
                    ["near", "999.0", "999.0"],
                    expected_exit=64,
                )
                print("  ✓ Offline IMGW invalid GPS validation passed (exit=64, error JSON on stderr)")
            except TestFailure as e:
                print(f"  ✗ Offline IMGW invalid GPS validation failed: {e}")
                failed_tests += 1

        elif skill_name == "sejm":
            # 1. Test offline terms catalogue
            total_tests += 1
            try:
                def check_terms(data):
                    if data.get("currentTerm") != 10 or data.get("count", 0) < 10:
                        raise TestFailure(f"Unexpected terms payload: {data}")

                test_json_stdout_contract(
                    script,
                    ["terms", "--offline"],
                    check_terms,
                )
                print("  ✓ Offline Sejm terms catalogue passed (10 terms, current=10, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline Sejm terms catalogue failed: {e}")
                failed_tests += 1

            # 2. Test offline MP fixture
            total_tests += 1
            try:
                def check_mp(data):
                    mps = data.get("mps", [])
                    if not mps or mps[0].get("firstLastName") != "Szymon Hołownia":
                        raise TestFailure(f"Unexpected MP payload: {mps}")

                test_json_stdout_contract(
                    script,
                    ["mps", "--offline"],
                    check_mp,
                )
                print("  ✓ Offline Sejm MP fixture passed (Szymon Hołownia, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline Sejm MP fixture failed: {e}")
                failed_tests += 1

            # 3. Test offline voting fixture
            total_tests += 1
            try:
                def check_voting(data):
                    if data.get("totalVoted") != 458 or data.get("yes") != 458:
                        raise TestFailure(f"Unexpected voting payload: {data}")
                    if "PiS" not in data.get("clubSummary", {}):
                        raise TestFailure(f"Missing clubSummary in voting: {data}")

                test_json_stdout_contract(
                    script,
                    ["voting", "1", "2", "--offline"],
                    check_voting,
                )
                print("  ✓ Offline Sejm voting fixture passed (total=458, yes=458, clubSummary, valid JSON)")
            except TestFailure as e:
                print(f"  ✗ Offline Sejm voting fixture failed: {e}")
                failed_tests += 1

            # 4. Test invalid arguments contract
            total_tests += 1
            try:
                test_error_contract(
                    script,
                    ["voting", "-1", "-1"],
                    expected_exit=64,
                )
                print("  ✓ Offline Sejm invalid args validation passed (exit=64, error JSON on stderr)")
            except TestFailure as e:
                print(f"  ✗ Offline Sejm invalid args validation failed: {e}")
                failed_tests += 1

    elapsed = time.time() - start_time
    print("\n───────────────────────────────────────────────────────────────")
    print(f"Ran {total_tests} contract tests across {len(skill_dirs)} skills in {elapsed:.2f}s.")

    if failed_tests > 0:
        print(f"Result: {failed_tests} TEST(S) FAILED", file=sys.stderr)
        return 1

    print("Result: ALL TESTS PASSED ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
