import threading
import unittest

from tiny_thread_local_context import Context


class TestCore(unittest.TestCase):

    def test_get_missing_returns_default(self):
        ctx = Context()
        self.assertIsNone(ctx.get("nope"))
        self.assertEqual(ctx.get("nope", "fallback"), "fallback")

    def test_set_then_get_same_thread(self):
        ctx = Context()
        ctx.set("request_id", "abc")
        self.assertEqual(ctx.get("request_id"), "abc")

    def test_isolation_between_threads(self):
        ctx = Context()
        ctx.set("k", "parent")
        seen = {}

        def worker():
            seen["value"] = ctx.get("k", "absent")

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        self.assertEqual(seen["value"], "absent")
        self.assertEqual(ctx.get("k"), "parent")

    def test_snapshot_is_independent_of_subsequent_sets(self):
        ctx = Context()
        ctx.set("a", 1)
        snap = ctx.snapshot()
        ctx.set("a", 2)
        self.assertEqual(snap["a"], 1)
        self.assertEqual(ctx.get("a"), 2)

    def test_snapshot_copies_so_snapshot_mutations_dont_leak(self):
        ctx = Context()
        ctx.set("a", 1)
        snap = ctx.snapshot()
        snap["a"] = 999
        self.assertEqual(ctx.get("a"), 1)

    def test_restore_replaces_existing_keys(self):
        ctx = Context()
        ctx.set("keep", "no")
        ctx.set("old", "x")
        ctx.restore({"new": "y"})
        self.assertEqual(ctx.get("new"), "y")
        self.assertNotIn("old", ctx)
        self.assertNotIn("keep", ctx)

    def test_restore_copies_so_caller_mutations_dont_leak(self):
        ctx = Context()
        data = {"v": 1}
        ctx.restore(data)
        data["v"] = 2
        data["extra"] = 3
        self.assertEqual(ctx.get("v"), 1)
        self.assertNotIn("extra", ctx)

    def test_snapshot_then_restore_propagates_to_child_thread(self):
        ctx = Context()
        ctx.set("rid", "parent-req")
        snap = ctx.snapshot()
        seen = {}

        def worker():
            ctx.restore(snap)
            seen["rid"] = ctx.get("rid")
            ctx.set("child_only", True)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        self.assertEqual(seen["rid"], "parent-req")
        self.assertNotIn("child_only", ctx)

    def test_all_returns_copy_not_live_object(self):
        ctx = Context()
        ctx.set("a", 1)
        view = ctx.all()
        view["a"] = 2
        view["b"] = 3
        self.assertEqual(ctx.get("a"), 1)
        self.assertNotIn("b", ctx)

    def test_clear_drops_current_thread_only(self):
        ctx = Context()
        ctx.set("a", 1)
        snap = ctx.snapshot()
        ctx.clear()
        self.assertEqual(ctx.get("a"), None)
        ctx.restore(snap)
        self.assertEqual(ctx.get("a"), 1)

    def test_container_protocol(self):
        ctx = Context()
        ctx.set("a", 1)
        self.assertIn("a", ctx)
        self.assertNotIn("b", ctx)
        self.assertEqual(len(ctx), 1)
        self.assertEqual(sorted(ctx), ["a"])

    def test_multiple_contexts_are_independent(self):
        a = Context()
        b = Context()
        a.set("k", "from-a")
        b.set("k", "from-b")
        self.assertEqual(a.get("k"), "from-a")
        self.assertEqual(b.get("k"), "from-b")


if __name__ == "__main__":
    unittest.main()
