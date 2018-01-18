from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig

default_app_config = 'scms.plugins.taxonomy.TaxonomyPluginConfig'

class TaxonomyPluginConfig(AppConfig):
    name = 'scms.plugins.taxonomy'
    verbose_name = _("Taxonomy")