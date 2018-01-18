from scms.plugin_base import SCMSPluginBase
from .models import Links

class LinksPlugin(SCMSPluginBase):
    template = 'admin/scms/page/edit_inline/tabular.html'
    model = Links
	

        