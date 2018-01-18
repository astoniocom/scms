# coding=utf-8
from django import forms
from scms.models import Page, Slugs, page_state 
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.forms.utils import ErrorList
from django.forms.models import ModelChoiceField
from django.core.exceptions import ValidationError 
import scms
from django.utils.translation import get_language
import settings

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata, re
    # value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = str(re.sub(r'[^\.,\/*\w\s-]', '', value).strip().lower()) #TODO разобраться со звездочкой, пропускает из-за использования в качестве 1го символа алиаса
    SCMS_SLUG = settings.SCMS_SLUG if hasattr(settings, 'SCMS_SLUG') else {}
    pattern = SCMS_SLUG.get('pattern', '[-\s,\.]+')
    change_symbol = SCMS_SLUG.get('change_symbol', '-')
    return re.sub(pattern, change_symbol, value)     

# Смысл в том, что креме полей одели Page на странице редактирования должны быть еще и поля модели Slug    
class PageForm(forms.ModelForm):
    type = forms.CharField(widget=forms.HiddenInput(), required=True)
    title = forms.CharField(label=_('Title'), widget=forms.TextInput(attrs={'style': "width: 80%;"}), required=True)
    slug = forms.CharField(label=_('Slug'), widget=forms.TextInput(attrs={'style': "width: 80%;"}), help_text=_('The part of the title that is used in the URL'), required=False)
    alias = forms.CharField(label=_('Alias'), widget=forms.TextInput(attrs={'style': "width: 80%;"}), required=False)
            
    class Meta:
        model = Page
        exclude = ['weight', ] # 'title', 'slug', 'alias', 'title', 'slug', 'alias' завязано на options.get_form."if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude" чтобы потом modelform_factory не выдало ошибки о несуществующих полях в моделе.
        
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        language = kwargs.pop('language', None)
        
        super(PageForm, self).__init__(*args, **kwargs)
        
        self.language = language and language or get_language()

        self.slug = Slugs()    
        if instance:
            try:
                self.slug = Slugs.objects.get(page=self.instance, language=self.language)
                self.fields['slug'].initial = self.slug.slug
                self.fields['alias'].initial = self.slug.alias
                self.fields['title'].initial = self.slug.title
            except Slugs.MultipleObjectsReturned:
                slugs = Slugs.objects.filter(page=self.instance, language=self.language)
                self.slug = slugs[0]
                # for i in range(1, len(slugs)):
                #     slugs[i].delete()
                self.fields['slug'].initial = self.slug.slug
                self.fields['alias'].initial = self.slug.alias
                self.fields['title'].initial = self.slug.title
            except Slugs.DoesNotExist:
                pass
        else:
            self.slug = Slugs()
    
    def clean(self):
        if 'modifed' in self._errors:
            del self._errors['modifed'] # т.к. присвоется автоматически при сохранении модели

        # Проверяем поля для которых важна последовательность провеки и проверка которых зависит от других полей
        
        # Проверка недопуск выбора родителя на самого себя
        if 'parent' in self.cleaned_data:    
            if self.cleaned_data['parent']:
                if self.cleaned_data['parent'].id == self.instance.id:
                    self._errors['parent'] = ErrorList([_('A page cannot be parrent for itself')]) # Записываем ошибку
                    del self.cleaned_data['parent'] # Удаляем поле из проверенных данных
                    return self.cleaned_data # Прекращаем проверку, но не через исключение, тк. ошибку уже внесли в списк.
                    # Через исключение не делаем, тк в этом случае не будет подсвечиваться поле в котором была ошибка. (актуально для clean)
        
        # Проверка на выбор недопустимого родителя (на основании связи типов страниц)
        if 'parent' in self.changed_data: # Проверяем корректность родителя, только если он был изменен
            parent_type = 'root'
            if self.cleaned_data['parent']:
                parent_type = self.cleaned_data['parent'].type
            parent_content_type = scms.site.get_content_type(parent_type)
            if self.cleaned_data['type'] not in parent_content_type.children:
                self._errors['parent'] = ErrorList([_('The selected page cannot be parent')])
                del self.cleaned_data['parent']
                return self.cleaned_data
        
        # Проверка на повторяемость поля Slug в одном уровне иерархии
        if 'slug' in self.cleaned_data:
            slug = slugify(self.cleaned_data['slug']) 
            if slug and 'parent' in self.cleaned_data: # Тк не имеет смысла проверять слуг, если родитель не прошел проверку.   
                parent = self.cleaned_data['parent']
                slugs_qs = Slugs.objects.filter(slug=slug, language=self.language, page__parent=parent).exclude(page=self.instance)
                #e=slug
                #d=1/0
                if slugs_qs.count():
                    self._errors['slug'] = ErrorList([_('Another page with this slug already exists')])
                    del self.cleaned_data['slug']
                    return self.cleaned_data
           
        return self.cleaned_data

    def clean_alias(self):
        # Проверка на уникальность алиасов
        # TODO: Добавить также анализ с учетеом '*' в начале и без
        alias = slugify(self.cleaned_data['alias'])
        aliases_qs = Slugs.objects.filter(alias=alias, language=self.language).exclude(page=self.instance)
        if aliases_qs.count():
            raise forms.ValidationError(_('Another page with this alias already exists'))
        return alias
            
    def clean_type(self):
        if not scms.site.get_content_type( self.cleaned_data['type']):
            raise forms.ValidationError(_('Incorrect page type'))
        return self.cleaned_data['type']
    
    def save(self, commit=True):
        obj = super(PageForm, self).save(commit)
        
        if commit and ('title' in self.cleaned_data and 'slug' in self.cleaned_data and 'alias' in self.cleaned_data): # тк полей может не быть, если траница настроек
            self.slug.page = obj
            self.slug.language = self.language
            self.slug.title = self.cleaned_data['title']
            self.slug.slug = self.cleaned_data['slug']
            self.slug.alias = self.cleaned_data['alias']
            self.slug.save()
        
        return obj

        
    