import json
import unittest
from datetime import timedelta
from pathlib import Path

try:
    from jsonschema import Draft202012Validator as JSONValidator
except ImportError:

    def JSONValidator(*a, **k):
        raise unittest.SkipTest("jsonschema module is not available")


from robot.model.statistics import Statistics
from robot.model.stats import SuiteStat, TagStat
from robot.result import TestCase, TestSuite
from robot.utils.asserts import assert_equal


def verify_stat(
    stat,
    name,
    passed,
    failed,
    skipped,
    combined=None,
    id=None,
    elapsed=0.0,
    doc="",
    links=None,
):
    assert_equal(stat.name, name, "stat.name")
    assert_equal(stat.passed, passed)
    assert_equal(stat.failed, failed)
    assert_equal(stat.skipped, skipped)
    assert_equal(stat.total, passed + failed + skipped)
    if isinstance(stat, TagStat):
        assert_equal(stat.combined, combined)
        assert_equal(stat.doc, doc)
        assert_equal(stat.links, links or [])
    if isinstance(stat, SuiteStat):
        assert_equal(stat.id, id)
    assert_equal(stat.elapsed, timedelta(seconds=elapsed))


def verify_suite(suite, name, id, passed, failed, skipped):
    verify_stat(suite.stat, name, passed, failed, skipped, id=id)


def generate_suite():
    suite = TestSuite(name="Root Suite")
    s1 = suite.suites.create(name="First Sub Suite")
    s2 = suite.suites.create(name="Second Sub Suite")
    s11 = s1.suites.create(name="Sub Suite 1_1")
    s12 = s1.suites.create(name="Sub Suite 1_2")
    s13 = s1.suites.create(name="Sub Suite 1_3")
    s21 = s2.suites.create(name="Sub Suite 2_1")
    s22 = s2.suites.create(name="Sub Suite 3_1")
    s11.tests = [
        TestCase(status="PASS"),
        TestCase(status="FAIL", tags=["t1"]),
    ]
    s12.tests = [
        TestCase(status="PASS", tags=["t_1", "t2"]),
        TestCase(status="PASS", tags=["t1", "smoke"]),
        TestCase(status="SKIP", tags=["t1", "flaky"]),
        TestCase(status="FAIL", tags=["t1", "t2", "t3", "smoke"]),
    ]
    s13.tests = [
        TestCase(status="PASS", tags=["t1", "t 2", "smoke"]),
    ]
    s21.tests = [
        TestCase(status="FAIL", tags=["t3", "Smoke"]),
    ]
    s22.tests = [
        TestCase(status="SKIP", tags=["flaky"]),
    ]
    return suite


def validate_schema(statistics):
    with open(
        Path(__file__).parent / "../../doc/schema/result.json", encoding="UTF-8"
    ) as file:
        schema = json.load(file)
    validator = JSONValidator(schema=schema)
    data = {
        "generator": "unit tests",
        "generated": "2024-09-23T14:55:00.123456",
        "rpa": False,
        "suite": {"name": "S", "elapsed_time": 0, "status": "FAIL"},
        "statistics": statistics.to_dict(),
        "errors": [],
    }
    validator.validate(data)


class TestStatisticsSimple(unittest.TestCase):

    def setUp(self):
        suite = TestSuite(name="Hello")
        suite.tests = [
            TestCase(status="PASS"),
            TestCase(status="PASS"),
            TestCase(status="FAIL"),
            TestCase(status="SKIP"),
        ]
        self.statistics = Statistics(suite)

    def test_total(self):
        verify_stat(self.statistics.total.stat, "All Tests", 2, 1, 1)

    def test_suite(self):
        verify_suite(self.statistics.suite, "Hello", "s1", 2, 1, 1)

    def test_tags(self):
        assert_equal(list(self.statistics.tags), [])

    def test_to_dict(self):
        assert_equal(
            self.statistics.to_dict(),
            {
                "total": {"pass": 2, "fail": 1, "skip": 1, "label": "All Tests"},
                "suites": [
                    {
                        "pass": 2,
                        "fail": 1,
                        "skip": 1,
                        "label": "Hello",
                        "name": "Hello",
                        "id": "s1",
                    }
                ],
                "tags": [],
            },
        )
        validate_schema(self.statistics)


