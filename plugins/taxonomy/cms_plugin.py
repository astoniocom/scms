# coding=utf-8
from scms.plugin_base import SCMSPluginBase
from models import Taxonomy, Terms
from forms import TaxonomyForm
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.datastructures import SortedDict

class TaxonomyPlugin(SCMSPluginBase):
    form = TaxonomyForm
    model = Taxonomy

    def __init__(self, 
                 name, 
                 vocabulary = None,
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
                 multiple=True,
                 filter_type = None,
                 show_weight = False,
                 any_filter_name = 'любой',):
        self.vocabulary = vocabulary and vocabulary or name
        self.multiple = multiple
        self.any_filter_name = any_filter_name
        super(TaxonomyPlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, filter_type, show_weight)

    def get_filters(self, page, lang, request):
        if self.filter_type:
            get = dict(request.REQUEST.items())
            
            getvar = 'taxonomy__terms__and___%s' % self.name
            
            if self.lang_depended:
                terms = Terms.objects.filter(language=lang, vocabulary=self.vocabulary)
            else:
                 terms = Terms.objects.filter(vocabulary=self.vocabulary)
            
            current_values = get.has_key(getvar) and get[getvar] or ''
            group_tids = [term.id for term in terms]
            actived_tids = [str(t) for t in group_tids if str(t) in [str(tid) for tid in current_values.split(',')]]
            
            chlist = SortedDict()
            chlist[0] = {
                'name': self.any_filter_name,
                'var':  getvar,
                'value': '',
                'active': not bool(actived_tids),
            }
            
            for term in terms:
                chlist[term.id] = {
                    'name': term.name, 
                    'var':  getvar,
                    'value': term.id,
                    'description': term.description,
                    'active': str(term.id) in actived_tids,
                }
            return {'type': 'taxonomy', 'name':getvar, 'id':self.name, 'title': self.verbose_name, 'choises': chlist.values()}
        else:
            return None
        
    def get_context(self, page, language):
        """
        Добавляет переменные в контекст отображения
        """
        results = SortedDict()
        try:
            values = self.model.objects.filter(page=page, language=language, field_name=self.name).select_related()
            key = 0 
            for value in values:
                results[key] = {}
                results[key]['terms'] =  value.terms.get_query_set()
                key = key+1
        except self.model.DoesNotExist:
            pass
        
        return results
