from datetime import datetime
from django.utils.timezone import utc
from django.db import models
import uuid


_ = lambda s: s


class SessionExchangeToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(_('session key'), max_length=40, default='')
    expires_at = models.DateTimeField(null=False, blank=False, verbose_name=_('expires at'))

    def is_expired(self):
        return self.expires_at.replace(tzinfo=utc) < datetime.now().replace(tzinfo=utc)