class TestStatisticsNotSoSimple(unittest.TestCase):

    def setUp(self):
        suite = generate_suite()
        self.statistics = Statistics(
            suite,
            suite_stat_level=2,
            tag_stat_include=["t*", "smoke"],
            tag_stat_exclude=["t3"],
            tag_stat_combine=[("t? & smoke", ""), ("none NOT t1", "a title")],
            tag_doc=[("smoke", "something is burning")],
            tag_stat_link=[("t2", "uri", "title"), ("t?", "http://uri/%1", "title %1")],
        )

    def test_total(self):
        verify_stat(self.statistics.total.stat, "All Tests", 4, 3, 2)

    def test_suite(self):
        suite = self.statistics.suite
        verify_suite(suite, "Root Suite", "s1", 4, 3, 2)
        [s1, s2] = suite.suites
        verify_suite(s1, "Root Suite.First Sub Suite", "s1-s1", 4, 2, 1)
        verify_suite(s2, "Root Suite.Second Sub Suite", "s1-s2", 0, 1, 1)
        assert_equal(len(s1.suites), 0)
        assert_equal(len(s2.suites), 0)

    def test_tags(self):
        # Tag stats are tested more thoroughly in test_tagstatistics.py
        tags = self.statistics.tags
        assert_equal(len(list(tags)), 5)
        verify_stat(tags.tags["smoke"], "smoke", 2, 2, 0, doc="something is burning")
        verify_stat(tags.tags["t1"], "t1", 3, 2, 1, links=[("http://uri/1", "title 1")])
        verify_stat(tags.tags["t2"], "t2", 2, 1, 0,
                    links=[("uri", "title"), ("http://uri/2", "title 2")])  # fmt: skip
        verify_stat(tags.combined[0], "t? & smoke", 2, 2, 0, "t? & smoke")
        verify_stat(tags.combined[1], "a title", 0, 0, 0, "none NOT t1")

    def test_to_dict(self):
        assert_equal(
            self.statistics.to_dict(),
            {
                "total": {"pass": 4, "fail": 3, "skip": 2, "label": "All Tests"},
                "suites": [
                    {
                        "pass": 4,
                        "fail": 3,
                        "skip": 2,
                        "id": "s1",
                        "name": "Root Suite",
                        "label": "Root Suite",
                    },
                    {
                        "pass": 4,
                        "fail": 2,
                        "skip": 1,
                        "label": "Root Suite.First Sub Suite",
                        "id": "s1-s1",
                        "name": "First Sub Suite",
                    },
                    {
                        "pass": 0,
                        "fail": 1,
                        "skip": 1,
                        "label": "Root Suite.Second Sub Suite",
                        "id": "s1-s2",
                        "name": "Second Sub Suite",
                    },
                ],
                "tags": [
                    {
                        "pass": 0,
                        "fail": 0,
                        "skip": 0,
                        "label": "a title",
                        "info": "combined",
                        "combined": "none NOT t1",
                    },
                    {
                        "pass": 2,
                        "fail": 2,
                        "skip": 0,
                        "label": "t? & smoke",
                        "info": "combined",
                        "combined": "t? & smoke",
                    },
                    {
                        "pass": 2,
                        "fail": 2,
                        "skip": 0,
                        "label": "smoke",
                        "doc": "something is burning",
                    },
                    {
                        "pass": 3,
                        "fail": 2,
                        "skip": 1,
                        "label": "t1",
                        "links": "title 1:http://uri/1",
                    },
                    {
                        "pass": 2,
                        "fail": 1,
                        "skip": 0,
                        "label": "t2",
                        "links": "title:uri:::title 2:http://uri/2",
                    },
                ],
            },
        )
        validate_schema(self.statistics)


