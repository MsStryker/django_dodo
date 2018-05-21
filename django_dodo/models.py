from __future__ import unicode_literals

import base64
import uuid
from datetime import timedelta
import logging

from django.db import models
# from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core import urlresolvers, signing
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template.loader import get_template

from sortedm2m.fields import SortedManyToManyField
from colorfield.fields import ColorField

from django_dodo.backends.backends import SESBackend
from django_dodo.email import send_mail
from django_dodo.tasks import send_user_email, send_market_email, send_network_email
from django_dodo.utils.context import get_domain_context
from django_dodo.utils.tokens import Tokens, get_user_by_email

LOG = logging.getLogger(__name__)


User = get_user_model()


@python_2_unicode_compatible
class Notification(models.Model):
    SYSTEM_NOTIFICATION = 'SN'
    USER_NOTIFICATION = 'UN'
    ADMIN_NOTIFICATION = 'AN'
    ALERT_NOTIFICATION = 'AN'

    NOTIFICATION_CHOICES = (
        (SYSTEM_NOTIFICATION, _('System notification')),
        (USER_NOTIFICATION, _('User notification')),
        (ADMIN_NOTIFICATION, _('Admin notification')),
        (ALERT_NOTIFICATION, _('Alert notification'))
    )

    timestamp = models.DateTimeField(auto_now=True)
    notification_type = models.CharField(max_length=3, choices=NOTIFICATION_CHOICES)
    description = models.TextField()

    def __str__(self):
        return "%s: %s" % (self.notification_type_display_name, self.timestamp)


@python_2_unicode_compatible
class EmailStats(models.Model):
    timestamp = models.DateField(unique=True, db_index=True)
    delivery_attempts = models.PositiveIntegerField(default=0)
    bounces = models.PositiveIntegerField(default=0)
    complaints = models.PositiveIntegerField(default=0)
    rejects = models.PositiveIntegerField(default=0)
    sent_24h = models.PositiveIntegerField(default=0)
    max_24h = models.PositiveIntegerField(default=200)
    per_second_rate = models.PositiveIntegerField(default=28)

    class Meta:
        verbose_name_plural = _('Email Stats')
        ordering = ['-timestamp']

    def __str__(self):
        return self.timestamp.strftime("%Y-%m-%d")

    @classmethod
    def create_stat(cls, item, send_quota=None):
        obj = cls(delivery_attempts=item['DeliveryAttempts'],
                  bounces=item['Bounces'],
                  complaints=item['Complaints'],
                  rejects=item['Rejects'],
                  timestamp=item['Timestamp'])
        if send_quota:
            obj.sent_24h = send_quota['SentLast24Hours']
            obj.max_24h = send_quota['Max24HourSend']
            obj.per_second_rate = send_quota['MaxSendRate']

        obj.save()

    @classmethod
    def update_send_stats(cls):
        last_entry = None
        send_stats = SESBackend().get_send_statistics()
        send_quota = SESBackend().get_send_rates()
        entries = cls.objects.all()
        if entries.exists():
            last_entry = entries[0]

        for item in send_stats:
            if last_entry and item['Timestamp'] == last_entry:
                last_entry.delivery_attempts = item['DeliveryAttempts']
                last_entry.bounces = item['Bounces']
                last_entry.complaints = item['Complaints']
                last_entry.rejects = item['Rejects']
                last_entry.save()
            elif last_entry and item['Timestamp'] > last_entry.timestamp:
                cls.create_stat(item, send_quota=send_quota)
            elif last_entry is None:
                cls.create_stat(item, send_quota=send_quota)

    @classmethod
    def get_send_stats(cls, filter_dt=timezone.now()-timedelta(days=30)):
        return cls.objects.filter(timestamp__gte=filter_dt).order_by('-timestamp')


@python_2_unicode_compatible
class EmailModel(models.Model):
    description = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.UUIDField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_edited_by = models.UUIDField(blank=True, null=True)
    last_edited_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if not self.description:
            return 'NA'
        return self.description


