# coding=utf-8
# Проверка на одинакоые заголовки в таксономии
# Регистрация пользователей в системе -- добавить
# Модуль file возвращает при загрузке страницы относительный путь от медиа
# Пагинатор не удобно настраивать
# Решить по другому.Добавить механизм, чтобы, если страницы нет на основном языке, на всех остальных языках ее содавать тоже нельзя. Иначе, нечего отображать в поле title
# Проверка алиасов при сохранении/изменении страницы на совпадение с url.py. Если совпадает, не разрешать сохранять алиас. (files раздел и папка)
from scms.admin.forms import PageForm
from django.contrib import admin
from scms.models import Page, Slugs, page_state, MongoManager
from functools import update_wrapper
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.admin import helpers
from django.utils.functional import curry
from django.forms.models import modelform_factory
from scms.utils import get_language_from_request, get_query_string
from django.conf import settings
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.forms.formsets import all_valid
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.utils.html import escape
from scms.utils.i18n import get_default_language
from django.forms.utils import ErrorList
from django.utils.http import urlquote
from scms.utils import get_destination
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.db.models import Q
import scms
from scms.admin.widgets import CMSForeignKeyRawIdWidget
from urlparse import urljoin
from django.contrib.admin.utils import flatten_fieldsets
from scms.admin import actions
from django.contrib.admin.utils import lookup_field, display_for_field
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import get_language
from django.utils.encoding import force_text
from django.contrib.auth.models import User
from scms.admin.actions import copy_page

IS_POPUP_VAR = '_popup'

