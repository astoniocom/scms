# coding=utf-8
from django.forms.models import ModelForm, BaseInlineFormSet
from django.contrib.admin.options import InlineModelAdmin
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from scms.utils import get_language_from_request
from collections import OrderedDict

class SCMSPluginBase(InlineModelAdmin):
    fk_name = 'page'
    exclude = None
    
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
                 show_weight = False, *args, **kwargs):

        if form:
            self.form = form
        else:
            if not self.form:
                self.form = ModelForm
            
        if formset:
            self.formset = formset
        else:
            if not self.formset:
                self.formset = BaseInlineFormSet
        
        if template:
            self.template = template
        else:
            if not self.template:
                self.template = 'admin/scms/page/edit_inline/simple.html'

        self.name = name
        
        if verbose_name is None:
            self.verbose_name = self.name
        else:
            self.verbose_name = verbose_name
        if verbose_name_plural is None:
            self.verbose_name_plural = self.verbose_name
        else:
            self.verbose_name_plural = verbose_name_plural
            
        self.extra = extra
        self.lang_depended = lang_depended
        self.can_order = can_order
        self.can_delete = can_delete
        self.max_num = max_num
        
        self.filter_type = filter_type
        self.show_weight = show_weight
        
        if show_weight:
            pass
        else:
            self.exclude = self.exclude and self.exclude+['weight'] or ['weight']

        self.placeholder = kwargs.get("placeholder", "")
        self.help_text = kwargs.get("help_text", "")

    def get_plugin_formset(self, request, obj=None, instance=None, **kwargs):
        # import debug
        # defaults = {
        #     'auto_id': self.auto_id,
        #     'prefix': self.add_prefix(i),
        #     'error_class': self.error_class,
        #     # Don't render the HTML 'required' attribute as it may cause
        #     # incorrect validation for extra, optional, and deleted
        #     # forms in the formset.
        #     'use_required_attribute': False,
        # }
        # defaults.update(kwargs)
        
        FormSet = self.get_formset(request, obj, **kwargs)
        language = self.lang_depended and get_language_from_request(request, None) or ''
        FormSet._queryset = self.model.objects.filter(language=language, page=instance, field_name=self.name).order_by('weight') # Фильтр на каком основании брать данные для полей плагина
        FormSet.form.page = instance # возможно, эти три строки неактуальны тк в пагеадмин есть request.change_page = obj obj? с целью, чтобы формы плагинов имели данные о странице
        FormSet.form.language = language
        FormSet.form.admin_field = self
        
        if request.POST:
            formset = FormSet(request.POST, request.FILES, instance=instance, prefix=self.name)
            
            # Можно было бы вынести и в общий блок (за пределы условия), но этот код вызывается только когда происходит save_formset. А это на данный момент только при POST-запросе
            for next_form in formset.extra_forms:
                for field in next_form.instance._meta.fields:
                    if field.name == 'language':
                        field.save_form_data(next_form.instance, language)
                    if field.name == 'field_name':
                        field.save_form_data(next_form.instance, self.name)
        else:
            formset = FormSet(instance=instance, prefix=self.name)
        
        # Добавим help_text, если он указан в плагине
        formset.help_text = self.help_text
        return formset
      
    def init(self, parent_model, admin_site):
        super(SCMSPluginBase, self).__init__(parent_model, admin_site)
        
    def will_delete(self, parent_object):
        """
        Вызывается перед удалением родительского объекта.
        """
        pass
    
    def get_context(self, page, language):
        """
        Добавляет переменные в контекст отображения
        """

        results = OrderedDict()
        try:
            values = self.model.objects.filter(page=page, language=language, field_name=self.name).order_by('weight')#.select_related() #t
            key = 0
            for value in values:
                results[key] = {}
                for sub_field in iter(value._meta.fields):
                    val = getattr(value, sub_field.name, None)
                    
                    if not val is None:
                        val = isinstance(val, str) and mark_safe(val) or val 
                    else:
                        val = ""

                    if not sub_field.choices:
                        results[key][sub_field.name] =  val
                    else:
                        cval = getattr(value, "get_%s_display" % sub_field.name)
                        cval = cval()
                        cval = not cval is None and cval or ""
                        results[key][sub_field.name] =  cval
                        results[key]["%s_id" % sub_field.name] =  val
                    #w=1/0
                key = key+1
        except self.model.DoesNotExist:
            pass
        return results
    
    def modify_page(self, page, request=None, language=None):
        pass
    
    def get_inline_instances(self, obj=None):
        """
        Используется при получении контекста полей. Просто иногда необходимо,
        чтобы плагин формировал не 1 поле, а несколько
        """
        return [self]
    
    
    def get_filters(self, page, lang, request):
        return None

