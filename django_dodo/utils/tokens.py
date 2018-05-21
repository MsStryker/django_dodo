from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied


REGISTRATION_TOKENS = {
    'activation_url': '{ ACTIVATION_URL }'
}
INVITATION_TOKENS = {
    'activation_url': '{ ACTIVATION_URL }',
    'sender_first_name': '{ SENDER_FIRST_NAME }',
    'sender_full_name': '{ SENDER_FULL_NAME }',
}
USER_TOKENS = {
    'user_first_name': '{ USER_FIRST_NAME }',
    'user_full_name': '{ USER_FULL_NAME }',
    'user_email': '{ USER_EMAIL }',
    'sender_first_name': '{ SENDER_FIRST_NAME }',
    'sender_full_name': '{ SENDER_FULL_NAME }',
    'profile_url': '{ PROFILE_URL }',
    'account_settings_url': '{ ACCOUNT_SETTINGS_URL }',
    'email_management_url': '{ EMAIL_MANAGEMENT_URL }'
}

TOKEN_START = '{'
TOKEN_END = '}'


def get_user_by_email(email, registration=False):
    """
    Returns the User model that is active in this project.
    """
    try:
        if registration:
            UserModel = django_apps.get_model(settings.SITE_REGISTRATION_USER_MODEL)
        else:
            UserModel = django_apps.get_model(settings.SITE_AUTH_USER_MODEL)
    except ValueError:
        raise ImproperlyConfigured("SITE_AUTH_USER_MODEL or SITE_REGISTRATION_USER_MODEL must be of the form "
                                   "'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SITE_AUTH_USER_MODEL or SITE_REGISTRATION_USER_MODEL refers to model '%s' that has not been "
            "installed" % settings.AUTH_USER_MODEL)

    return UserModel.get_user_by_email(email)


def get_email_context(email, registration):
    user = get_user_by_email(email, registration=registration)
    return user.get_email_context()


class Tokens(object):

    def __init__(self):
        self.email = None

    @classmethod
    def get_token_preview_context(cls, registration=False, invitation=False):
        example_url = 'http://example.com'
        if registration:
            tokens = {
                'activation_url': '{}/activation-preview'.format(example_url),
            }
        elif invitation:
            tokens = {
                'activation_url': '{}/invitation-preview'.format(example_url),
                'sender_first_name': 'Sally',
                'sender_full_name': 'Sally Smith',
            }
        else:
            tokens = {
                'user_first_name': 'Jane',
                'user_full_name': 'Jane Doe',
                'user_email': 'janedoe@example.com',
                'sender_first_name': 'Sally',
                'sender_full_name': 'Sally Smith',
                'profile_url': '{}/janedoe'.format(example_url),
                'account_settings_url': '{}/settings'.format(example_url),
                'email_management_url': '{}/email'.format(example_url)}

        return tokens

    @classmethod
    def is_registration(cls, token_context):
        return ('activation_url' in token_context and
                'user_first_name' not in token_context and
                'sender_first_name' not in token_context)

    @classmethod
    def is_invitation(cls, token_context):
        return ('activation_url' in token_context and
                'user_first_name' not in token_context and
                'sender_first_name' in token_context)

    @classmethod
    def replace_tokens(cls, context, dirty_text):
        """
        This should get called after the email is rendered by Django.
        Why? Because of token injections!

        :param context: the context data to replace
        :param dirty_text: the text that need to have tokens replaced
        :return: text that has had tokens replaced
        """
        if not (TOKEN_START in dirty_text and TOKEN_END in dirty_text):
            return dirty_text

        token_context = context
        if cls.is_invitation(token_context):
            token_dict = INVITATION_TOKENS
        elif cls.is_registration(token_context):
            token_dict = REGISTRATION_TOKENS
        elif 'activation_url' in token_context and 'user_first_name' in token_context:
            raise ValueError('Cannot have user tokens and activation tokens together!')
        else:
            token_dict = USER_TOKENS

        domain_url = token_dict.get('domain_url', 'https://morgynstryker.com')
        for key, value in token_dict.items():
            action_url = context.get(key)
            if key.endswith('_url') and action_url:
                context[key] = '{domain_url}{action_url}'.format(domain_url=domain_url, action_url=action_url)

        clean_text = dirty_text
        for key, value in token_context.items():
            token = token_dict.get(key)
            if token:
                clean_text = clean_text.replace(token, value)

        return clean_text