class EmailTheme(EmailModel):
    TEXT_ALIGN_CHOICES = (
        ('left', 'left'),
        ('right', 'right'),
        ('center', 'center'),
        ('inherit', 'inherit')
    )
    font_family = models.CharField(max_length=250, default='Helvetica, Arial, sans-serif')
    font_size = models.PositiveIntegerField(default=16, validators=[MaxValueValidator(52)])
    line_height = models.PositiveIntegerField(default=18, validators=[MaxValueValidator(56)])
    width = models.PositiveIntegerField(default=500, validators=[MaxValueValidator(600)])
    background_color = ColorField(default='#FFFFFF')
    color = ColorField(default='#000000')
    border_color = ColorField(default='#333333')
    border_width = models.CharField(default='0', max_length=20)
    border_style = models.CharField(max_length=20, default='solid')
    border_radius = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(50)])
    text_align = models.CharField(max_length=20, choices=TEXT_ALIGN_CHOICES, default=TEXT_ALIGN_CHOICES[0][0])
    outer_padding = models.CharField(max_length=100, default='20px')
    inner_padding = models.CharField(max_length=100, default='15px 25px')

    def __str__(self):
        return '{} ({}px:{})'.format(self.description, self.font_size, self.text_align)


@python_2_unicode_compatible
class EmailButton(models.Model):
    description = models.CharField(max_length=50, help_text="Description of button")
    theme = models.ForeignKey(EmailTheme, related_name='button_theme')
    text = models.CharField(max_length=50, default='Go There &rarr;')
    url_link = models.CharField(_('URL Link'), max_length=100)

    def __str__(self):
        if not self.description:
            return 'NA'
        return self.description


@python_2_unicode_compatible
class EmailWidget(EmailModel):
    BRAND_LOGO = 'brand'
    HEADER = 'header'
    BODY = 'body'
    FOOTER = 'footer'
    FOOTER_MARKETING = 'footer_marketing'
    DUAL_COLUMN = 'dual_column'
    COLUMN_PIC = 'column_pic'
    PRODUCT_HEADER = 'product_header'

    WIDGET_TYPES = (
        (BRAND_LOGO, _('Brand')),
        (HEADER, _('Header')),
        (BODY, _('Body')),
        (FOOTER, _('Footer')),
        (FOOTER_MARKETING, _('Footer Marketing')),
        (PRODUCT_HEADER, _('Product Header')),
        (DUAL_COLUMN, _('Two column')),
        (COLUMN_PIC, _('Column with pic'))

    )
    TEXT_ALIGN_CHOICES = (
        ('left', 'left'),
        ('right', 'right'),
        ('center', 'center'),
        ('inherit', 'inherit')
    )
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    direction_ltr = models.BooleanField(
        default=False,
        help_text="Images will be on the left, if false. Use with column/pic widgets.")
    image = models.ImageField(upload_to="email", blank=True, null=True)
    image_alt_text = models.CharField(max_length=100, blank=True, null=True)
    alt_text_size = models.PositiveIntegerField(default=14)

    theme = models.ForeignKey(EmailTheme, related_name='widget_global_theme')

    header_theme = models.ForeignKey(
        EmailTheme,
        blank=True,
        null=True,
        related_name='header_theme',
        on_delete=models.PROTECT)
    header = models.TextField(
        blank=True,
        null=True,
        help_text='Default content, or the left most content.')

    body_theme = models.ForeignKey(
        EmailTheme,
        blank=True,
        null=True,
        related_name='body_theme',
        on_delete=models.PROTECT)
    body = models.TextField(blank=True, null=True, help_text='Right most content, if any.')

    button = models.ForeignKey(EmailButton, blank=True, null=True)

    def __str__(self):
        return '{} ({})'.format(self.description, self.get_widget_type_display())

    @property
    def path(self):
        return 'django_dodo/widgets/{template}.html'.format(template=self.widget_type)

    @property
    def is_footer(self):
        return self.widget_type in [self.FOOTER, self.FOOTER_MARKETING]

    @property
    def is_brand(self):
        return self.widget_type == self.BRAND_LOGO

    def clean(self):
        if self.widget_type in [self.HEADER, self.PRODUCT_HEADER]:
            if not self.image:
                raise ValidationError(_('Must contain an image'))
        if self.widget_type == self.BODY:
            if not self.header and not self.body:
                raise ValidationError(_('Must contain header or body'))


