#!/usr/bin/env python3
"""Offline contract test for the local MCP server (mcp/server.py).

Checks the MCP handshake, that every tool points at an existing skill script and has a
valid input schema, an offline tool call (terminy), and JSON-RPC error handling.

Zero external dependencies (Python 3.8+ standard library only).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SERVER = ROOT_DIR / "mcp" / "server.py"


class Client:
    def __init__(self) -> None:
        self.proc = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True, cwd=ROOT_DIR)
        self.next_id = 0

    def send(self, method: str, params=None, notify: bool = False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self.next_id += 1
            msg["id"] = self.next_id
        return self.raw(json.dumps(msg), expect_reply=not notify)

    def raw(self, line: str, expect_reply: bool = True):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline()) if expect_reply else None

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


def main() -> int:
    failures = []

    def check(cond: bool, label: str) -> None:
        print(f"  {'✓' if cond else '✗'} {label}")
        if not cond:
            failures.append(label)

    sys.path.insert(0, str(SERVER.parent))
    import server  # noqa: E402

    c = Client()
    try:
        init = c.send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "test", "version": "1"}})["result"]
        check(init["protocolVersion"] == "2025-06-18", "initialize echoes a supported protocol version")
        check("tools" in init["capabilities"], "server declares the tools capability")
        c.send("notifications/initialized", notify=True)

        tools = c.send("tools/list")["result"]["tools"]
        check(len(tools) == len(server.TOOLS) and len(tools) >= 20, f"tools/list returns all {len(server.TOOLS)} tools")
        names = [t["name"] for t in tools]
        check(len(names) == len(set(names)), "tool names are unique")
        for spec in server.TOOLS:
            ok = server.script_path(spec["skill"]).is_file()
            schema = spec["inputSchema"]
            ok = ok and set(schema["required"]) <= set(schema["properties"])
            if not ok:
                check(False, f"tool {spec['name']}: script exists and required ⊆ properties")
        check(True, "every tool points at an existing skill script with a consistent schema")

        res = c.send("tools/call", {"name": "terminy_deadlines", "arguments": {"month": "2026-09"}})["result"]
        data = json.loads(res["content"][0]["text"]) if not res["isError"] else {}
        vat = next((d for d in data.get("deadlines", []) if d["id"] == "vat"), {})
        check(vat.get("deadline") == "2026-10-26", "offline tool call works (VAT for 2026-09 moved to 2026-10-26)")

        res = c.send("tools/call", {"name": "terminy_month", "arguments": {}})["result"]
        check(res["isError"], "missing required argument returns isError")
        res = c.send("tools/call", {"name": "terminy_month", "arguments": {"month": "2026-13"}})["result"]
        check(res["isError"] and "exit 64" in res["content"][0]["text"], "skill validation error is reported (exit 64)")
        check("error" in c.send("tools/call", {"name": "no_such_tool", "arguments": {}}), "unknown tool returns a JSON-RPC error")
        check(c.send("no/such/method")["error"]["code"] == -32601, "unknown method returns -32601")
        check(c.raw("not json")["error"]["code"] == -32700, "invalid JSON returns -32700")
        check(c.send("ping")["result"] == {}, "ping returns an empty result")
    finally:
        c.close()

    print(f"\nMCP server: {'ALL CHECKS PASSED ✔' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
