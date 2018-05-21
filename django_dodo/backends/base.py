"""
The email backend for Critsend's API. This is a thin wrapper
around an email service that exposes more information using the
API than the typical email backends that are only used to send
emails. This is only used as a compatibility layer between django
and what it expects as an email backend and the respective service
"""

import logging
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BaseServiceEmailBackend(BaseEmailBackend):
    """
    Critsend email backend. Can be used as a drop in replacement for
    any of the django email backends. Uses the Critsend SOAP API through
    the respective service calss for sending emails.
    """

    def __init__(self, fail_silently=False, *args, **kwargs):
        """
        Initializes the backend. Set fail_silently to True to make the
        backend not raise on errors.
        """
        self.service = None
        self.fail_silently = fail_silently

    def open(self):
        """
        Delegates opening the connection to the email provider
        to the respective service
        """
        try:
            self.service.open()
        except Exception as e:
            logger.error("Opening connection failed: %s", e)
            if not self.fail_silently:
                raise

    def close(self):
        """
        Delegates closing the connection to the email provider
        to the respective service
        """
        try:
            self.service.close()
        except Exception as e:
            logger.error("Closing connection failed: %s", e)
            if not self.fail_silently:
                raise

    def send_messages(self, messages):
        """
        Sends the messages using the critsend email service

        Arguments:
        - `messages`: The list of EmailMessage instances to send
        """
        try:
            return self.service.send_messages(messages)
        except Exception as e:
            logger.error("Sending email messages failed: %s" % e)
            if not self.fail_silently:
                raise

