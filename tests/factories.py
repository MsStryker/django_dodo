from factory.django import DjangoModelFactory
from factory import LazyAttribute, Sequence, SubFactory, post_generation

from django_pigeon.models import EmailTemplate, EmailTheme, EmailWidget, EmailButton


class EmailThemeFactory(DjangoModelFactory):

    class Meta:
        model = EmailTheme


class EmailButtonFactory(DjangoModelFactory):

    class Meta:
        model = EmailButton

    description = Sequence(lambda n: 'Button description: %d' % n)
    theme = SubFactory(EmailThemeFactory)
    text = Sequence(lambda n: 'Go there %d' % n)
    url_link = 'http://example.com'


class EmailWidgetFactory(DjangoModelFactory):

    class Meta:
        model = EmailWidget

    theme = SubFactory(EmailThemeFactory)
    header_theme = SubFactory(EmailThemeFactory)
    header = Sequence(lambda n: 'Header %03d' % n)
    body_theme = SubFactory(EmailThemeFactory)
    body = Sequence(lambda n: 'Body content %03d' % n)


class EmailTemplateFactory(DjangoModelFactory):

    class Meta:
        model = EmailTemplate

    email_type = EmailTemplate.REGISTRATION_REQUEST
    subject = Sequence(lambda n: 'Subject %03d' % n)
    title = Sequence(lambda n: 'Title %03d' % n)
    pre_header = Sequence(lambda n: 'Pre-Header %03d' % n)
    base_theme = SubFactory(EmailThemeFactory)

    @post_generation
    def widgets(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for widget in extracted:
                self.widgets.add(widget)
        else:
            widget = EmailWidgetFactory()
            self.widgets.add(widget)
