from scms.models.pluginmodel import SCMSPluginModel
from django.utils.translation import ugettext_lazy as _
from tinymce import models as tinymce_models


class TinyMCE(SCMSPluginModel):
    body = tinymce_models.HTMLField(_("Text"))
