from django.conf.urls import url

from .views import EmailLinkRedirectView


urlpatterns = [
    # url(r'^$', ContactMessageFormView.as_view(), name='contact'),
    url(r'^lnk/(?P<slug>[\w-]+)/$', EmailLinkRedirectView.as_view(), name='email-redirect'),
]
