"""Token đã dùng cho một ticket, tính từ transcript Claude Code, chia theo phase và agent.

python3 .claude/skills/ship-ticket-fashion/scripts/metrics.py <T> [--write]
`--write` ghi `metrics.md` vào thư mục ticket (commit cùng ticket). Chỉ đếm lượt trả lời
trên nhánh của ticket (`gitBranch` = `branch` của state), gồm cả sub-agent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from common import load_state, repo_root, resolve
from state import PHASES

MAIN = "phiên chính"
FIELDS = (
    ("input", "input_tokens"),
    ("cache_write", "cache_creation_input_tokens"),
    ("cache_read", "cache_read_input_tokens"),
    ("output", "output_tokens"),
)


@dataclass
class Usage:
    turns: int = 0
    input: int = 0
    cache_write: int = 0
    cache_read: int = 0
    output: int = 0

    @property
    def total(self) -> int:
        return self.input + self.cache_write + self.cache_read + self.output

    def add(self, usage: dict[str, Any]) -> None:
        self.turns += 1
        for attr, key in FIELDS:
            setattr(self, attr, getattr(self, attr) + int(usage.get(key) or 0))


@dataclass
class Report:
    by_phase: dict[str, Usage] = field(default_factory=dict)
    by_agent: dict[str, Usage] = field(default_factory=dict)
    total: Usage = field(default_factory=Usage)
    first: datetime | None = None
    last: datetime | None = None


def transcript_dirs(repo: Path) -> list[Path]:
    """Thư mục transcript của repo và thư mục con của nó (phiên mở trong thư mục con…)."""
    config = os.environ.get("CLAUDE_CONFIG_DIR")
    projects = (Path(config) if config else Path.home() / ".claude") / "projects"
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo))
    if not projects.is_dir():
        return []
    return sorted(p for p in projects.iterdir() if p.name == slug or p.name.startswith(slug + "-"))


def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone()


def phase_at(moment: datetime, transitions: list[dict[str, Any]]) -> str:
    phase = transitions[0]["from"] if transitions else "grill"
    for t in transitions:
        if parse_time(t["at"]) <= moment:
            phase = t["to"]
    return phase


def agent_label(path: Path) -> str:
    if path.parent.name != "subagents":
        return MAIN
    meta = path.with_suffix(".meta.json")
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return path.stem
    return data.get("description") or data.get("agentType") or path.stem


def turns(path: Path, branch: str) -> dict[str, dict[str, Any]]:
    """Lượt trả lời trên `branch`, khoá theo message id; dòng sau của cùng message ghi đè."""
    found: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        if entry.get("type") != "assistant" or entry.get("gitBranch") != branch:
            continue
        if not message.get("usage") or not entry.get("timestamp"):
            continue
        found[message.get("id") or entry.get("uuid", line)] = entry
    return found


def collect(state: dict[str, Any], dirs: list[Path]) -> Report:
    report = Report()
    transitions = state.get("transitions") or []
    for directory in dirs:
        files = [*directory.glob("*.jsonl"), *directory.glob("*/subagents/*.jsonl")]
        for path in sorted(files):
            label = agent_label(path)
            for entry in turns(path, state["branch"]).values():
                moment = parse_time(entry["timestamp"])
                usage = entry["message"]["usage"]
                report.by_phase.setdefault(phase_at(moment, transitions), Usage()).add(usage)
                report.by_agent.setdefault(label, Usage()).add(usage)
                report.total.add(usage)
                report.first = min(filter(None, (report.first, moment)))
                report.last = max(filter(None, (report.last, moment)))
    return report


def table(
    title: str, rows: dict[str, Usage], total: Usage, order: list[str] | None = None
) -> list[str]:
    head = f"| {title} | Lượt | Input | Cache ghi | Cache đọc | Output | Tổng |"
    lines = [head, "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]

    def row(name: str, u: Usage) -> str:
        cells = (u.turns, u.input, u.cache_write, u.cache_read, u.output, u.total)
        return f"| {name} | " + " | ".join(f"{c:,}" for c in cells) + " |"

    if order:
        ordered = sorted(rows.items(), key=lambda item: [*order, item[0]].index(item[0]))
    else:
        ordered = sorted(rows.items(), key=lambda item: -item[1].total)
    lines += [row(name, usage) for name, usage in ordered]
    lines.append(row("**Tổng**", total))
    return lines


def render(report: Report, ticket: str) -> str:
    span = (
        f"{report.first:%d/%m/%Y %H:%M} → {report.last:%d/%m/%Y %H:%M}"
        if report.first and report.last
        else "không có lượt nào"
    )
    lines = [
        f"# Token: {ticket}",
        "",
        f"{span} · {report.total.turns} lượt · {report.total.total:,} token "
        f"(output {report.total.output:,})",
        "",
        *table("Phase", report.by_phase, report.total, PHASES),
        "",
        *table("Agent", report.by_agent, report.total),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--write", action="store_true", help="ghi metrics.md vào thư mục ticket")
    args = parser.parse_args()
    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    if not state:
        parser.error(f"chưa có state cho {args.ticket}")
    report = collect(state, transcript_dirs(repo_root()))
    text = render(report, f"{feature.slug}/{ticket.num:02d}")
    if args.write:
        out = Path(state["ticket"]) / "metrics.md"
        (repo_root() / out).write_text(text, encoding="utf-8", newline="\n")
        print(f"WROTE {out}")
    print(text.split("\n")[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
