from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig

default_app_config = 'scms.plugins.contact_form.ContactPluginConfig'

class ContactPluginConfig(AppConfig):
    name = 'scms.plugins.contact_form'
    verbose_name = _("Contact form")