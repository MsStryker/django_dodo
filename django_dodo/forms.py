from django import forms

from .models import EmailTemplate, EmailWidget, EmailButton


class ButtonForm(forms.ModelForm):

    class Meta:
        model = EmailButton
        fields = ['text', 'description', 'theme', 'url_link']


class EmailWidgetForm(forms.ModelForm):
    order = forms.IntegerField()

    class Meta:
        model = EmailWidget
        fields = '__all__'

    def has_changed(self):
        """
        Returns True if we have initial data.
        """
        has_changed = super(EmailWidgetForm, self).has_changed()
        return bool(self.initial or has_changed)


class BaseEmailWidgetFormSet(forms.BaseModelFormSet):
    """
    Custom formset that support initial data
    """

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 queryset=None, instance=None, **kwargs):
        if instance:
            queryset = instance.widgets.all()
        super(BaseEmailWidgetFormSet, self).__init__(data=data, files=files, auto_id=auto_id, prefix=prefix,
                                                     queryset=queryset, **kwargs)


EmailWidgetFormSet = forms.modelformset_factory(EmailWidget, form=EmailWidgetForm, formset=BaseEmailWidgetFormSet)


class EmailTemplateForm(forms.ModelForm):

    class Meta:
        model = EmailTemplate
        fields = ['email_type', 'subject', 'title', 'pre_header', 'widgets']