@python_2_unicode_compatible
class EmailTemplate(EmailModel):
    IDENTITY_VERIFICATION = 'IV'
    PASSWORD_CHANGED = 'PC'
    PASSWORD_RESET = 'PR'
    USERNAME_CHANGED = 'UC'
    REGISTRATION_REQUEST = 'R'
    REGISTRATION_INVITATION = 'AI'
    ACCOUNT_CREATED = 'AC'
    ACCOUNT_ALERT = 'AA'
    SECURITY_ALERT = 'SA'
    DAILY_NOTIFICATION = 'DN'
    WEEKLY_NOTIFICATION = 'WN'
    WATCHERS = 'W'
    BLOG_DAILY_SUBSCRIPTION = 'BDS'
    BLOG_WEEKLY_SUBSCRIPTION = 'BWS'
    COMIC_DAILY_SUBSCRIPTION = 'CDS'
    COMIC_WEEKLY_SUBSCRIPTION = 'CWS'

    USER_EMAILS = [
        IDENTITY_VERIFICATION,
        PASSWORD_CHANGED,
        PASSWORD_RESET,
        USERNAME_CHANGED,
        REGISTRATION_REQUEST,
        REGISTRATION_INVITATION,
        ACCOUNT_CREATED,
    ]

    EMAIL_TYPES = (
        (IDENTITY_VERIFICATION, _('Identity Verification Email')),
        (USERNAME_CHANGED, _('Username Changed')),
        (PASSWORD_CHANGED, _('Password Changed')),
        (PASSWORD_RESET, _('Password Reset')),
        (REGISTRATION_REQUEST, _('Registration Request')),
        (REGISTRATION_INVITATION, _('Registration Invitation')),
        (ACCOUNT_CREATED, _('Account Created')),
        (ACCOUNT_ALERT, _('Account Alert')),
        (SECURITY_ALERT, _('Security Alert')),
        (DAILY_NOTIFICATION, _('Daily Notification')),
        (WEEKLY_NOTIFICATION, _('Weekly Notification')),
        (WATCHERS, _('Show watchers')),
        (BLOG_DAILY_SUBSCRIPTION, _('Blog Daily Subscription')),
        (BLOG_WEEKLY_SUBSCRIPTION, _('Blog Weekly Subscription')),
        (COMIC_DAILY_SUBSCRIPTION, _('Comic Daily Subscription')),
        (COMIC_WEEKLY_SUBSCRIPTION, _('Comic Weekly Subscription'))
    )
    TEMPLATE_1 = 'base'
    TEMPLATE_2 = 'base2'
    TEMPLATE_3 = 'base3'
    TEMPLATE_4 = 'base4'
    TEMPLATE_CHOICES = (
        (TEMPLATE_1, _('base')),
        (TEMPLATE_2, _('boxed')),
        (TEMPLATE_3, _('boxed footer below')),
        (TEMPLATE_4, _('boxed brand above footer below'))
    )
    base_template = models.CharField(max_length=12, choices=TEMPLATE_CHOICES, default=TEMPLATE_1)
    default_template = models.BooleanField(_('default'), default=False)
    release = models.BooleanField(default=False)
    email_type = models.CharField(max_length=3, choices=EMAIL_TYPES)
    base_theme = models.ForeignKey(EmailTheme, related_name='email_template_theme')
    subject = models.CharField(max_length=150, help_text='Subject line of email')
    title = models.CharField(max_length=150, help_text='Title for email HTML')
    pre_header = models.CharField(max_length=250, help_text='The text that displays below subject line')
    widgets = SortedManyToManyField(EmailWidget, related_name='email_templates')

    def __str__(self):
        return '{}: default={}'.format(self.get_email_type_display(), self.default_template)

    @property
    def is_registration_invite(self):
        return self.email_type == self.REGISTRATION_INVITATION

    @property
    def is_registration_request(self):
        return self.email_type == self.REGISTRATION_REQUEST

    def widget_list(self):
        return [ew.widgets for ew in EmailContentItem.objects.filter(email_template=self).order_by('order')]

    def get_context_data(self, extra_context=None):
        current_site = get_current_site(None)
        admin_prefix = 'admin.'
        site_name = current_site.name
        domain = current_site.domain
        if site_name.startswith(admin_prefix):
            site_name = site_name[len(admin_prefix):]
        if domain.startswith(admin_prefix):
            domain = domain[len(admin_prefix):]

        context = {
            'protocol': 'https',
            'site_name': site_name,
            'domain': domain,
            'email_template': self,
            'widgets': self.widgets.all()
        }
        context.update(extra_context or {})
        return context

    def render_subject(self, context):
        if self.subject is None:
            return self.get_email_type_display()
        return Tokens.replace_tokens(context, self.subject)

    def render_html(self, context):
        template = 'django_dodo/{template}.html'.format(template=self.base_template)
        rendered_html = get_template(template).render(context)
        return Tokens.replace_tokens(context, rendered_html)

    def render_text(self, context, template='django_dodo/base.txt'):
        rendered_text = get_template(template).render(context)
        return Tokens.replace_tokens(context, rendered_text)

    def render_template(self, context):
        html_body = self.render_html(context)
        text_body = self.render_text(context)
        subject = self.render_subject(context)
        return {'subject': subject,
                'body': html_body,
                'html_body': html_body,
                'text_body': text_body}

    def render_preview(self, context=None):
        if context is None:
            context = self.get_context_data()

        token_context = Tokens.get_token_preview_context(registration=self.is_registration_request,
                                                         invitation=self.is_registration_invite)
        context.update(token_context or {})
        return self.render_template(context)

    def render(self, extra_context=None):
        context = self.get_context_data(extra_context=extra_context)
        return self.render_template(context)

    @classmethod
    def get_email_template(cls, email_type):
        objs = cls.objects.filter(release=True, email_type=email_type)

        if objs.count() > 1:
            default_obj = objs.filter(default_template=True)
            if default_obj.exists():
                return default_obj
        elif objs.count() == 0:
            return
        elif objs.count() == 1:
            return objs.get()

        return objs[0]

    def _set_unique_default_template(self):
        if self.default_template:
            objs = EmailTemplate.objects.filter(default_template=True, email_type=self.email_type)
            if self.pk:
                objs = objs.exclude(pk=self.pk)
            objs.update(default_template=False)

    def save(self, *args, **kwargs):
        self._set_unique_default_template()
        super(EmailTemplate, self).save(*args, **kwargs)


