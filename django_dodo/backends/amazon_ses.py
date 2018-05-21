from django_dodo.backends.base import BaseServiceEmailBackend
from django_dodo.services.amazon_ses import AmazonSEService


class AmazonSESBackend(BaseServiceEmailBackend):
    """
    Amazon SES email backend. Can be used as a drop in replacement for
    any of the django email backends. Uses the Amazon API through
    the respective service class for sending emails.
    """

    def __init__(self, fail_silently=False, *args, **kwargs):
        """
        Initializes the backend. Set fail_silently to True to make the
        backend not raise on errors.
        """
        self.service = AmazonSEService()
        self.fail_silently = fail_silently
