from __future__ import unicode_literals

from celery import shared_task


@shared_task
def send_user_email(email_id):
    from django_dodo.models import UserEmail
    from django_dodo.email import send_mail

    email = UserEmail.get_email(email_id)
    if email is None:
        return

    email_data = email.email_template.render()
    send_mail(email_data['subject'], email_data['text_body'], email.to_recipient, html_body=email_data['html_body'])


@shared_task
def send_market_email(email_sent_id):
    from django_dodo.models import MarketEmail
    from django_dodo.email import send_mail

    email = MarketEmail.get_email(email_sent_id)
    if email is None:
        return

    email_data = email.email_template.render()
    for recipient in email.to_recipients():
        send_mail(email_data['subject'], email_data['text_body'], recipient, html_body=email_data['html_body'])


@shared_task
def send_network_email(email_sent_id):
    from django_dodo.models import NetworkEmail
    from django_dodo.email import send_mail

    email = NetworkEmail.get_email(email_sent_id)
    if email is None:
        return

    email_data = email.email_template.render()
    send_mail(email_data['subject'],
              email_data['text_body'],
              email.to_recipients(),
              html_body=email_data['html_body'],
              cc=email.cc_recipients(),
              bcc=email.bcc_recipients())
