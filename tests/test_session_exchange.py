from ..models import SessionExchangeToken
from importlib import import_module
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import TestCase
from pypantry.tests.factories import CustomerFactory
import re
import testsupport
import unittest
import urllib
from uuid import uuid4


SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


class TestInitialRequestToGrove(TestCase):

    @classmethod
    def setUpTestData(cls):
        testsupport.create_default_page()
        testsupport.create_default_flow()
        testsupport.create_socialapp()

    # With a grove.co server
    # And a no session
    # When a request to grove.co/ is made
    # Expect a redirect to epantry.com/session-exchange
    def test_new_session(self):
        path = '/'
        url = '%s/session-exchange/?fwd=%s' % (settings.SESSION_EXCHANGE_ORIGIN_URL, urllib.quote(path, ''))
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_forward_redirect_with_query_parameters(self):
        path = '/?hello=world'
        url = '%s/session-exchange/?fwd=%s' % (settings.SESSION_EXCHANGE_ORIGIN_URL, urllib.quote(path, ''))
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_api_resquest(self):
        path = '/api/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertNotEquals(response.status_code, 302)

    def test_terms_resquest(self):
        path = '/terms/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertNotEquals(response.status_code, 302)

    def test_sitemap_resquest(self):
        path = '/sitemap.xml'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertNotEquals(response.status_code, 302)

    def test_robots_resquest(self):
        path = '/robots.txt'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertNotEquals(response.status_code, 302)

    def test_request_from_origin_domain(self):
        path = '/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertEquals(response.status_code, 200)

    def test_request_from_prerender_user_agent(self):
        path = '/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, HTTP_USER_AGENT='Prerender')
        self.assertEquals(response.status_code, 200)

    def test_request_from_googlebot_user_agent(self):
        path = '/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, HTTP_USER_AGENT='Googlebot')
        self.assertEquals(response.status_code, 200)

    # With a grove.co server
    # And a logged in session
    # When a request to grove.co/ is made
    # Expect 200 OK
    def test_logged_in_session(self):
        self.client.force_login(CustomerFactory())
        response = self.client.get('/', SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertEqual(response.status_code, 200)

    # With a grove.co server
    # And an exchanged session
    # When a request to grove.co/ is made
    # Expect 200 OK
    def test_exchanged_session(self):
        session = self.client.session
        session['is_exchange_complete'] = True
        session.save()
        response = self.client.get('/', SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        self.assertEqual(response.status_code, 200)


class TestExchangeGrant(TestCase):

    # With a epantry.com server
    # And session[xyz] = {}
    # When a request to epantry.com/session-exchange is made
    # Expect a redirect to grove.co/session-exchange/asdf1234
    # Expect session_exchange[asdf1234] to equal "xyz"
    def test_logged_in_session(self):
        self.client.force_login(CustomerFactory())
        response = self.client.get('/session-exchange/', SERVER_NAME=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        match = re.match(r"^.*/session-exchange/(?P<pk>[0-9a-z\-]+)/", response.url)
        token_pk = match.group('pk')
        token = SessionExchangeToken.objects.get(pk=token_pk)
        url = '%s/session-exchange/%s/' % (settings.SESSION_EXCHANGE_DESTINATION_URL, token_pk)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.assertEqual(token.session_key, self.client.session.session_key)

    # With a epantry.com server
    # And no session
    # When a request to epantry.com/session-exchange is made
    # Expect a redirect to grove.co/session-exchange/ghjk5678
    # Expect session_exchange[ghjk5678] to equal ""
    def test_logged_out_session(self):
        self.client.logout()
        response = self.client.get('/session-exchange/', SERVER_NAME=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        match = re.match(r'^.*/session-exchange/(?P<pk>[0-9a-z\-]+)/', response.url)
        token_pk = match.group('pk')
        token = SessionExchangeToken.objects.get(pk=token_pk)
        url = '%s/session-exchange/%s/' % (settings.SESSION_EXCHANGE_DESTINATION_URL, token_pk)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.assertEqual(token.session_key, '')

    def test_forward_request(self):
        fwd = '/demonstration'
        path = '/session-exchange/?fwd=%s' % urllib.quote(fwd, '')
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN)
        match = re.match(r'^.*/session-exchange/(?P<pk>[0-9a-z\-]+)/', response.url)
        token_pk = match.group('pk')
        url = '%s/session-exchange/%s/?fwd=%s' % (settings.SESSION_EXCHANGE_DESTINATION_URL, token_pk, urllib.quote(fwd, ''))
        self.assertRedirects(response, url, fetch_redirect_response=False)


class TestHandoff(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tomorrow = datetime.now() + timedelta(days=1)
        cls.token = SessionExchangeToken.objects.create(session_key='', expires_at=cls.tomorrow)

    def setUp(self):
        self.token.session_key = ''
        self.token.expires_at = self.tomorrow
        self.token.save()

    # With a grove.co server
    # And session_exchange[asdf1234] = "xyz"
    # And no session
    # When a request to grove.co/session-exchange/asdf1234 is made
    # And the Origin header is from epantry.com
    # Expect a session to exist
    # Expect the session id to not equal "xyz"
    # Expect the session's content to equal session[xyz]
    # expect redirect to grove.co/
    def test_existing_origin_session(self):
        url = '%s/' % settings.SESSION_EXCHANGE_DESTINATION_URL
        session = SessionStore()
        session['random-uuid'] = str(uuid4())
        session.save()
        self.token.session_key = session.session_key
        self.token.save()
        path = '/session-exchange/%s/' % self.token.id
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertNotEqual(self.client.session.session_key, session.session_key)
        self.assertEqual(self.client.session.get('random-uuid'), session['random-uuid'])
        self.assertTrue(self.client.session.get('is_exchange_complete'))
        self.assertRedirects(response, url + '?rebrand=1', fetch_redirect_response=False)

    def test_expired_session_exchanged_token(self):
        url = '%s/' % settings.SESSION_EXCHANGE_DESTINATION_URL
        session = SessionStore()
        session['random-uuid'] = str(uuid4())
        session.save()
        self.token.session_key = session.session_key
        self.token.expires_at = datetime.now() - timedelta(seconds=10)
        self.token.save()
        path = '/session-exchange/%s/' % self.token.id
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertNotEqual(self.client.session.get('random-uuid'), session['random-uuid'])
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_origin_session_is_destryed(self):
        session = SessionStore()
        session.save()
        self.token.session_key = session.session_key
        self.token.save()
        path = '/session-exchange/%s/' % self.token.id
        self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertRaises(Session.DoesNotExist, Session.objects.get, session_key=session.session_key)

    # With a grove.co server
    # And session_exchange[asdf1234] = ""
    # And no session
    # When a request to grove.co/session-exchange/asdf1234 is made
    # And the Origin header is from epantry.com
    # Expect a session to exist
    # expect redirect to grove.co/
    def test_empty_origin_session(self):
        url = '%s/' % settings.SESSION_EXCHANGE_DESTINATION_URL
        path = '/session-exchange/%s/' % self.token.id
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertIsNotNone(self.client.session)
        self.assertRedirects(response, url, fetch_redirect_response=False)

    # With a grove.co server
    # And session_exchange[asdf1234] = ""
    # And no session
    # When a request to grove.co/session-exchange/asdf1234?fwd=grove.co/randompage is made
    # And the Origin header is from epantry.com
    # expect redirect to grove.co/randompage
    def test_forward_redirect(self):
        fwd = '/somerandompage'
        path = '/session-exchange/%s/?fwd=%s' % (self.token.id, urllib.quote(fwd, ''))
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertRedirects(response, fwd, fetch_redirect_response=False)

    # With a grove.co server
    # And session_exchange[faketoken] does not exist
    # When a request to grove.co/session-exchange/123-acdf is made
    # And the Origin header is epantry.com
    # Expect 404 Does Not Exist
    def test_invalid_exchange_token(self):
        uuid = uuid4()
        path = '/session-exchange/%s/' % uuid
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertEqual(response.status_code, 404)

    def test_logged_in_destination_session(self):
        self.client.force_login(CustomerFactory())
        url = '%s/' % settings.SESSION_EXCHANGE_DESTINATION_URL
        session = SessionStore()
        session['random-uuid'] = str(uuid4())
        session.save()
        self.token.session_key = session.session_key
        self.token.save()
        path = '/session-exchange/%s/' % self.token.id
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN)
        self.assertIsNone(self.client.session.get('random-uuid'))
        self.assertTrue(self.client.session.get('is_exchange_complete'))
        self.assertRedirects(response, url, fetch_redirect_response=False)


# Skipping for now because getting access to the request origin has been difficult
@unittest.skip
class TestInvalidOrigin(TestCase):

    # With a epantry.co server
    # When a request to epantry.com/session-exchange/ is made
    # And the Origin header is example.com
    # Expect 403 Forbidden
    def test_exchange_grant_request(self):
        path = '/session-exchange/'
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_ORIGIN_DOMAIN, REMOTE_HOST='example.com')
        self.assertEqual(response.status_code, 403)

    def test_handoff_request(self):
        path = '/session-exchange/%s/' % uuid4()
        response = self.client.get(path, SERVER_NAME=settings.SESSION_EXCHANGE_DESTINATION_DOMAIN, REMOTE_HOST='example.com')
        self.assertEqual(response.status_code, 403)
