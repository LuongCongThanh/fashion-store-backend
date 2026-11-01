"""Đếm ticket đã merge cho retro theo đợt; checkpoint được commit cùng PR retro.

python S/scripts/retro_batch.py status
python S/scripts/retro_batch.py complete --through <sha> --batch <id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from gitcmd import repo_root

BATCH_SIZE = 10
CHECKPOINT = Path(__file__).resolve().parent.parent / "reference/retro-batch.json"


def git_at(root: Path, *args: str, empty_ok: bool = False) -> str:
    """Đọc Git tại repo chỉ định; lỗi Git không được coi như danh sách rỗng."""
    executable = shutil.which("git")
    if executable is None:
        raise ValueError("Không tìm thấy Git trên PATH")
    result = subprocess.run(  # noqa: S603 -- Git cố định, truyền argv trực tiếp, không qua shell.
        [executable, "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode and not (empty_ok and result.returncode == 1):
        raise ValueError(result.stderr.strip() or "Git không đọc được lịch sử retro")
    return result.stdout


def resolved(root: Path, ref: str) -> set[str]:
    """Chỉ lấy spec resolved trong commit, không đọc thay đổi chưa merge ở worktree."""
    output = git_at(
        root,
        "grep",
        "-l",
        "-z",
        "-E",
        "^Status: resolved[[:space:]]*$",
        ref,
        "--",
        ".scratch/*/issues/*/spec.md",
        empty_ok=True,
    )
    return {item.partition(":")[2] for item in output.split("\0") if item}


def status(root: Path, checkpoint: dict, ref: str = "origin/dev") -> dict:
    """Tính đợt kế tiếp từ ticket mới resolved kể từ baseline, trừ các đợt đã xử lý."""
    through = git_at(root, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    baseline = checkpoint["baseline"]
    git_at(root, "merge-base", "--is-ancestor", baseline, through)
    reviewed = {ticket for batch in checkpoint["batches"] for ticket in batch["tickets"]}
    pending = sorted(resolved(root, through) - resolved(root, baseline) - reviewed)
    tickets = pending[:BATCH_SIZE]
    batch_id = hashlib.sha256("\n".join(tickets).encode()).hexdigest()[:12]
    return {
        "through": through,
        "pending": len(pending),
        "due": len(pending) >= BATCH_SIZE,
        "batch": batch_id,
        "tickets": tickets,
    }


def complete(root: Path, checkpoint: dict, through: str, batch_id: str) -> dict:
    """Ghi nhận đúng đợt đã review; chạy lại cùng id không tiêu thụ thêm ticket."""
    if any(batch["id"] == batch_id for batch in checkpoint["batches"]):
        return checkpoint
    current = status(root, checkpoint, through)
    if not current["due"] or current["batch"] != batch_id:
        raise ValueError("Đợt chưa đủ 10 ticket hoặc id không khớp snapshot đã review")
    batch = {"id": batch_id, "through": current["through"], "tickets": current["tickets"]}
    return {**checkpoint, "batches": [*checkpoint["batches"], batch]}


def main() -> int:
    """In đợt pending hoặc cập nhật checkpoint sau khi review đã có kết luận."""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("status")
    read.add_argument("--ref", default="origin/dev")
    write = commands.add_parser("complete")
    write.add_argument("--through", required=True)
    write.add_argument("--batch", required=True)
    args = parser.parse_args()
    root = repo_root()
    try:
        checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        if args.command == "status":
            output = status(root, checkpoint, args.ref)
        else:
            output = complete(root, checkpoint, args.through, args.batch)
            CHECKPOINT.write_text(
                json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Retro checkpoint: {exc}\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
