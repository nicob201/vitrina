import threading
import unittest

from vitrina.loops import run_every


class RunEveryTest(unittest.TestCase):
    def test_keeps_running_after_errors(self):
        stop = threading.Event()
        calls, logs = [], []
        done = threading.Event()

        def task():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("boom")
            done.set()

        run_every(0.01, task, "x", logs.append, stop)
        self.assertTrue(done.wait(2))
        stop.set()
        self.assertEqual(logs[0], "x: boom")
        self.assertGreaterEqual(len(calls), 2)

    def test_stop_ends_thread(self):
        stop = threading.Event()
        thread = run_every(0.01, lambda: None, "x", print, stop)
        self.assertTrue(thread.daemon)
        stop.set()
        thread.join(1)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