class TestSuiteStatistics(unittest.TestCase):

    def test_all_levels(self):
        suite = Statistics(generate_suite()).suite
        verify_suite(suite, "Root Suite", "s1", 4, 3, 2)
        [s1, s2] = suite.suites
        verify_suite(s1, "Root Suite.First Sub Suite", "s1-s1", 4, 2, 1)
        verify_suite(s2, "Root Suite.Second Sub Suite", "s1-s2", 0, 1, 1)
        [s11, s12, s13] = s1.suites
        verify_suite(
            s11, "Root Suite.First Sub Suite.Sub Suite 1_1", "s1-s1-s1", 1, 1, 0
        )
        verify_suite(
            s12, "Root Suite.First Sub Suite.Sub Suite 1_2", "s1-s1-s2", 2, 1, 1
        )
        verify_suite(
            s13, "Root Suite.First Sub Suite.Sub Suite 1_3", "s1-s1-s3", 1, 0, 0
        )
        [s21, s22] = s2.suites
        verify_suite(
            s21, "Root Suite.Second Sub Suite.Sub Suite 2_1", "s1-s2-s1", 0, 1, 0
        )
        verify_suite(
            s22, "Root Suite.Second Sub Suite.Sub Suite 3_1", "s1-s2-s2", 0, 0, 1
        )

    def test_only_root_level(self):
        suite = Statistics(generate_suite(), suite_stat_level=1).suite
        verify_suite(suite, "Root Suite", "s1", 4, 3, 2)
        assert_equal(len(suite.suites), 0)

    def test_deeper_level(self):
        PASS = TestCase(status="PASS")
        FAIL = TestCase(status="FAIL")
        SKIP = TestCase(status="SKIP")
        suite = TestSuite(name="1")
        suite.suites = [TestSuite(name="1"), TestSuite(name="2"), TestSuite(name="3")]
        suite.suites[0].suites = [TestSuite(name="1")]
        suite.suites[1].suites = [TestSuite(name="1"), TestSuite(name="2")]
        suite.suites[2].tests = [PASS, FAIL]
        suite.suites[0].suites[0].suites = [TestSuite(name="1")]
        suite.suites[1].suites[0].tests = [PASS, PASS, PASS, FAIL, SKIP]
        suite.suites[1].suites[1].tests = [PASS, PASS, FAIL, SKIP]
        suite.suites[0].suites[0].suites[0].tests = [FAIL, FAIL, FAIL]
        s1 = Statistics(suite, suite_stat_level=3).suite
        verify_suite(s1, "1", "s1", 6, 6, 2)
        [s11, s12, s13] = s1.suites
        verify_suite(s11, "1.1", "s1-s1", 0, 3, 0)
        verify_suite(s12, "1.2", "s1-s2", 5, 2, 2)
        verify_suite(s13, "1.3", "s1-s3", 1, 1, 0)
        [s111] = s11.suites
        verify_suite(s111, "1.1.1", "s1-s1-s1", 0, 3, 0)
        [s121, s122] = s12.suites
        verify_suite(s121, "1.2.1", "s1-s2-s1", 3, 1, 1)
        verify_suite(s122, "1.2.2", "s1-s2-s2", 2, 1, 1)
        assert_equal(len(s111.suites), 0)

    def test_iter_only_one_level(self):
        [stat] = list(Statistics(generate_suite(), suite_stat_level=1).suite)
        verify_stat(stat, "Root Suite", 4, 3, 2, id="s1")

    def test_iter_also_sub_suites(self):
        stats = list(Statistics(generate_suite()).suite)
        verify_stat(stats[0], "Root Suite", 4, 3, 2, id="s1")
        verify_stat(stats[1], "Root Suite.First Sub Suite", 4, 2, 1, id="s1-s1")
        verify_stat(
            stats[2], "Root Suite.First Sub Suite.Sub Suite 1_1", 1, 1, 0, id="s1-s1-s1"
        )
        verify_stat(
            stats[3], "Root Suite.First Sub Suite.Sub Suite 1_2", 2, 1, 1, id="s1-s1-s2"
        )
        verify_stat(
            stats[4], "Root Suite.First Sub Suite.Sub Suite 1_3", 1, 0, 0, id="s1-s1-s3"
        )
        verify_stat(stats[5], "Root Suite.Second Sub Suite", 0, 1, 1, id="s1-s2")
        verify_stat(
            stats[6],
            "Root Suite.Second Sub Suite.Sub Suite 2_1",
            0,
            1,
            0,
            id="s1-s2-s1",
        )
        verify_stat(
            stats[7],
            "Root Suite.Second Sub Suite.Sub Suite 3_1",
            0,
            0,
            1,
            id="s1-s2-s2",
        )


