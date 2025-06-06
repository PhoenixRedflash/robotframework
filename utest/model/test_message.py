import unittest
from datetime import datetime

from robot.model import Message
from robot.result import Keyword, Var, While
from robot.result.executionerrors import ExecutionErrors
from robot.utils.asserts import assert_equal, assert_raises


class TestMessage(unittest.TestCase):

    def test_timestamp(self):
        dt = datetime.now()
        assert_equal(Message().timestamp, None)
        assert_equal(Message(timestamp=dt).timestamp, dt)
        assert_equal(Message(timestamp=dt.isoformat()).timestamp, dt)
        msg = Message()
        msg.timestamp = dt
        assert_equal(msg.timestamp, dt)
        msg.timestamp = dt.isoformat()
        assert_equal(msg.timestamp, dt)

    def test_slots(self):
        assert_raises(AttributeError, setattr, Message(), "attr", "value")

    def test_to_dict(self):
        assert_equal(
            Message("Hello!").to_dict(), {"message": "Hello!", "level": "INFO"}
        )
        dt = datetime.now()
        assert_equal(
            Message("<b>Hi!</b>", "WARN", html=True, timestamp=dt).to_dict(),
            {
                "message": "<b>Hi!</b>",
                "level": "WARN",
                "html": True,
                "timestamp": dt.isoformat(),
            },
        )

    def test_id_without_parent(self):
        assert_equal(Message().id, "m1")

    def test_id_with_keyword_parent(self):
        kw = Keyword()
        assert_equal(kw.body.create_message().id, "k1-m1")
        assert_equal(kw.body.create_message().id, "k1-m2")
        assert_equal(kw.body.create_keyword().id, "k1-k1")
        assert_equal(kw.body.create_message().id, "k1-m3")
        assert_equal(kw.body.create_keyword().body.create_message().id, "k1-k2-m1")

    def test_id_with_control_parent(self):
        for parent in Var(), While():
            assert_equal(parent.body.create_message().id, "k1-m1")
            assert_equal(parent.body.create_message().id, "k1-m2")

    def test_id_with_errors_parent(self):
        errors = ExecutionErrors()
        assert_equal(errors.messages.create().id, "errors-m1")
        assert_equal(errors.messages.create().id, "errors-m2")

    def test_id_when_item_not_in_parent(self):
        kw = Keyword()
        assert_equal(Message(parent=kw).id, "k1-m1")
        assert_equal(kw.body.create_message().id, "k1-m1")
        assert_equal(kw.body.create_message().id, "k1-m2")
        assert_equal(Message(parent=kw).id, "k1-m3")


class TestHtmlMessage(unittest.TestCase):

    def test_empty(self):
        assert_equal(Message().html_message, "")
        assert_equal(Message(html=True).html_message, "")

    def test_no_html(self):
        assert_equal(Message("Hello, Kitty!").html_message, "Hello, Kitty!")
        assert_equal(
            Message("<b> & ftp://url").html_message,
            '&lt;b&gt; &amp; <a href="ftp://url">ftp://url</a>',
        )

    def test_html(self):
        assert_equal(Message("Hello, Kitty!", html=True).html_message, "Hello, Kitty!")
        assert_equal(Message("<b> & ftp://x", html=True).html_message, "<b> & ftp://x")


class TestStringRepresentation(unittest.TestCase):

    def setUp(self):
        self.empty = Message()
        self.ascii = Message("Kekkonen", level="WARN")
        self.non_ascii = Message("hyvä")

    def test_str(self):
        for tc, expected in [
            (self.empty, ""),
            (self.ascii, "Kekkonen"),
            (self.non_ascii, "hyvä"),
        ]:
            assert_equal(str(tc), expected)

    def test_repr(self):
        for tc, expected in [
            (self.empty, "Message(message='', level='INFO')"),
            (self.ascii, "Message(message='Kekkonen', level='WARN')"),
            (self.non_ascii, "Message(message='hyvä', level='INFO')"),
        ]:
            assert_equal(repr(tc), "robot.model." + expected)


if __name__ == "__main__":
    unittest.main()
