from importlib import import_module
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseNotFound
from .models import SessionExchangeToken
from datetime import datetime, timedelta
from .utils import url_add_params
import urllib
import urlparse


def exchange_grant(request):
    fwd = request.GET.get('fwd')
    session_key = request.session.session_key
    expiration_date = datetime.now() + timedelta(seconds=30)
    token = SessionExchangeToken.objects.create(session_key=session_key or '', expires_at=expiration_date)
    url = '%s/session-exchange/%s/' % (settings.SESSION_EXCHANGE_DESTINATION_URL, token.id)

    if fwd:
        url += '?fwd=%s' % urllib.quote(fwd, '')

    return HttpResponseRedirect(url)


def handoff(request, pk):
    fwd = request.GET.get('fwd', '/')

    try:
        token = SessionExchangeToken.objects.get(pk=pk)
    except SessionExchangeToken.DoesNotExist:
        return HttpResponseNotFound('Token not found')

    if request.user.is_anonymous() and not token.is_expired() and token.session_key != '':
        fwd = url_add_params(str(fwd), {'rebrand': '1'})
        SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
        origin_session = SessionStore(session_key=token.session_key)
        request.session.update(origin_session)
        request.session.save()
        origin_session.delete()

    token.delete()
    request.session.update({'is_exchange_complete': True})

    return HttpResponseRedirect(fwd)
