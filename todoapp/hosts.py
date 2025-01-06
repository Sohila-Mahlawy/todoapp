from django_hosts import patterns, host
from django.conf import settings

host_patterns = patterns(
    '',
    host(r'www', settings.ROOT_URLCONF, name='www'),  # Default root domain (e.g., netfull.site)
    host(r'(?P<company>[\w-]+)', 'yourproject.company_urls', name='company'),  # For subdomains like ams.netfull.site
)