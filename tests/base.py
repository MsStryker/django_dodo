from django.test import TestCase

from django_pigeon.tests.factories import EmailTemplateFactory
from django_pigeon.models import EmailTemplate


class EmailTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        for item in EmailTemplate.EMAIL_TYPES:
            email_template = EmailTemplateFactory(email_type=item[0],
                                                  release=True,
                                                  subject=item[1],
                                                  title=item[1],
                                                  pre_header=item[1])
            email_template.save()

    @classmethod
    def tearDownClass(cls):
        EmailTemplate.objects.all().delete()
