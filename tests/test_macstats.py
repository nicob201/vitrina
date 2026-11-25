import importlib
import subprocess
import sys
import time
import unittest
from unittest import mock

from tests.test_metrics import REAL_PMSET
from vitrina import macstats
from vitrina.macstats import (computer_name, ram_total, read_battery, read_cpu_ticks, read_disk, read_gpu,
                              read_memory_used, read_net)
from vitrina.metrics import cpu_percent


class CommandsTest(unittest.TestCase):
    def test_battery_uses_pmset(self):
        run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout=REAL_PMSET))
        self.assertEqual(read_battery(run), {"pct": 80, "state": "ac"})
        self.assertEqual(run.call_args.args[0], ["/usr/bin/pmset", "-g", "batt"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_battery_failure_is_none(self):
        self.assertIsNone(read_battery(mock.Mock(return_value=subprocess.CompletedProcess([], 1, stdout=""))))

    def test_computer_name(self):
        run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout="MacBook Air de Nico\n"))
        self.assertEqual(computer_name(run), "MacBook Air de Nico")
        self.assertEqual(run.call_args.args[0], ["/usr/sbin/scutil", "--get", "ComputerName"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_computer_name_falls_back_to_mac(self):
        for run in (mock.Mock(side_effect=subprocess.TimeoutExpired("scutil", 10)),
                    mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout="  \n")),
                    mock.Mock(return_value=subprocess.CompletedProcess([], 1, stdout="x\n")),
                    mock.Mock(side_effect=FileNotFoundError())):
            with self.subTest(run=run):
                self.assertEqual(computer_name(run), "Mac")

    def test_importing_loads_no_framework(self):  # runs everywhere
        with mock.patch("ctypes.CDLL") as cdll:
            importlib.reload(macstats)
        cdll.assert_not_called()


class GpuTypeTest(unittest.TestCase):
    """A driver that ever answered with another type must not crash vitrina: a wrong CF call can't be caught."""
    DICT, NUMBER = 18, 22

    def read_with(self, types):
        iokit, cf = mock.Mock(), mock.Mock()
        iokit.IOServiceGetMatchingServices.return_value = 0
        iokit.IOIteratorNext.side_effect = [7, 0]
        iokit.IORegistryEntryCreateCFProperty.return_value = 100  # the statistics, if a dictionary
        cf.CFDictionaryGetValue.return_value = 200  # the utilization, if a number
        cf.CFGetTypeID.side_effect = lambda ref: types[ref]
        with mock.patch("vitrina.macstats._iokit", return_value=(iokit, cf, ("perf", "util"), (self.DICT, self.NUMBER))):
            return read_gpu(), iokit, cf

    def test_statistics_that_are_not_a_dictionary_are_skipped(self):
        gpu, iokit, cf = self.read_with({100: 99})
        self.assertIsNone(gpu)
        cf.CFDictionaryGetValue.assert_not_called()
        cf.CFRelease.assert_called_once_with(100)
        iokit.IOObjectRelease.assert_any_call(7)

    def test_a_utilization_that_is_not_a_number_is_skipped(self):
        gpu, _, cf = self.read_with({100: self.DICT, 200: 99})
        self.assertIsNone(gpu)
        cf.CFNumberGetValue.assert_not_called()


@unittest.skipUnless(sys.platform == "darwin", "macOS only")
class RealReadersTest(unittest.TestCase):
    def test_values_in_range(self):
        a = read_cpu_ticks()
        time.sleep(0.2)
        b = read_cpu_ticks()
        pct = cpu_percent(a, b)
        self.assertTrue(pct is None or 0 <= pct <= 100, pct)
        self.assertTrue(0 < read_memory_used() < ram_total())
        gpu = read_gpu()
        self.assertTrue(gpu is None or 0 <= gpu <= 100, gpu)
        net = read_net()
        self.assertTrue(all(name.startswith("en") for name in net), net)
        self.assertTrue(all(rx >= 0 and tx >= 0 for rx, tx in net.values()), net)
        d = read_disk()
        self.assertTrue(0 <= d["free"] <= d["total"])


if __name__ == "__main__":
    unittest.main()
