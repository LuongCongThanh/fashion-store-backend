# State

`.git/ship-ticket-fashion/<K>.json`, created in phase 1 by `state.py init`. Read this file in phase 1 and before writing a field for the first time.

```json
{
  "ticket": ".scratch/backend-bootstrap/issues/16-shared-api-layer",
  "feature": "backend-bootstrap", "num": 16,
  "branch": "feat/shared-api-layer", "mode": "full",
  "phase": "code", "next": "S2: viết test 404 trả ErrorDTO rồi exception_handler",
  "gates": { "g1": "2026-10-29", "g2": null },
  "slices": [
    { "id": "S1", "acs": [4], "dependsOn": [], "status": "done",
      "seam": "GET list endpoint qua APIClient",
      "tests": ["common/tests/api/test_pagination.py::test_page_size_capped_at_100"],
      "tddTests": ["common/tests/api/test_pagination.py::test_page_size_capped_at_100"],
      "verificationTests": [],
      "expectedRed": {"common/tests/api/test_pagination.py::test_page_size_capped_at_100": "AssertionError"},
      "files": ["common/api/pagination.py"],
      "governingDocs": {"common/api/pagination.py": ["docs/architecture/13-python-django-coding-style.md::3.1"]},
      "tdd": {"common/tests/api/test_pagination.py::test_page_size_capped_at_100":
        {"redAt": "2026-10-29T10:10:00+07:00", "redReason": "FAILED …", "greenAt": "2026-10-29T10:20:00+07:00"}},
      "handoff": ["StandardPagination trong common/api/pagination.py"] },
    { "id": "S2", "acs": [1], "dependsOn": ["S1"], "status": "code", "seam": "service result",
      "tests": ["apps/x/tests/services/test_x.py::test_x"], "tddTests": [],
      "verificationTests": ["apps/x/tests/services/test_x.py::test_x"], "expectedRed": {},
      "files": ["apps/x/services/x.py"],
      "governingDocs": {"apps/x/services/x.py": ["docs/architecture/13-python-django-coding-style.md::4"]},
      "tdd": {} }
  ],
  "currentSlice": "S2",
  "untestable": { "3": "cần Redis thật; kiểm tay bằng make up rồi tắt redis" },
  "userRequested": [{ "date": "2026-10-29", "request": "…" }],
  "notes": {},
  "pr": null,
  "transitions": [{ "from": "grill", "to": "code", "at": "2026-10-29T10:00:00", "reason": "G1 approved" }]
}
```

- `acs`: 1-based index of the AC in the `## Acceptance criteria` section of `spec.md`.
- `tests`: deduplicated union of `tddTests` and `verificationTests`; function-level pytest ids (`file.py::test_x`), relative to the repo root.
- `tddTests`: new behaviour tests; need `expectedRed`, go red then green. `verificationTests`: existing tests that only need a verified green.
- `files`: files the slice will change, recorded in phase 1 for `plan.md`; one slice is one commit containing exactly these files.
- `governingDocs`: each key is a file in `files`, each value a `path.md::section` reference; the script checks file and heading exist, and that the reference appears in `## Quyết định`.
- `tdd`: written only by `tdd.py`. `tddTests` need `redAt` + `greenAt`; `verificationTests` need `verifiedAt` before the slice is `done`.
- `notes`: free-form notes by key. `notes.baselineRed`: ids of tests already red on `origin/dev`, recorded in phase 1 from the baseline log.
- `untestable`: ACs not testable automatically here, with reason and manual check; the report lists them under *Chưa làm*.
- Slice `status`: `todo` → `code` → `done`. Slice dependencies form a DAG; `state.py check` rejects duplicate ids, unknown `dependsOn` and cycles.
- `handoff`: at most 5 lines per slice, only what later slices reuse (exported names, decisions). No work log.
- `next`: exactly one concrete next task, rewritten after every step.
- `phase`: `grill | code | report | review | sync | ship | done | closed`.
- `pr`: PR number, recorded in phase 6.
- `phase`, `transitions`, `gates`: written only by `state.py transition`; `set` / `push` reject them. `--gate g1` only on `grill → code`, `--gate g2` only on `sync → ship`.
- After merge `done → closed`; waiting for merge stays `done`.

Commands:

```bash
python3 S/scripts/state.py init <T> --branch <branch> --mode lite|full
python3 S/scripts/state.py set <T> mode=lite slices.S1.status=code 'next=S1: chạy test red' currentSlice=S1
# Push one complete object following the S1/S2 schema above; state.py rejects missing fields.
python3 S/scripts/state.py check <T>
```

Values that parse as JSON are stored as JSON (`[4]`, `null`, `true`), anything else as a string. The path `slices.S1.x` selects the slice by `id`. `push` appends each element of a list to the end of a list field.
