from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_mail(subject, body, recipients, from_email=settings.DEFAULT_FROM_EMAIL, html_body=None,
              bcc=None, cc=None):
    """
    Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
    """
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    if not isinstance(recipients, list):
        recipients = [recipients]

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=recipients,
        cc=cc,
        bcc=bcc
    )
    if html_body is not None:
        email_message.attach_alternative(html_body, 'text/html')

    email_message.send()
