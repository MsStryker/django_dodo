"""
Base classes for the services implementation
"""


class EmailServiceError(Exception):
    """
    Base exception that the services should throw on error
    """
    pass


class EmailService(object):
    """
    Base service. Actual services subclass this one
    in order to keep a consistent API. This could be
    the actual backend but to keep the backend api close
    to the one provided by django the choice was to separate
    the differences and name the whole thing a service.

    In the base class all the methods throw a NotImplementedError
    """

    def open(self):
        """
        If the service is not initialized this is where the
        service initialization should be implemented
        """
        raise NotImplementedError

    def close(self):
        """
        If the service is initialized this should close it
        making it unavailable.
        """
        raise NotImplementedError

    def send_messages(self, messages):
        """
        Sends a list of EmailMessage (or EmailMultiAlternatives)
        instances that represent email messages using the service
        API
        """
        raise NotImplementedError
