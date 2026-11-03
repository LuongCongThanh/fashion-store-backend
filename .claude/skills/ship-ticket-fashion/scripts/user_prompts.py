"""In các prompt người dùng đã gõ trong phiên Claude Code của repo này, làm bằng chứng cho retro.

Bỏ qua kết quả tool, thân skill và thông báo hệ thống; lệnh skill in thành "[/tên] tham số".
python3 .claude/skills/ship-ticket-fashion/scripts/user_prompts.py [--last N]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from gitcmd import repo_root

SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+\-/]+=*"),
    re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b"
    ),
    re.compile(r"(?i)\b(password|passwd|token|api[_-]?key|secret)\b(\s*[:=]\s*)([^\s,;]+)"),
)


def redact(text: str) -> str:
    """Che credential phổ biến trước khi prompt rời transcript cục bộ."""
    text = SECRET_PATTERNS[0].sub(r"\1 [REDACTED]", text)
    text = SECRET_PATTERNS[1].sub("[REDACTED]", text)
    return SECRET_PATTERNS[2].sub(r"\1\2[REDACTED]", text)


def sessions_dir() -> Path:
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo_root()))


def prompts(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "user" or entry.get("isMeta"):
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        if not content or content.startswith(
            ("<local-command", "<task-notification", "<bash-stdout")
        ):
            continue
        command = re.search(
            r"<command-name>(.*?)</command-name>.*?<command-args>(.*?)</command-args>",
            content,
            re.S,
        )
        if command:
            if command.group(1) == "/clear":
                continue
            content = f"[{command.group(1)}] {command.group(2)}"
        elif len(content) > 1500:
            continue  # thân skill được nạp vào phiên
        out.append(redact(" ".join(content.split())))
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--last", type=int, default=1, help="số phiên gần nhất (mặc định 1: phiên hiện tại)"
    )
    args = parser.parse_args()
    if args.last < 1:
        parser.error("--last phải lớn hơn hoặc bằng 1")

    directory = sessions_dir()
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)[-args.last :]
    if not files:
        print(f"Không thấy phiên nào trong {directory}")
        return 1
    for path in files:
        print(f"===== {path.stem}")
        for prompt in prompts(path):
            print(f"- {prompt[:600]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
