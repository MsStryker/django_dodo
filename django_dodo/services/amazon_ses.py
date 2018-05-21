from boto.ses.connection import SESConnection

from django.conf import settings

from django_dodo.services.base import EmailService


class AmazonSEService(EmailService):

    def __init__(self, *args, **kwargs):
        """
        Initializes the Amazon SES email service.
        """
        self.connection = None
        self.id = settings.EMAIL_SERVICES_CLIENT_ID
        self.key = settings.EMAIL_SERVICES_CLIENT_KEY

    def open(self):
        """
        Creates the connection that will interact with the Amazon API
        using Boto.
        """
        if self.connection:
            return

        self.connection = SESConnection(aws_access_key_id=self.id,
                                        aws_secret_access_key=self.key)

    def close(self):
        """
        Creates the connection that will interact with the Amazon API
        using Boto.
        """
        if not self.connection:
            return

        self.connection.close()
        self.connection = None

    def send_messages(self, email_messages):
        """
        Sends one or more email messages using throught amazon SES
        using boto.
        """
        if not self.connection:
            self.open()

        for message in email_messages:
            self.connection.send_raw_email(
                source=message.from_email,
                destinations=message.recipients(),
                raw_message=message.message().as_string())
