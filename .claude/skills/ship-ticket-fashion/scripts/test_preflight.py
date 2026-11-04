import json
import unittest

from preflight import compose_states, evaluate, next_fix

RUNNING = ("worker", "beat", "relay", "redis", "mailpit")
HEALTHY_DJANGO = {"db": "ok", "pending_migrations": 0, "provinces": 34, "admins": 1, "redis": "ok"}


def ps(**states: str) -> str:
    rows = [{"Service": s, "State": st, "ExitCode": 0} for s, st in states.items()]
    return "\n".join(json.dumps(r) for r in rows)


def failed(checks):
    return {c.name: c for c in checks if not c.ok}


class Preflight(unittest.TestCase):
    def test_compose_states_reads_json_lines_and_arrays(self):
        lines = ps(worker="running", migrate="exited")
        self.assertEqual(
            compose_states(lines), {"worker": ("running", 0), "migrate": ("exited", 0)}
        )
        array = json.dumps([{"Service": "redis", "State": "running", "ExitCode": 0}])
        self.assertEqual(compose_states(array), {"redis": ("running", 0)})

    def test_all_green_when_everything_is_up(self):
        compose = compose_states(ps(migrate="exited", **dict.fromkeys(RUNNING, "running")))
        checks = evaluate(compose, HEALTHY_DJANGO, {"healthz": 200, "readyz": 200, "mailpit": 200})
        self.assertEqual(failed(checks), {})

    def test_each_gap_maps_to_its_fix(self):
        compose = compose_states(ps(worker="exited", redis="running"))
        django = {**HEALTHY_DJANGO, "pending_migrations": 2}
        checks = failed(
            evaluate(compose, django, {"healthz": None, "readyz": None, "mailpit": None})
        )
        self.assertEqual(checks["docker"].fix, "make up")
        self.assertIn("worker", checks["docker"].detail)
        self.assertEqual(checks["migrations"].fix, "make migrate")
        self.assertNotIn("seed geo", checks)  # seed chỉ kiểm sau khi migrate xong
        self.assertEqual(checks["api"].fix, "make run")
        self.assertFalse(checks["api"].auto)  # server chạy nền do agent bật

    def test_seed_gaps_after_migrations(self):
        django = {**HEALTHY_DJANGO, "provinces": 0, "admins": 0}
        checks = failed(evaluate({}, django, {}))
        self.assertEqual(checks["seed geo"].fix, "make load-geo")
        self.assertTrue(checks["seed geo"].auto)
        self.assertFalse(checks["seed admin"].auto)  # create-admin hỏi mật khẩu: người dùng chạy

    def test_next_fix_follows_dependency_order(self):
        compose = compose_states(ps(worker="exited"))
        django = {**HEALTHY_DJANGO, "pending_migrations": 1}
        self.assertEqual(next_fix(evaluate(compose, django, {}), set()), "make up")
        self.assertEqual(next_fix(evaluate(compose, django, {}), {"make up"}), "make migrate")

    def test_database_down_skips_dependent_checks(self):
        django = {"db": "OperationalError: connection refused"}
        checks = failed(evaluate({}, django, {}))
        self.assertIn("database", checks)
        self.assertNotIn("migrations", checks)
        self.assertFalse(checks["database"].auto)


if __name__ == "__main__":
    unittest.main()
