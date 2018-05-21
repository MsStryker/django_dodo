from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django.core.cache import cache
from django.conf.urls import url
from django.http import HttpResponse, JsonResponse
from django.contrib.admin import register
from django.shortcuts import render_to_response
from django.template import RequestContext

import pytz

from .models import (EmailTemplate, EmailWidget, EmailContentItem,
                     EmailButton, EmailTheme, UserEmail, EmailStats)
from .forms import EmailWidgetFormSet, EmailWidgetForm


class EmailModelAdmin(admin.ModelAdmin):
    readonly_fields = ('created_by', 'created_at', 'last_edited_by', 'last_edited_at')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.uuid

        obj.last_edited_by = request.user.uuid
        obj.save()


@register(EmailButton)
class EmailButtonAdmin(admin.ModelAdmin):
    list_display = ('description', 'text', 'url_link', 'theme')
    search_fields = ('description', 'text', 'url_link', 'theme_description')


@register(EmailTheme)
class EmailThemeAdmin(EmailModelAdmin):
    list_display = ('description', 'background_color', 'color', 'created_by', 'created_at')


class EmailContentItemInline(admin.TabularInline):
    model = EmailContentItem
    can_delete = True
    extra = 0
    min_num = 3
    verbose_name = 'Email Widget'
    verbose_name_plural = 'Email Widgets'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.uuid

        obj.last_edited_by = request.user.uuid
        obj.save()


class EmailWidgetInline(admin.StackedInline):
    model = EmailWidget
    form = EmailWidgetForm
    formset = EmailWidgetFormSet

    fields = (
        'order',
        ('widget_type', 'direction_ltr'),
        ('image', 'image_alt_text', 'alt_text_size'),
        ('font_family', 'bg_color'),
        ('header_color', 'header_size', 'header_line_height'),
        'header',
        ('font_color', 'font_size', 'font_line_height'),
        'body',
        'button'
    )


@register(EmailWidget)
class EmailWidgetAdmin(EmailModelAdmin):
    save_as = True
    list_display = ('description', 'widget_type', 'header', 'body')
    list_filter = ('widget_type',)
    fields = (
        'description',
        ('widget_type', 'direction_ltr', 'theme'),
        ('image', 'image_alt_text', 'alt_text_size'),
        'header_theme',
        'header',
        'body_theme',
        'body',
        'button'
    )


@register(EmailTemplate)
class EmailTemplateAdmin(EmailModelAdmin):
    list_display = ('email_type', 'subject', 'default_template', 'release', 'created_at', 'created_by')
    change_form_template = 'admin/django_dodo/email_template_change_form.html'

    fields = (
        'base_template',
        ('email_type', 'release', 'default_template'),
        'base_theme',
        'subject', 'title', 'pre_header',
        ('created_by', 'created_at'),
        ('last_edited_by', 'last_edited_at'),
        'widgets'
    )

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        urlpatterns = super(EmailTemplateAdmin, self).get_urls()

        extra_patterns = [
            url(r'^preview/$', self.admin_site.admin_view(self.preview_view), name='%s_%s_preview' % info),
        ]
        return extra_patterns + urlpatterns

    def preview_view(self, request):
        if request.method == 'POST':
            obj = None
            object_id = request.GET.get('object_id', None)
            if object_id:
                obj = self.model.objects.get(pk=object_id)

            ModelForm = self.get_form(request, obj)
            form = ModelForm(request.POST, request.FILES)
            instance = form.save(commit=False)

            widgets_list = form.data['widgets'].split(',')
            widgets = []
            for widget in widgets_list:
                widgets.append(EmailWidget.objects.get(pk=widget))

            context = {'email_template': instance, 'widgets': widgets}
            # rendered_email = instance.render_preview(settings.PREVIEW_EMAIL, context=context)
            rendered_email = instance.render_preview(context=context)
            return JsonResponse(rendered_email)

        return HttpResponse('Unable to process.', content_type='text/plain')


def resend_email(modeladmin, request, queryset):
    for obj in queryset:
        obj.resend(request.user.uuid)


@register(UserEmail)
class UserEmailAdmin(admin.ModelAdmin):
    list_display = ('primary_to', 'timestamp', 'timestamp_sent', 'bounced', 'timestamp_resend')
    actions = [resend_email]

    def has_add_permission(self, request):
        return False


@register(EmailStats)
class EmailStatsAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'delivery_attempts', 'bounces', 'complaints', 'rejects')
    change_list_template = 'services/send_stats.html'

    # def get_urls(self):
    #     extra_urls = [
    #         url(r'^ses/(?P<pk>[-\w]+)/$', self.admin_site.admin_view(self.ses_dashboard), name='ses-stats'),
    #     ]
    #     return extra_urls + super(StatsAdmin, self).get_urls()

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        Graph SES send statistics over time.
        """
        template = self.change_list_template
        # cache_key = 'vhash:ses_stats'
        cache_key = 'django_dodo:ses_stats'
        cached_view = cache.get(cache_key)
        if cached_view:
            return cached_view

        self.model.update_send_stats()

        send_stats = self.model.get_send_stats()

        extra_context = {
            'title': 'SES Statistics',
            'data_points': send_stats,
            # '24hour_quota': quota['Max24HourSend'],
            # '24hour_sent': quota['SentLast24Hours'],
            # '24hour_remaining': float(quota['Max24HourSend']) - float(quota['SentLast24Hours']),
            # 'per_second_rate': quota['MaxSendRate'],
            # 'verified_emails': verified_emails,
            # 'summary': summary,
            # 'access_key': connection.gs_access_key_id,
            'local_time': True if pytz else False,
        }

        response = render_to_response(template, extra_context, context_instance=RequestContext(request))

        cache.set(cache_key, response, 60 * 15)  # Cache for 15 minutes
        return response