class TestElapsedTime(unittest.TestCase):

    def setUp(self):
        ts = "2012-08-16 00:00:"
        suite = TestSuite(
            start_time=ts + "00.000",
            end_time=ts + "59.999",
        )
        suite.suites = [
            TestSuite(
                start_time=ts + "00.000",
                end_time=ts + "30.000",
            ),
            TestSuite(
                start_time=ts + "30.000",
                end_time=ts + "42.042",
            ),
        ]
        suite.suites[0].tests = [
            TestCase(
                start_time=ts + "00.000",
                end_time=ts + "00.001",
                tags=["t1"],
            ),
            TestCase(
                start_time=ts + "00.001",
                end_time=ts + "01.001",
                tags=["t1", "t2"],
            ),
        ]
        suite.suites[1].tests = [
            TestCase(
                start_time=ts + "30.000",
                end_time=ts + "40.000",
                tags=["t1", "t2", "t3"],
            )
        ]
        self.stats = Statistics(suite, tag_stat_combine=[("?2", "combined")])

    def test_total_stats(self):
        assert_equal(self.stats.total.stat.elapsed, timedelta(seconds=11.001))

    def test_tag_stats(self):
        t1, t2, t3 = self.stats.tags.tags.values()
        verify_stat(t1, "t1", 0, 3, 0, elapsed=11.001)
        verify_stat(t2, "t2", 0, 2, 0, elapsed=11.000)
        verify_stat(t3, "t3", 0, 1, 0, elapsed=10.000)

    def test_combined_tag_stats(self):
        combined = self.stats.tags.combined[0]
        verify_stat(combined, "combined", 0, 2, 0, combined="?2", elapsed=11.000)

    def test_suite_stats(self):
        assert_equal(self.stats.suite.stat.elapsed, timedelta(seconds=59.999))
        assert_equal(self.stats.suite.suites[0].stat.elapsed, timedelta(seconds=30.000))
        assert_equal(self.stats.suite.suites[1].stat.elapsed, timedelta(seconds=12.042))

    def test_suite_stats_when_suite_has_no_times(self):
        suite = TestSuite()
        assert_equal(Statistics(suite).suite.stat.elapsed, timedelta())
        ts = "2012-08-16 00:00:"
        suite.tests = [
            TestCase(start_time=ts + "00.000", end_time=ts + "00.001"),
            TestCase(start_time=ts + "00.001", end_time=ts + "01.001"),
        ]
        assert_equal(Statistics(suite).suite.stat.elapsed, timedelta(seconds=1.001))
        suite.suites = [
            TestSuite(start_time=ts + "02.000", end_time=ts + "12.000"),
            TestSuite(),
        ]
        assert_equal(Statistics(suite).suite.stat.elapsed, timedelta(seconds=11.001))

    def test_elapsed_from_get_attributes(self):
        for time, expected in [
            ("00:00:00.000", "00:00:00"),
            ("00:00:00.001", "00:00:00"),
            ("00:00:00.500", "00:00:00"),
            ("00:00:00.501", "00:00:01"),
            ("00:00:00.999", "00:00:01"),
            ("00:00:01.000", "00:00:01"),
            ("00:00:01.001", "00:00:01"),
            ("00:00:01.499", "00:00:01"),
            ("00:00:01.500", "00:00:02"),
            ("01:59:59.499", "01:59:59"),
            ("01:59:59.500", "02:00:00"),
        ]:
            suite = TestSuite(
                start_time="2012-08-17 00:00:00.000",
                end_time="2012-08-17 " + time,
            )
            stat = Statistics(suite).suite.stat
            elapsed = stat.get_attributes(include_elapsed=True)["elapsed"]
            assert_equal(elapsed, expected, time)


if __name__ == "__main__":
    unittest.main()
