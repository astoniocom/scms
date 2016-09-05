from scms.plugin_base import SCMSPluginBase
from models import Parameters, Colors

class ParametersPlugin(SCMSPluginBase):
    model = Parameters
    template = 'admin/scms/page/edit_inline/tabular.html'

class ColorPlugin(SCMSPluginBase):
    model = Colors
    template = 'admin/scms/page/edit_inline/tabular.html'