@python_2_unicode_compatible
class EmailContentItem(models.Model):
    order = models.PositiveIntegerField()
    email_template = models.ForeignKey(EmailTemplate, related_name='template_widgets', on_delete=models.CASCADE)
    email_widget = models.ForeignKey(EmailWidget, related_name='ordered_widgets', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('email_template', 'order')
        ordering = ['order']

    def __str__(self):
        return '{} ({} - {})'.format(self.email_template, self.order, self.email_widget)


@python_2_unicode_compatible
class EmailRecipient(models.Model):
    user_id = models.UUIDField(blank=True, null=True)
    email = models.CharField(max_length=200, unique=True, db_index=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

    @property
    def user(self):
        try:
            user = User.get_user_by_email(self.email)
        except User.DoesNotExist:
            return
        return user

    def get_token_context(self, registration=False):
        user = get_user_by_email(self.email, registration=registration)
        return {'system_tokens': user.get_email_context()}

    @classmethod
    def get_or_create(cls, email):
        try:
            obj = cls.objects.get(email=email)
        except cls.DoesNotExist:
            try:
                user = User.get_user_by_email(email)
            except User.DoesNotExist:
                obj = cls(email=email)
            else:
                obj = cls(email=email, user_id=user.uuid)

            obj.save()

        if obj.user_id is None:
            try:
                user = User.get_user_by_email(email)
                obj.user_id = user.uuid
                obj.save(update_fields=['user_id'])
            except User.DoesNotExist:
                pass

        return obj


@python_2_unicode_compatible
class EmailLink(models.Model):
    email_url = models.CharField(max_length=250, unique=True, db_index=True)
    redirect_url = models.TextField()
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(auto_now=False, blank=True, null=True)

    def __str__(self):
        return self.email_url

    @classmethod
    def generate_url(cls, user_email, redirect_url):
        token_dict = {'url': redirect_url, 'email': user_email}
        value = signing.dumps(token_dict)
        return base64.b64encode(value)

    @classmethod
    def create(cls, user_email, redirect_url):
        email_url = cls.generate_url(user_email, redirect_url)
        obj = cls(email_url=email_url, redirect_url=redirect_url)
        obj.save()

    @classmethod
    def get_redirect_link(cls, email_url):
        try:
            obj = cls.objects.get(email_url=email_url)
        except cls.DoesNotExist:
            return None

        obj.clicked = True
        obj.clicked_at = timezone.now()
        obj.save()
        return obj


@python_2_unicode_compatible
class EmailTag(models.Model):
    tag = models.CharField(max_length=50)

    def __str__(self):
        return self.tag


class AbstractEmailModel(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.PROTECT)
    primary_to = models.ForeignKey(EmailRecipient, related_name='%(class)s_primary_recipient')
    sender = models.ForeignKey(EmailRecipient, related_name='%(class)s_sender', blank=True, null=True)
    links = models.ManyToManyField(EmailLink, related_name='%(class)s_links')
    tags = models.ManyToManyField(EmailTag, related_name='%(class)s_tags')
    context_data = models.TextField(max_length=500, blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    timestamp_sent = models.DateTimeField(auto_now=False, db_index=True, blank=True, null=True)
    bounced = models.BooleanField(default=False)
    timestamp_resend = models.DateTimeField(help_text='Timestamp to request resend',
                                            auto_now=False, blank=True, null=True)
    resend_requester = models.UUIDField(blank=True, null=True)

    class Meta:
        abstract = True

    def _set_context_data(self):
        if isinstance(self.context_data, dict):
            self.context_data = str(self.context_data)

    def get_context_data(self):
        return eval(self.context_data)

    @classmethod
    def get_email(cls, email_id):
        try:
            obj = cls.objects.get(pk=email_id)
        except cls.DoesNotExist:
            return
        return obj

    def save(self, *args, **kwargs):
        self._set_context_data()
        super(AbstractEmailModel, self).save(*args, **kwargs)


@python_2_unicode_compatible
class MarketEmail(AbstractEmailModel):
    to = models.ManyToManyField(EmailRecipient, related_name='market_email_to_recipients')

    def __str__(self):
        return '{} {} {}'.format(self.email_template, self.timestamp_sent, self.to)

    def to_recipients(self):
        primary_to = self.primary_to.email
        to_recipients = self.to.all()
        recipient_list = to_recipients.values_list('email', flat=True)
        if primary_to not in recipient_list:
            recipient_list = recipient_list.append(primary_to)

        return recipient_list

    def send(self):
        send_market_email(self.id)


@python_2_unicode_compatible
class NetworkEmail(AbstractEmailModel):
    to = models.ManyToManyField(EmailRecipient, related_name='network_email_to_recipients')
    cc = models.ManyToManyField(EmailRecipient, related_name='network_email_cc_recipients')
    bcc = models.ManyToManyField(EmailRecipient, related_name='network_email_bcc_recipients')

    def __str__(self):
        return '{} {} {}'.format(self.email_template, self.timestamp_sent, self.to)

    def to_recipients(self):
        primary_to = self.primary_to.email
        to_recipients = self.to.all()
        recipient_list = to_recipients.values_list('email', flat=True)
        if primary_to not in recipient_list:
            recipient_list = recipient_list.append(primary_to)

        return recipient_list

    def cc_recipients(self):
        return self.cc.all().values_list('email', flat=True)

    def bcc_recipients(self):
        return self.bcc.all().values_list('email', flat=True)

    @classmethod
    def send(self, to_recipients, cc_recipients, bcc_recipients, email_type):
        if email_type in EmailTemplate.USER_EMAILS:
            return
        email_template = EmailTemplate.get_email_template(email_type)
        to_list = []
        for recipient in to_recipients:
            to_list.append(EmailRecipient.get_or_create(recipient))
        send_network_email(self.id)


@python_2_unicode_compatible
class UserEmail(AbstractEmailModel):

    class Meta:
        verbose_name = 'User Email'
        verbose_name_plural = 'User Emails'

    def __str__(self):
        return '{} {} {}'.format(self.email_template, self.timestamp_sent, self.primary_to)

    @property
    def to_recipient(self):
        return [self.primary_to.email]

    @classmethod
    def get_recent_count_last_time(cls):
        objs = cls.objects.filter(timestamp_sent__gte=timezone.now() - timedelta(days=1)).order_by('-timestamp_sent')
        return objs.count(), objs[0]

    @classmethod
    def send_email_task(cls, email, email_type):
        email_template = EmailTemplate.get_email_template(email_type)
        recipient = EmailRecipient.get_or_create(email)
        if email_template:
            email = cls.objects.create(email_template=email_template, primary_to=recipient)
            send_user_email([email.id])
        else:
            LOG.error('Cannot find %s for user: %s', email_type, email)

    @classmethod
    def create_and_send(cls, user, email_type, sender=None, extra_context=None):
        if extra_context is None:
            extra_context = {}

        email_template = EmailTemplate.get_email_template(email_type)
        recipient = EmailRecipient.get_or_create(user.email)
        if sender:
            sender = EmailRecipient.get_or_create(sender.email)

        if email_template:
            email = cls.objects.create(email_template=email_template,
                                       primary_to=recipient,
                                       sender=sender,
                                       context_data=extra_context)
            try:
                email.send(extra_context=extra_context)
            except Exception as e:
                LOG.error('\nCannot send email, %s, %e', email.id, e)
        else:
            LOG.error('\nCannot find %s for user: %s', email_type, user.email)

    def send(self, extra_context=None):
        if extra_context is None:
            extra_context = self.get_context_data()

        domain_context = get_domain_context()
        extra_context.update(domain_context)
        extra_context['user'] = self.primary_to.user
        if self.sender:
            extra_context['sender'] = self.sender.user

        if not self.email_template:
            # Get the latest template
            email_template = EmailTemplate.get_email_template(self.email_template.email_type)
        else:
            email_template = self.email_template

        try:
            email_data = email_template.render(extra_context=extra_context)
            send_mail(email_data['subject'],
                      email_data['text_body'],
                      self.to_recipient,
                      html_body=email_data['html_body'])
        except Exception as e:
            LOG.error('Cannot send email, %s, %e', self.id, e)
        else:
            if email_template != self.email_template:
                self.email_template = email_template

            self.timestamp_sent = timezone.now()
            self.save(update_fields=['timestamp_sent', 'email_template'])

    def resend(self, requester=None, extra_context=None):
        self.resend_requester = requester
        self.timestamp_resend = timezone.now()
        self.save(update_fields=['resend_requester', 'timestamp_resend'])
        self.send(extra_context=extra_context)

