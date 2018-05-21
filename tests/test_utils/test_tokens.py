from unittest.mock import Mock
from django.test import TestCase

from django_pigeon.tokens import Tokens


class TokensTestCase(TestCase):

    def setUp(self):
        self.context = {
            'protocol': 'https',
            'domain': 'example.com'
        }

    def test_replace_tokens_registration_link(self):
        self.context['activation_url'] = '/activation/test/code'

        dirty_text = 'Here is a dirty link <a href="{ ACTIVATION_URL }">Dirty</a>'
        clean_text = Tokens.replace_tokens(self.context, dirty_text)

        self.assertNotIn('ACTIVATION_URL', clean_text)
        self.assertIn(self.context['activation_url'], clean_text)

