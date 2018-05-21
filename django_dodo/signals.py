from django.dispatch import Signal


marked_unread = Signal(providing_args=['read'])


class MessageCourier(object):

    def marked_unread(self, read):
        pass
