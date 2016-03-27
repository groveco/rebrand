from django.test import TestCase
from ..models import SessionExchangeToken
from datetime import datetime, timedelta


class TestSessionExchangeToken(TestCase):

    def test_is_expired_before_expiration(self):
        tomorrow = datetime.now() + timedelta(days=1)
        token = SessionExchangeToken(session_key='foobar', expires_at=tomorrow)
        self.assertFalse(token.is_expired())

    def test_is_expired_after_expiration(self):
        tomorrow = datetime.now() - timedelta(days=1)
        token = SessionExchangeToken(session_key='foobar', expires_at=tomorrow)
        self.assertTrue(token.is_expired())

    def test_is_expired_on_expiration(self):
        now = datetime.now()
        token = SessionExchangeToken(session_key='foobar', expires_at=now)
        self.assertTrue(token.is_expired())
