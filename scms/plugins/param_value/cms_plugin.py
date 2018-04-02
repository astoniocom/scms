# coding: utf-8
from scms.plugin_base import SCMSPluginBase
from models import ParamValue

class ParamValuePlugin(SCMSPluginBase):
    model = ParamValue
    template = 'admin/scms/page/edit_inline/tabular.html'