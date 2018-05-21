import logging
from time import sleep

from boto.ses import SESConnection, connect_to_region
# from boto.regioninfo import RegionInfo

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.cache import cache

LOG = logging.getLogger(__name__)

DAILY_SECONDS = 24 * 60 * 60


class SESBackend(BaseEmailBackend):

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None, region_endpoint=None):
        self.aws_access_key_id = getattr(settings, 'AWS_SES_ACCESS_KEY_ID', aws_access_key_id)
        self.aws_secret_access_key = getattr(settings, 'AWS_SES_SECRET_ACCESS_KEY', aws_secret_access_key)
        self.region_name = getattr(settings, 'AWS_SES_REGION_NAME', region_name)
        self.region_endpoint = getattr(settings, 'AWS_SES_REGION_ENDPOINT', region_endpoint)
        self.region = None
        self.connection = None

    def open(self):
        # if self.region is None:
        #     self.region = RegionInfo(name=self.region_name, endpoint=self.region_endpoint)
        if self.connection:
            return

        self.connection = connect_to_region(self.region_name,
                                            aws_access_key_id=self.aws_access_key_id,
                                            aws_secret_access_key=self.aws_secret_access_key)

    def _send_email(self, email_message):
        if not email_message.to_recipients:
            return False

        try:
            self.connection.send_mail(email_message.from_email,
                                      email_message.subject,
                                      email_message.body,
                                      email_message.to_recipients,
                                      cc_addresses=email_message.cc_recipients,
                                      bcc_addresses=email_message.bcc_recipients,
                                      return_path=settings.MAIL_FROM_DOMAIN)
        except Exception as e:
            LOG.error('Failed to send email: %s', e)
            return False

        return True

    def _send_raw_email(self, email_message):
        if not email_message.to_recipients:
            return False

        try:
            self.connection.send_raw_email(email_message,
                                           email_message.from_email,
                                           email_message.to_recipients)
        except Exception as e:
            LOG.error('Failed to send raw email: %s', e)
            return False

        return True

    def delay(self, num_sent):
        """
        Delay the email sending if needed

        :param num_sent: current emails sent in the batch
        :return: None
        """
        rates = self.get_send_rates()

        seconds_delay = DAILY_SECONDS/(rates['Max24HourSend'] - rates['SentLast24Hours'])
        if num_sent > rates['MaxSendRate']:
            sleep(seconds_delay*2)

    def send_messages(self, email_messages):
        if not email_messages:
            return

        num_sent = 0
        for email_message in email_messages:
            self.delay(num_sent)
            self.open()
            if email_message.alternatives:
                if self._send_raw_email(email_message):
                    num_sent += 1
            else:
                if self._send_email(email_message):
                    num_sent += 1

        return num_sent

    # def send_mass_mail(self, email_messages):
    #     self.send_messages(email_messages)
    #
    # def send_mail(self, subject, body, to_addresses, connection=None, **kwargs):
    #     if connection is None:
    #         connection = self.open()
    #
    #     body = None
    #
    #     text_body = kwargs['text_body']
    #     html_body = kwargs.get('html_body', '')
    #     if html_body is None:
    #         format = 'text'
    #     else:
    #         format = kwargs.get('format', 'html')
    #
    #     from_email = kwargs.get('from_email', settings.DEFAULT_FROM_EMAIL)
    #     return_path = kwargs.get('return_path', settings.MAIL_FROM_DOMAIN)
    #
    #     cc_addresses = kwargs.get('cc_addresses', [])
    #     bcc_addresses = kwargs.get('bcc_addresses', [])
    #
    #     connection.send_email(from_email, subject, body, to_addresses,
    #                           cc_addresses=cc_addresses, bcc_addresses=bcc_addresses,
    #                           format=format, return_path=return_path, text_body=text_body, html_body=html_body)

    def get_send_quota(self):
        self.open()
        return self.connection.get_send_quota()

    def get_send_statistics(self):
        """
        Get the send statistics from AWS, returning the list of SendDataPoints.
            - The list should be in 15 minute intervals

        :return: A list of dicts
            {'Complaints':...
             'Timestamp':...
             'DeliveryAttempts':...
             'Bounces':...
             'Rejects':...}
        """
        self.open()
        response_dict = self.connection.get_send_statistics()
        return response_dict['GetSendStatisticsResponse']['GetSendStatisticsResponse']['SendDataPoints']

    def get_send_rates(self, current=False):
        """
        Get the maximum send rate, we cache the value for 2 minutes to reduce calls to AWS.
        This may need future review, but for now we try.

        :return: The MaxSendRate
        """
        try:
            if current:
                response_dict = self.get_send_quota()
            else:
                response_dict = cache.get_or_set('ses_send_rate', self.get_send_quota(), 120)
        except Exception:
            return 2

        return response_dict['GetSendQuotaResponse']['GetSendQuotaResult']