csrf_protect_m = method_decorator(csrf_protect)
class PageAdmin(admin.ModelAdmin):
    slug_model = Slugs
    save_as = True
    # save_as = False # !!!
    actions = [actions.delete_selected, actions.copy_selected]
    form = PageForm
    declared_fieldsets = []

    def copy_page(self, obj):
        return copy_page(obj)
    
    def get_urls(self):
        from django.conf.urls import patterns, url
        
        def wrap(view):
            def wrapper(request, *args, **kwargs):
                request.scms = {
                    'page': None, # Текущая страница
                    'page_type': None, #тип отображаемой/редактируемой страницы
                }
                return self.admin_site.admin_view(view)(request, *args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name

        urlpatterns = [
            url(r'^$', wrap(self.changelist_view), name='%s_%s_changelist' % info),
            url(r'^add/$', wrap(self.add_view), name='%s_%s_add' % info),  
            url(r'^(.+)/history/$', wrap(self.history_view), name='%s_%s_history' % info),
            url(r'^(.+)/delete/$', wrap(self.delete_view), name='%s_%s_delete' % info),
            url(r'^(.+)/$', wrap(self.change_view), name='%s_%s_change' % info),
        ]
        # Add in each model's views.
        #for key, obj in scms.site.get_content_type().iteritems():
        #    urlpatterns += patterns('',
        #        url(r'^add/(%s)$' % obj.id, wrap(self.add_view), name='%s_%s_add' % info) #name='add_%s_content' % obj.id)
        #    )
        return urlpatterns
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'parent':
            kwargs['widget'] = CMSForeignKeyRawIdWidget(request.scms['page_type'], db_field.rel,  self.admin_site)
        return super(PageAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        # import debug
        if obj and obj.state == page_state.SETTINGS:
            if request.user.is_superuser:
                self.fieldsets = ([_('Additional'), {'classes': ('collapse',), 'fields': ('title', 'authors', 'state', 'type')}],)
            else:
                self.fieldsets = ([_('Additional'), {'classes': ('collapse',), 'fields': ('title', 'authors', 'type'         )}],)
        else:    
            if request.user.is_superuser:
                self.fieldsets = ([None, {'fields': ('parent', 'title', 'slug')}], [_('Advanced options'), {'classes': ['collapse'], 'fields': (('published', 'hidden', 'expanded', 'state'), 'date', 'alias', 'authors', 'type'), }])
            else:
                self.fieldsets = ([None, {'fields': ('parent', 'title', 'slug')}], [_('Advanced options'), {'classes': ['collapse'], 'fields': (('published', 'hidden', 'expanded',        ), 'date', 'alias', 'authors', 'type'), }])                
            
        
        form = super(PageAdmin, self).get_form(request, obj, **kwargs)
        qs = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
        form.base_fields['authors'].initial = [request.user.id,] # Так, конечно не правильно, но другого способа назначить авторов по простому не нашел, возможно в будущих версиях переделают add_view
        form.base_fields['authors'].queryset = qs
        if qs:
            for u in qs:
               form.base_fields['authors'].initial.append(u.pk) 
        
        return form
        
    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        parent_id = None
        try:    
            parent_id = int(request.GET.get('parent'))
            request.scms['page'] = self.model.objects.get(id=parent_id)
        except (ValueError, TypeError, self.model.DoesNotExist):
            request.scms['page'] = self.model(id=None).full_load()

        request.scms['page_type'] = request.GET.get('type', '__undefined__') # произвольное редкое имя, чтобы сл. функция вернула ложь

        parent_content_type = scms.site.get_content_type(request.scms['page'].type)
        if not request.user.is_superuser and not request.scms['page_type']  in parent_content_type.children:
            raise Http404()
        
        request.scms['has_add_permission'] = True
                
        extra_context = self.update_language_tab_context(request, None, extra_context)
        extra_context['destination'] = request.GET.get('destination', None)
        extra_context['breadcrumbs'] = self.model(id=parent_id).full_load().parents
        
        return super(PageAdmin, self).add_view(request, form_url, extra_context)

    @csrf_protect_m
    @transaction.atomic
    def change_view(self, request, object_id, form_url='', extra_context=None):
        # import debug
        tab_language = get_language_from_request(request, None)
                                   
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))
            

        if not self.has_change_permission(request, obj):
            messages.warning(request, _("You have no permissions to change %(name)s") % {"name": obj})
            if request.GET.get('destination'):
                dest_url = self.parse_destination(request, obj)
            else:
                dest_url = reverse('admin:%s_%s_changelist' % (opts.app_label, opts.model_name),  current_app=self.admin_site.name)
            return HttpResponseRedirect(dest_url)
        
        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_text(opts.verbose_name), 'key': escape(object_id)})

        request.scms['page_type'] = obj.type
        request.scms['page'] = obj
        #if request.method == 'POST' and "_saveasnew" in request.POST:
            #raise PermissionDenied
            # Не реализовано
            #if not request.user.is_superuser and 'create' in scms.site.get_content_type(obj.type).permissions:
            #    return self.add_view(request, form_url='../add/%s' %  obj.type, current_app=self.admin_site.name)
            #else:
            #    raise PermissionDenied

        ModelForm = self.get_form(request, obj)
        formsets = []
        inline_instances = scms.site.get_content_type(obj.type).get_fields(obj)
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj, language=tab_language)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
                 # Возвращается просто объект страницы, но запись в БД еще не происходила
                 # тк еще надо проверь корректность inline ов
            else:
                form_validated = False
                new_object = obj
            
            for inline in inline_instances:
                inline.init(self.model, self.admin_site)
                formset = inline.get_plugin_formset(request, obj, instance=new_object)
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                if "_saveasnew" in request.POST:
                    new_object = self.copy_page(new_object)

                self.save_related(request, form, formsets, True)
                self.save_model(request, new_object, form, True)
                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                response = self.response_change(request, new_object) # стандартный обработчик
                if tab_language and response.status_code == 302 and response._headers['location'][1] == request.path :
                    location = response._headers['location']
                    response._headers['location'] = (location[0], "%s?language=%s" % (location[1], tab_language))
                return response

        else:
            form = ModelForm(instance=obj, language=tab_language)
            
            for inline in inline_instances:
                inline.init(self.model, self.admin_site)
                formset = inline.get_plugin_formset(request, None, instance=obj)
                formsets.append(formset)

        fieldsets = self.get_fieldsets(request, obj) 
                
        adminForm = helpers.AdminForm(form, fieldsets,
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            prepopulated = dict(inline.get_prepopulated_fields(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
        
        fullobj = form.instance.full_load(language=tab_language)
        
        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name), #TODO: указывать тип создаваемой страницы
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.GET or "_popup" in request.POST,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
            #TODO!!!'root_path': self.admin_site.root_path,
            'view_path': fullobj and fullobj.link or None ,
            'destination': self.parse_destination(request, obj),
            'has_permission': True,
            'breadcrumbs': self.model(id=obj.parent_id).full_load().parents + [obj.full_load()],
        }

        context = self.update_language_tab_context(request, None, context)
        context.update(extra_context or {})

        return self.render_change_form(request, context, change=True, obj=obj, form_url=form_url)
    
    @csrf_protect_m    
    def changelist_view(self, request, extra_context=None):
        self._request = request
        extra_context = extra_context or {}

        parent_id = None
        try:
            parent_id = int(request.GET.get('parent__id__exact'))
            request.scms['page'] = self.model.objects.get(id=parent_id)
        except (ValueError, TypeError, self.model.DoesNotExist):
            request.scms['page'] = self.model(id=None).full_load()
        request.scms['page_type'] = request.scms['page'].type
        parent = self.model(id=parent_id).full_load()
        try:        
            extra_context.update({
                'parent_id': parent_id,
                'destination': get_destination(request),
                'breadcrumbs': self.model(id=parent_id).full_load().parents,
                'opts': self.model._meta, # для темплэйта breadcrumbs.html
            })
        except:
            pass
            # import debug
        parent = self.model(id=parent_id).full_load()

        parent_content_type = scms.site.get_content_type(request.scms['page_type'])

        # Подготавливаем ячейки просмотра/редактирования от плагинов
        admin_list_ext = [] # Ниже вставляется в self.list_display
        for plugin_field_info in parent_content_type.get_changelist_fields(True):
            if isinstance(plugin_field_info, dict):
                list_name = plugin_field_info['list_name']
                def ext_field_view(obj):
                    val = getattr(obj, list_name, '')
                    return val and val or ''
                ext_field_view.allow_tags = True 
                ext_field_view.short_description = plugin_field_info['column_name'] 
                
                setattr(self, plugin_field_info['list_name'], ext_field_view)
                admin_list_ext += [plugin_field_info['list_name']] # в self.list_display должна быть строка, поэтому сохраняем только имя поля(функции-обработчика)
            else:
                admin_list_ext += [plugin_field_info]

        if not '_popup' in  request.GET:
            # 'action_checkbox', убрал из следующей строчки первым пунктом, т.к. у нас не испльзуются действия, см. также. объявление класса 
            self.list_display = ['adminlist_icon', 'adminlist_title', 'adminlist_state'] + admin_list_ext + ['adminlist_actions'] # В функцию вынесено с целью упрощенного переопределения
            self.list_editable = [field for field in ['weight', 'date', 'published', 'hidden', 'expanded'] if field in self.list_display]  
        else:
            # 'action_checkbox', убрал из следующей строчки первым пунктом, т.к. у нас не испльзуются действия, см. также. объявление класса
            self.list_display = ['adminlist_empty', 'adminlist_icon', 'adminlist_title', 'type', 'adminlist_actions',] # В функцию вынесено с целью упрощенного переопределения
            self.list_editable = []

        # Формирование списка ссылок для добавления новых страниц
        add_list = []
        for children_name in parent_content_type.children:
            next_content_type = scms.site.get_content_type(children_name)
            if not self.has_add_permission(request, parent_page=request.scms['page'], type=children_name):
                continue
            add_list.append(next_content_type)
        extra_context.update({'add_list': add_list})

        return super(PageAdmin, self).changelist_view(request, extra_context)

    def get_changelist_form(self, request, **kwargs):
        class ChangelistModelForm(ModelForm):
            plugin_fields = scms.site.get_content_type(request.scms['page_type']).get_changelist_fields()
            formfield_for_dbfield = self.formfield_for_dbfield
    
            class Meta:
                fields = "__all__"

            def __init__(self, instance=None, **kwargs ):
                super(ChangelistModelForm, self).__init__(instance=instance, **kwargs)
                if instance: # instance == None, когда нет потомков для отображения
                    for plugin_field_info in self.plugin_fields:
                        for field in scms.site.get_content_type(instance.type).get_fields():
                            if field == plugin_field_info['field'] and plugin_field_info['editable']:
                                self.fields[plugin_field_info['list_name']] = self.formfield_for_dbfield(db_field=plugin_field_info['field'].model._meta.get_field_by_name(plugin_field_info['db_field'])[0], request=request)
                                val = getattr(instance, plugin_field_info['list_name'], None)
                                if val:
                                    self.initial[plugin_field_info['list_name']] = val

            def save(self, commit=True):
                obj = super(ChangelistModelForm, self).save(commit)
                for plugin_field_info in self.plugin_fields:
                    if plugin_field_info['list_name'] in self.changed_data:
                        record = {}
                        record['page'] = obj
                        record['language'] = plugin_field_info['field'].lang_depended and get_default_language() or ''
                        record['field_name'] = plugin_field_info['field'].name
                        
                        # Получаем объект редактируемого параметра
                        field_obj = plugin_field_info['field'].model.objects.filter(**record)[plugin_field_info['pos']:plugin_field_info['pos']+1]
                        
                        if field_obj:
                            field_obj = field_obj[0]
                        else:
                            field_obj = plugin_field_info['field'].model(**record)
                        # Записываем новое значение этого параметра
                        setattr(field_obj, plugin_field_info['db_field'], self.cleaned_data[plugin_field_info['list_name']])
                        if commit:
                            field_obj.save()
                        
                return obj
        defaults = {
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
        }
        defaults.update(kwargs)
        return modelform_factory(self.model, form=ChangelistModelForm, **defaults)
    
    def get_changelist(self, request, **kwargs):
        from scms.admin.views.main import SCMSChangeList
        return SCMSChangeList    
    
    @csrf_protect_m
    @transaction.atomic
    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        
        extra_context = {
            'breadcrumbs': self.model(id=obj.parent_id).full_load().parents + [obj.full_load()],
        }
        to_return = super(PageAdmin, self).delete_view(request, object_id, extra_context)
        if isinstance(to_return, HttpResponseRedirect) and 'destination' in request.GET:
            return HttpResponseRedirect(self.parse_destination(request))
        return to_return   
    
    def save_model(self, request, obj, form, change):
        # import debug
        form.save()
        
    def has_add_permission(self, request, parent_page=None, type=None):
        if not parent_page or not type:
            if hasattr(request, 'scms') and request.scms.get('has_add_permission'): # Вот такой вот костыль. Чтобы из add_view первый раз всегда было труе, а так изели типц не указаны -- фолс
                request.scms.pop('has_add_permission')
                return True
            else:
                return False
        
        #Если долго не пригодиться -- удалить
        #if not hasattr(request, 'scms') and (not parent_page or not type): # На случай проверки из вне, например, с главной страницы django_admin
        #    return False
        #parent_page = parent_page and parent_page or request.scms['page']
        #check_type = type and type or request.scms['page_type']        

        parent_content_type = scms.site.get_content_type(parent_page.type)
        if not request.user.is_superuser and not type in parent_content_type.children: # суперпользователь может добавлять любой тип, не смотря на ограничения, правда, этот тип не отображается в списках добавления.
            return False
                
        if not request.user.is_superuser:
            try:
                perm_obj = parent_page.type != 'root' and parent_page or self.model.objects.filter(state=page_state.SETTINGS)[0]
            except:
                return True # если нет настроек, тогда, разрешаем добавлять всё
            if not perm_obj.get_ancestors().filter(authors=request.user.id) and request.user not in perm_obj.authors.get_queryset():
                return False
        
        return super(PageAdmin, self).has_add_permission(request)
        
    def has_change_permission(self, request, obj=None):
        if obj:
            if not request.user.is_superuser:
                if not obj.get_ancestors(include_self=True).filter(authors=request.user.id):
                    return False
        
        return super(PageAdmin, self).has_change_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        if obj:
            protacted_states = [page_state.LOCK_DELETION, page_state.MAIN, page_state.SETTINGS]
            if isinstance(obj, (Page, Slugs)):
                if (not obj.get_ancestors().filter(authors=request.user.id) and not request.user.is_superuser) or \
                   (obj.get_children().filter(state__in=protacted_states) or obj.state in protacted_states):
                   # request.user not in obj.authors.get_queryset() and
                    return False  
            elif isinstance(obj, (MongoManager)):
                if not request.user.id in obj.authors or not request.user.is_superuser:# or \
                   # (obj.get_children().filter(state__in=protacted_states) or obj.state in protacted_states):
                    return False  
            
        return super(PageAdmin, self).has_delete_permission(request, obj)
     
    def update_language_tab_context(self, request, obj=None, context=None):
        """
        Функция обновления контекста шаблона на основании языковых настроек.
        """
        if not context:
            context = {}
        language = get_language_from_request(request, obj)
        context.update({
            'langgetvars': get_query_string(request.GET, remove=['language'], addq=False),
            'language': language,
            'traduction_language': settings.SCMS_LANGUAGES,
            'show_language_tabs': len(settings.SCMS_LANGUAGES) > 1,
        })
        return context

    def parse_destination(self, request, obj=None):
        """
        Анализирует GET['destination'] и формирует путь по которому необходимо перейти
        """
        destination = request.GET.get('destination', '../') 
        if destination == 'alias':
            edit_lang = get_language_from_request(request)
            if obj.state == page_state.MAIN:
                destination = "/"
            else:
                try:
                    destination = self.slug_model.objects.get(page=obj, language=edit_lang).alias.replace('*', '')
                except self.slug_model.DoesNotExist: # на случай если destination == alias, а записи в слугс нет
                    return "/"
            if not edit_lang == get_default_language() and  not edit_lang == get_language(): # для того, чтобы при возврате на 'alias' страница отображалась не на языке по-умолчанию, а на редактируемом
                destination = '/%s%s' % (edit_lang, destination)
        
                
        return destination

    def response_add(self, request, obj, post_url_continue='../%s/'):
        result = super(PageAdmin, self).response_add(request, obj, post_url_continue)
        
        if "_continue" in request.POST:
            return HttpResponseRedirect(post_url_continue % obj._get_pk_val() + get_query_string(request.GET, remove=['type', 'parent'], addq=True))
        
        if "_addanother" in request.POST:
            return HttpResponseRedirect(request.path + get_query_string(request.GET, addq=True))
        
        if request.GET.get('destination'):
            dest_url = self.parse_destination(request, obj)
            return HttpResponseRedirect(dest_url)
                
        return result
        
    def response_change(self, request, obj):
        result = super(PageAdmin, self).response_change(request, obj)
            
        if "_continue" in request.POST:
            if IS_POPUP_VAR in request.POST:
                return HttpResponseRedirect(request.path + get_query_string(request.GET, new_params={'_popup': 1}, addq=True))
            else:
                return HttpResponseRedirect(request.path + get_query_string(request.GET, addq=True))
        elif "_saveasnew" in request.POST:
            pass # не реализовано
        elif "_addanother" in request.POST:
            return HttpResponseRedirect(result['location'] + '' + get_query_string(request.GET, new_params={'parent': str(obj.parent_id), 'type': obj.type}, remove=['language',], addq=True))
        
        if request.GET.get('destination'):
            dest_url = self.parse_destination(request, obj)
            
            return HttpResponseRedirect(dest_url)
            
        return result

    def adminlist_icon(self, obj):
        content_type = scms.site.get_content_type(obj.type)
        if content_type:
            return '<img src="%s" style="width: 16px; height: 16px; margin: auto; display: block;">' % urljoin(settings.STATIC_URL, content_type.icon)
        else:
            return ''
    adminlist_icon.short_description = ''
    adminlist_icon.allow_tags = True
    
    def adminlist_slug(self, obj):
        return obj.slug and obj.slug or obj.id
    adminlist_slug.short_description = _('Slug')
    
    def adminlist_title(self, obj):
        content_type = scms.site.get_content_type(obj.type) 
        caption = '<strong>%s</strong>' % obj.title   
        if content_type and (content_type.children or obj.nchildren):
            caption = '<a href="%s">%s</a>' % (get_query_string(self._request.GET, new_params={'parent__id__exact': str(obj.id)}, remove=['parent__id__exact'], addq=True), caption)
        return caption

    adminlist_title.short_description = _('Title')
    adminlist_title.allow_tags = True
    
    def adminlist_state(self, obj):
        if obj.state:
            field, attr, value = lookup_field('state', obj, self)
            return display_for_field(value, field, "---")
        else:
            return ''
    adminlist_state.short_description = _('State')
    
    def get_queryset(self, request):
        # import debug
            
        qs = super(PageAdmin, self).get_queryset(request)
        # qs = qs.filter(date__gte=datetime.datetime.now() - datetime.timedelta(hours=1))
        # qs = qs.exclude(state__in=[page_state.SETTINGS, page_state.LOCK_DELETION, page_state.EXTRAHIDDEN])
        # qs = Page().get_pages(request)['object_list']
        # if not request.GET.get('parent__id__exact'):
        #     qs = qs.filter(parent=None)
        return qs       

    def adminlist_actions(self, obj):
        # import debug
        links = [] 
        parent_content_type = scms.site.get_content_type(obj.type)

        destination = '?destination=%s' % get_destination(self._request)
        
        if not '_popup' in self._request.GET:
            view_link = obj.alias and obj.alias or '/'
            # import debug
            links.append('<nobr><a href="%s" title="%s"><img src="%s" style="width: 16px; height: 16px; margin: 0px 4px 0px 4px;">%s</a></nobr>' % (view_link, _('View'), urljoin(settings.STATIC_URL, 'scms/icons/view.png'), _('View')) )
            #if self.has_change_permission(self._request, obj): # не проверяем разрешения, чтобы не создавать нагрузку на БД. в противном случае раскомментировать
            links.append(u'<nobr><a href="%s/%s" title="%s"><img src="%s" style="width: 16px; height: 16px; margin: 0px 4px 0px 4px;">%s</a></nobr>' % (obj.id, destination, _('Edit'), urljoin(settings.STATIC_URL, 'scms/icons/edit.png'), _('Edit')) )
        elif self._request.GET.get('parent_type', '__none_type__') in parent_content_type.children or not self._request.GET.get('parent_type'): # Второе условия на случай необходимости выбора страницы из другой модели/приложения
                links.append( u'<nobr><a href="#" onclick="opener.dismissRelatedLookupPopup(window, %s); return false;" title="%s"><img src="%s" style="width: 16px; height: 16px; margin: 0px 4px 0px 4px;">%s</a>' % (obj.id, _('Select'), urljoin(settings.STATIC_URL, 'scms/icons/choise.png'), _('Select')) )
        # import debug
        return u' '.join(links)
    adminlist_actions.allow_tags = True
    adminlist_actions.short_description = _('Actions')
    
    def adminlist_type(self, obj):
        content_type = scms.site.get_content_type(obj.type)
        if content_type:
            return content_type.name
        else:
            return obj.type
    adminlist_type.short_description = _('Type')

    def adminlist_children(self, obj):
        return obj.nchildren and obj.nchildren or ''
    adminlist_children.short_description = _('Children')


    def adminlist_empty(self, obj):
        return '' # Поле- заглушка. Чтобы в режиме pop число столбцов до иконки не менялось и было как в листвью и иконки (.., /) не прыгали
    adminlist_empty.short_description = ''


admin.site.register(Page, PageAdmin)        
    #def adminlist_weight(self, obj): Раньше был этот блок, но теперь, думаю, не нужен
    #    return '<input type="text" size="3" name="weight[%s]" value="%s">' % (obj.id, obj.weight) 
    #adminlist_weight.short_description = _('Weight')
    #adminlist_weight.allow_tags = True
