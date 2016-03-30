from django import http
from django.conf import settings
import urllib
import urlparse


IGNORE_AGENTS = [
    'AdsBot-Google',
    'Mediapartners-Google',
    'Googlebot',
    'Prerender'
]
IGNORE_PATHS = [
    '/session-exchange/',
    '/api/',
    '/terms/',
    '/robots.txt',
    '/sitemap.xml',
]
IGNORE_REBRAND_PATHS = [
    '/session-exchange/',
    '/api/o/'  # oauth
]


def build_url_params(params):
    return '?' + '&'.join(['%s=%s' % (k, v) for k, v in params.iteritems()])


def url_add_params(url, params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.urlencode(query)
    return urlparse.urlunparse(url_parts)


class RebrandMiddleware(object):

    @staticmethod
    def _should_redirect(request):
        host = request.get_host()
        return (settings.REBRANDED or request.user.is_staff()) \
            and host == settings.SESSION_EXCHANGE_ORIGIN_DOMAIN \
            and 'local' not in host \
            and not any([p in request.path for p in IGNORE_REBRAND_PATHS])

    @staticmethod
    def process_request(request):
        if RebrandMiddleware._should_redirect(request):
            url = '%s%s%s' % (settings.SESSION_EXCHANGE_DESTINATION_URL,
                              request.path,
                              build_qs_string(request))
            url = url_add_params(url, {'epredirect': '1'})
            return http.HttpResponsePermanentRedirect(url)
        return None


class SessionExchangeMiddleware(object):

    @staticmethod
    def process_request(request):
        is_whitelisted_agent = 'HTTP_USER_AGENT' in request.META and any(x in request.META['HTTP_USER_AGENT'] for x in IGNORE_AGENTS)
        is_whitelisted_path = any(x in request.path for x in IGNORE_PATHS)

        if not is_whitelisted_path \
           and not is_whitelisted_agent \
           and request.get_host() == settings.SESSION_EXCHANGE_DESTINATION_DOMAIN \
           and not request.session.get('is_exchange_complete', False) \
           and request.user.is_anonymous():
            fwd = request.get_full_path()
            url = '%s/session-exchange/?fwd=%s' % (settings.SESSION_EXCHANGE_ORIGIN_URL, urllib.quote(fwd, ''))

            return http.HttpResponseRedirect(url)
        else:
            return None
