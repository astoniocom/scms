# coding=utf-8
import shutil, os 
from scms.plugin_base import SCMSPluginBase
from .models import File
from .forms import FileForm


class FilePlugin(SCMSPluginBase):
    form = FileForm
    model = File
    template = 'admin/scms/page/edit_inline/tabular.html'
 
    def __init__(self, 
                 name, 
                 verbose_name=None, 
                 verbose_name_plural=None, 
                 form=None, 
                 formset=None, 
                 extra=3, 
                 can_order=False, 
                 lang_depended=True, 
                 can_delete=True, 
                 max_num=1, 
                 template = None,
                 filter_type = None,
                 show_weight = False,
                 description = True,):
        
        if not description:
            self.exclude = ['description',]
        
        super(FilePlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, filter_type, show_weight)
