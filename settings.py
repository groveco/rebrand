SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# The original site domain
SESSION_EXCHANGE_ORIGIN_DOMAIN = 'www.epantry.com'
SESSION_EXCHANGE_ORIGIN_URL = 'https://%s' % SESSION_EXCHANGE_ORIGIN_DOMAIN

# The new, rebranded, domain
SESSION_EXCHANGE_DESTINATION_DOMAIN = 'www.grove.co'
SESSION_EXCHANGE_DESTINATION_URL = 'https://%s' % SESSION_EXCHANGE_DESTINATION_DOMAIN

# True if the rebrand has occurred
REBRANDED = True
