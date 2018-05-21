from django.conf import settings
from django.contrib.sites.models import Site


def get_domain_context():
    current_site = Site.objects.get(pk=settings.SITE_ID)
    site_name = current_site.name
    domain = current_site.domain
    if settings.USES_HTTPS and not settings.DEBUG:
        protocol = 'https'
    else:
        protocol = 'http'

    return {'domain_url': '{}://{}'.format(protocol, domain),
            'site_name': site_name}
