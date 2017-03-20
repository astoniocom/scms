# coding=utf-8
import datetime, scms, mptt, pickle, cPickle, dill, bson
from pytils import translit
from copy import deepcopy
from datetime import datetime
from bson.binary import Binary
from importlib import import_module
from collections import OrderedDict
from django.db import models
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _
from django.contrib.sitemaps import ping_google
from django.utils.translation import get_language
from django.utils.encoding import force_unicode, smart_str
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from scms.utils.i18n import get_default_language
from scms.utils import get_mongo

class FieldData(dict):
    '''
    Класс для данных из полей
    '''
    def __iter__(self):
        for i in self['values']:
            yield self['values'][i]


    # def __get__(self, attr):
    #     super(FieldData, self).__getitem__(attr)
    #     return self['values'][attr]
    # def __getitem__(self, attr):
    #     # super(FieldData, self).__getitem__(attr)
    #     return self.get(attr)

    # def __getattr__(self, attr):
    #     # import debug
    #     # if 'body' in attr:
    #         # import debug
    #     try:
    #         return self['values'][attr]
    #     except KeyError:
    #         # try:
    #         #     return self[.attr
    #         # except KeyError:
    #         #     pass
    #         return super(FieldData, self).__call__(attr)

    def __unicode__(self, *args, **kwargs):
        var = self.getvalue()
        if isinstance(var, float):
            return "%s" % var
        return var

    # def __call__(self, *args, **kwargs):
        # import debug
        # return self.getvalue()

    def getvalue(self):
        attrs = ['body', 'data', 'link']

        if len(self['values']) > 0:
            for a in attrs:
                if a in self['values'][0]:
                    return self['values'][0][a]
        # if self['type'] == 'FloatPlugin' or self['type'] == 'IntegerPlugin':
        #     return 0
        return ""

class page_state():
    MAIN=1
    LOCK_DELETION=2
    EXTRAHIDDEN=3
    IN_TRASH=4
    SETTINGS=5

if 'smart_cache' in settings.INSTALLED_APPS:
    import smart_cache

def pagecache_make_cid(pid, lang):
    return 'page_%s_%s' % (pid, lang)

def pagecache_delete(pid, lang, objtype):
    # удаляем кеш самого объекта
    cid = pagecache_make_cid(pid, lang)
    cache.delete(cid)
    
    if 'smart_cache' in settings.INSTALLED_APPS:
        smart_cache.delete('scms_type', objtype)
        smart_cache.delete('scms_object', cid)
    

class Page(models.Model):
    state_choises = (
        (page_state.MAIN, _('Main page')), 
        (page_state.LOCK_DELETION, _('Lock deletion')), 
        (page_state.EXTRAHIDDEN, _('Extrahidden')), 
        (page_state.IN_TRASH, _('In the trash')), 
        (page_state.SETTINGS, _('Settings page'))
    )
    
    parent = models.ForeignKey('self', verbose_name=_('Parent'), null=True, blank=True, related_name='children', db_index=True, default=None)
    type   = models.CharField(_("Type"), max_length=16, blank=False, db_index=True)
    weight = models.IntegerField(_("Weight"), blank=False, db_index=True, default=0)
    published = models.BooleanField(_("Published"), default=True, blank=False, db_index=True)
    hidden = models.BooleanField(_("Hidden"), default=False, blank=False, db_index=True)
    expanded = models.BooleanField(_("Expanded"), default=False, blank=False, db_index=True)
    state = models.IntegerField(_("State"), blank=True, null=True, db_index=True, choices=state_choises)
    date = models.DateTimeField(_("Date"), default=datetime.now)
    modifed = models.DateTimeField(_("Modifed"), blank=True)
    authors = models.ManyToManyField(User, verbose_name=_("Authors"), blank=True)
    
    class Meta:
        app_label = 'scms'
        verbose_name = _('page')
        verbose_name_plural = _('pages')
        ordering = ('weight', 'tree_id', 'lft', )

    def __init__(self, *args, **kwargs):
        super(Page, self).__init__(*args, **kwargs)
        # self.title = self.__unicode__()
        # self.title = 'ddd'
        # import debug
        language = None
        lang = language and language or get_language()
        lang_prefix = (not lang == get_default_language() and getattr(settings, 'SCMS_IS_LANG_LINK', True)) and ('/%s' % lang) or ''

        select = {
                                'title': '`scms_slugs`.`title`', 
                                'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                                'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
                                'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (self._meta.db_table, self._meta.db_table),
                                }

        # slug = self.slugs_set.all() 
        if self.pk:
            try:
                slug = Slugs.objects.get(page=self, language=get_language())
            except Slugs.DoesNotExist:
                pass
            else:
                # import debug
                self.title = slug.title 
                self.link = "%s%s" % (lang_prefix, "/" if self.state == page_state.MAIN else slug.alias)  #filter(language='%s' % lang).first()
                self.alias = slug.alias
                self.slug = slug
                self.nchildren = Page.objects.filter(parent=self).aggregate(count=Count('id'))['count']
        # p = Page.objects.filter(pk=self.id, slugs__language='%s' % lang).extra(select=select)[0]        
    
    def __unicode__(self):
        try:
            slug = Slugs.objects.get(page=self, language=get_language())
        except Slugs.DoesNotExist:
            return u'Страница'
        return slug.title
        # return "%s" % slug.title

    def save(self, force_insert=False, force_update=False, using=None):
        # Если вес в списке страниц для страницы не указан, вычисляем его
        if not self.weight:
            weight = Page.objects.filter(parent=self.parent).aggregate(models.Max('weight'))['weight__max']
            self.weight = weight and weight+5 or 5
        
        # Определяем для модели дату последней модификации. Используется для построения sitemap
        self.modifed = datetime.now()
        
        # Сохраняем старое положение в дереве
        old_lft = self.lft
        old_rght = self.rght
        old_tree_id = self.tree_id
                
        result = super(Page, self).save(force_insert, force_update, using)

        if self.state == page_state.MAIN:
            for p in Page.objects.filter(state=page_state.MAIN).exclude(id=self.id):
                p.state=None
                p.save()
        
        # Очищаем кеш текущей страницы
        for lang in dict(settings.SCMS_LANGUAGES).keys():
            pagecache_delete(self.pk, lang, self.type)

        # В случае необходимости, если положение в дереве изменилось, очищаем кеш зависимых по mptt страниц
        if not old_lft == self.lft or not old_rght == self.rght or not old_tree_id == self.tree_id:
            # т.к. изменился родитель, необходимо переформировать алиасы всех потомков и потомков-потомков для всех языков
            for next_slug in Slugs.objects.filter(page=self):
                next_slug.save(rebuild_children_alias=True, using=using)
                
            for p in Page.objects.using(using).filter(tree_id__in=[self.tree_id, old_tree_id]):
                for lang in dict(settings.SCMS_LANGUAGES).keys():
                    pagecache_delete(p.pk, lang, p.type)

        # Эти строчки могут тормозить сохранение страницы при отладке, если не тконнекта с интернетом                
        try:
            if not settings.DEBUG:
                ping_google()
        except:
            pass
        
        # При создании страницы, создаем папку этой страницы на диске
        try:
            from scms.utils import build_page_folder_path
            import os
            os.makedirs(build_page_folder_path(self.id), 0775)
        except OSError, (errno, strerror):
            pass

        return result

    def delete(self, *args, **kwargs):
        # При удалении страницы, удаляем с диска папку этой страницы со всем содержимым
        import shutil
        from scms.utils import build_page_folder_path
        shutil.rmtree(build_page_folder_path(self.id), True)
        
        for p in Page.objects.filter(tree_id=self.tree_id): # Очищаем кеши со всем содержимым
            for lang in dict(settings.SCMS_LANGUAGES).keys():
                pagecache_delete(p.id, lang, p.type)
                
        super(Page, self).delete(*args, **kwargs)
        

    
    def full_load(self, language=None, request=None, only_cached=True):
        # Нельзя вызывать при создании узла, т.к. не будет возвращать актуальную информацию, т.к. еще нет записи в Slugs
        # import debug
        lang = language and language or get_language()
        if self.id:
            cid = pagecache_make_cid(self.pk, lang)
            page = cache.get(cid)
            
            
            #lang_prefix = (not lang == get_default_language() and not lang == get_language() and) and ('/%s' % lang) or ''
            lang_prefix = (not lang == get_default_language() and getattr(settings, 'SCMS_IS_LANG_LINK', True)) and ('/%s' % lang) or ''
            
            if not page:
                try:
                    page = Page.objects.filter(pk=self.id, slugs__language='%s'%lang).extra(select={
                        'title': '`scms_slugs`.`title`', 
                        'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                        'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
                        'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (self._meta.db_table, self._meta.db_table),
                        })[0]
                    
                except IndexError:
                    return None
                # Формирование полей
                page.fields = OrderedDict()

                # Обращаемся к каждому плагину, чтобы тот встраивал данные в контекст, которые кешируются
                for field_obj in scms.site.get_content_type(page.type).get_fields(page):
                    values_lang = field_obj.lang_depended and lang or '' # Определяем язык для получения значений
                    
                    field_data = {}
                    field_data['plugin'] = field_obj
                    field_data['values'] = field_obj.get_context(page, values_lang) # Получаем значения
                    if field_data['values']:
                        # пусть из первого поля будут в параметре
                        for k,v in zip(field_data['values'][0], field_data['values'][0].values()):
                            field_data[k] = v

                    field_data.update(field_data['values']) # С целью доступность без использование values, values использовать для for
                    field_data['type'] = field_obj.__class__.__name__ # Сохраняем тип поля
                    
                    field_data['dynamic'] = getattr(field_obj, 'dynamic', False)
                    
                    setattr(page, field_obj.name, field_data) # Добавляем в атрибуты объекта
                    page.fields[field_obj.name] = field_data # Добавляем в словарь, чтобы можно было в темплейтах делать перечисление полей

                # Формирование родителей
                parents =  page.get_ancestors(ascending=False).filter(slugs__language='%s' % lang).extra(select={
                    'title': '`scms_slugs`.`title`', 
                    'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                    'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
                    'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (self._meta.db_table, self._meta.db_table),
                    })
                page.parents = [np for np in parents] + [page]
                
                # Формирование списка модулей для подгрузки. Сделано с целью оптимизации, чтобы каждый вызов не происходил import_modules
                page.modules = []
                for module_name in ['l_%s-%s'%(page.type, self.pk), 'l_%s'%page.type, 'l_common']:
                    try:
                        mod = import_module('pages.' + module_name)
                        page.modules.append(module_name)
                    except ImportError:
                        continue
                
                
                
                try: #TODO Понимаю, что так не правильно но иначе иногда при сохранении (формировании кеша выскакивает: Can't pickle <type 'function'> или expected string or Unicode object, NoneType found)
                    cache.set(cid, page, 99999999)
                except:
                    pass
            
            if 'smart_cache' in settings.INSTALLED_APPS:
                smart_cache.add('scms_type', page.type)
                smart_cache.add('scms_object', cid)

            if request and hasattr(request, 'scms'):
                # Определяем активна ли эта страница в данный момент    
                if request.scms.has_key('cp'):
                    if get_mongo(): 
                        page.active = (page.id in request.scms['cp'].parents) and 1 or 0
                    else:
                        page.active = (page.id in [p.id for p in request.scms['cp'].parents]) and 1 or 0
                    page.super_active = (page.id == request.scms['cp'].id) and 1 or 0
            
            if not only_cached:             
                # Обращаемся к расширяющим модулям
                for source in page.modules:
                    try:
                        mod = import_module('pages.' + source)
                        #try:
                        prepare_func = getattr(mod, 'load')
                        prepare_func(page, request)
                        #except AttributeError:
                        #    continue
                    except ImportError:
                        continue
    
                # Обращаемся к каждому плагину, чтобы тот встраивал данные в контекст, которые не кешируются
                try:
                    for field_obj in scms.site.get_content_type(page.type).get_fields(page):
                        field_obj.modify_page(page, request)    
                except AttributeError:
                    pass

            # для удобства выборки из объекта
            for key in page.__dict__:
                field = getattr(page, key)
                if isinstance(field, (dict)):
                    setattr(page, key, FieldData(field))

            return page
        else:
            # Заглушка, возможно, этот обработчик вообще не нужен
            self.type = 'root' 
            self.title = ''
            self.alias = ''
            self.date = False
            self.parent_id = None
            self.parents = []
            return self

    def get_pages(self, request, curr_id=None, order='weight', page=None, perpage=None, language=None, filter_vars = None, 
                         params_prefix=None, params_exclude=(), params_use=(), func_modify_qs=None):
        """
        Получение страниц упорядоченных по 'weight' языка 'language'.
        В случае использования пагинатора, страница 'page' и на страницу распологается 'perpage'.
        curr_id -- текущая отображаемая страница на основании которой будут генериться активные пункты во всех меню.
        filter_vars -- словарь-фильтр
        params_prefix -- см. функцию queryset_from_dict
        params_exclude -- см. функцию queryset_from_dict
        params_use -- см. функцию queryset_from_dict
        func_modify_qs -- функция, которая должна вернуть модефицированный объект QuerySet. Используется, например, когда необходимо организовать дополнительные фильтры.
        """
        # Формирование списка родителей. Т.к. это информация необходимо для определения активных пунктов меню на 
        # протяжении всех родителей до самого корня # Вывести в функцию get breadcrumbs
        cp = Page(id=curr_id).full_load(language=None, request=request)
        parents = [str(p.id) for p in cp.parents]
       
        lang = language and language or get_language()
        qs = Page.objects.filter(slugs__language='%s'%lang, published=1 ).exclude(state__in=[page_state.EXTRAHIDDEN, page_state.IN_TRASH, page_state.SETTINGS])
    
        # маркер, если не включать скрытые. По умолчанию не включать
        notshowhidden = True
        
        # Если необходимо использовать допонительные фильтры
        if filter_vars:
            from scms.utils import queryset_from_dict
            qs = queryset_from_dict(qs, filter_vars, params_prefix, params_exclude, params_use)
            
            # Смотрим, есть ли какое-либо управление скрытыми полями, если есть, тогда убираем фильтр не включать в список скрытые страницы
            for key in filter_vars.keys():
                if key == 'hidden' or key.startswith('hidden__'):
                    notshowhidden = False
    
        if notshowhidden == True:
            qs = qs.filter(hidden=0)
        
        if func_modify_qs:
            qs = func_modify_qs(qs)
        
        if order:
            qs = qs.order_by(*order.split(','))

	lang_prefix = (not lang == get_default_language() and getattr(settings, 'SCMS_IS_LANG_LINK', True)) and ('/%s' % lang) or ''
        #lang_prefix = (not lang == get_default_language() and not lang == get_language()) and ('/%s' % lang) or ''

        qs = qs.extra(select={
            'title': '`scms_slugs`.`title`', 
            'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
            'active': '`scms_page`.`id` IN (%s)' % (parents and ','.join(parents) or '0'),
            'is_front': 'IF (`scms_page`.`state` = %s, True, False)' % page_state.MAIN,
            }).distinct()
            
        #if order == '?':
        #ss = str(qs.query)
        #    w=1/0
            
        if page and perpage: # Если используется пагинатор
            paginator = Paginator(qs, perpage)
            try:
                return paginator.page(page)
            except (EmptyPage, InvalidPage):
                return paginator.page(paginator.num_pages)
        elif perpage: # Если необходимо отобразить определенное количество
            return {'object_list': qs[:perpage]}
        else: # Если необходимо отобразить все результаты
            return {'object_list': qs}
        

try:
    mptt.register(Page)
except mptt.AlreadyRegistered:
    pass

class Slugs(models.Model):
    title = models.CharField(_("Title"), max_length=255, blank=False, db_index=False, unique=False)
    page = models.ForeignKey(Page, blank=False, db_index=True)
    language = models.CharField(_("Language"), max_length=5, db_index=True)
    slug = models.SlugField(_("Slug"), max_length=255, blank=True, db_index=True, unique=False)
    alias  = models.CharField(_("Alias"), max_length=255, blank=True, null=True, db_index=True)
    class Meta:
        app_label = 'scms'
        unique_together = ("language", "alias")
    
    def __unicode__(self):
        return '/%s%s' % (self.language, self.alias.replace("*", ''))
    
        
    def save(self, force_insert=False, force_update=False, using=None, rebuild_children_alias=False):
        #if (self.slug): непонятно, как определять родителя, да и надо ли. Да и как быть в ситуации перемещения...
        #    slug_copy = Slugs.objects.filter(slug=self.slug, language=self.language, page__parent=self.parent).exclude(page=self.page)
        #    if slug_copy.count():
        #        raise ValueError, u"Дублирование поля Slug"
        # Очищаем кеш, используемый в scms.utils.pageload

        old_slug = None
        if not rebuild_children_alias: # Просто без разницы какой старый слуг, если всё равно обязательно будем переформировывать потомков, а лишние запросы нам не нужны
            try:
                old_slug = Slugs.objects.get(pk=self.id)
            except Slugs.DoesNotExist:
                pass 

        # Если поле слаг пустое, генерируем слаг автоматически
        if not self.slug:
            slug = "%s".lower() % (translit.slugify(self.title))
            i = 1
            while True:
                try:
                    Slugs.objects.exclude(id=self.pk).get(slug=slug, language=self.language)
                except Slugs.DoesNotExist:
                    self.slug = slug
                    break
                except Slugs.MultipleObjectsReturned:
                    pass

                slug = "%s_%s".lower() % (translit.slugify(self.title), i)
                i += 1            

        # Если поле алиас пустое, или начинается с символа '*' -- генерируем алиас автоматически
        if not self.alias or self.alias[0] == '*':
            #pk = self.page.pk
            #e=1/0
            self.alias = '*'
            # Page._tree_manager.rebuild() #Если перестают правильно формироваться альясы

            for next_page in self.page.get_ancestors(ascending=False, include_self=True).using(using): # Получаем каждого родителя
                try:
                    next_slug = next_page == self.page and self or Slugs.objects.using(using).get(page=next_page, language=self.language)
                    next_slug = next_slug.slug and next_slug.slug or str(next_page.id)
                except Slugs.DoesNotExist:
                    next_slug = str(next_page.id)
                
                self.alias = '%s/%s' % (self.alias, next_slug)
        else:
            if not self.alias[0] == '/': # Если алиас сгенерирован не автоматически, удостоверяемся, что в начале есть слеш
                self.alias = '/' + self.alias
            if self.alias[-1] == '/': # Если алиас сгенерирован не автоматически, удостоверяемся, что в начале есть слеш
                self.alias = self.alias[0:-1]

        super(Slugs, self).save(force_insert, force_update, using)
        
        # В случае, если слуг поменялся либо, по какой либо другой причине (если rebuild_children_alias) Пересохраняем всех потомков рекурсивно, чтобы им переформировались алиасы
        if rebuild_children_alias or (old_slug and not old_slug.slug == self.slug):
            children_slugs = Slugs.objects.filter(language=self.language, page__in=self.page.get_children())
            for next_slug in children_slugs:
                next_slug.save(rebuild_children_alias=True) # rebuild_children_alias -- для того, чтобы алиасы потомков этого потомка тоже переформировались

        pagecache_delete(self.page.id, self.language, self.page.type)

class modict(dict, object):
    """docstring for modict"""
    def __init__(self, *args, **kwargs):
        super(modict, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return mark_safe(force_unicode(smart_str(self.get('body') or "%s" % self.get('data', "") or self.get('state', ""))))

    def pk(self):
        return self.get('id', '')

    # def __getattr__(self, key):
    #     # import debug
    #     # if hasattr(self.query_result, key):
    #     try:
    #         return  self.mark_safe(self.get(key, ""))
    #     except AttributeError:
    #         pass
    #         # return  self.mark_safe("")


class pagedict(dict):
    """docstring for modict"""
    def __init__(self, *args, **kwargs):
        super(pagedict, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return mark_safe(force_unicode(smart_str(self.get('body') or "%s" % self.get('data') or self.get('state') or "")))

    def pk(self):
        return self.get('pk')

    # def __call__(self):
    #     return self.get('body') or self.get('data') or self.get('state') or self

class MongoManager(object):
    """docstring for MongoManager"""
    

    def safe_value(value):
        return mark_safe(force_unicode(smart_str(value)))
    safe_value.is_safe = True

    def __init__(self, *args, **kwargs):
        super(MongoManager, self).__init__()
        db = get_mongo()
        if not db: 
            return 
        import pymongo
        self.pymongo = pymongo

        self.args = args
        self.kwargs = kwargs
        self.query = kwargs.get('query', list(args)[0] if args else {})
        self.query_db = db
        self.query_collection = kwargs.get('collection', 'pages')
        self.query_context = kwargs.get('context', {})
        self.query_page = kwargs.get('page', 1)
        self.query_limit = kwargs.get('limit', 100)
        self.query_from = kwargs.get('from', 0)
        self.query_page = kwargs.get('page', 1)
        self.query_sort = self.parse_sort(kwargs.get('sort')) if kwargs.get('sort') else [("weight", pymongo.ASCENDING)]
        self.query_show_hidden = kwargs.get('show_hidden', False)
        self.query_result = self.query_db[self.query_collection].find(self.query).sort(self.query_sort)
        self.query_start = 0
        self.parent_self = kwargs.get('parent')
        # self.children = self.get_children_all()
        # self.children = lambda: MongoManager({'lft__gt': self.lft, 'lft__lt': self.rght, 'tree_id': self.tree_id}, sort="level,weight")
        # self.first = self.query_result[0] if self.query_result.count() else []
        self.paginator = self.get_paginator()
        self.first = self.get_self()
    
    def __len__(self):
        # переделать для быстрого подсчета
        return len([i for i in self]) #self.query_result.count() if self.get_self() else 0

    # def __repr__(self):
    #     return "id=1"
    #     # return self.get_self()
    #     return "%s" % self.get_self().get('id', "")

    # def __unicode__(self):
    #     # return self.get_self()
    #     return "%s" % self.get_self().get('id', "")

    # def __str__(self):
    #     # return self.get_self()
    #     return "%s" % self.get_self().get('id', "")

    def get_self(self):
        try:
            first = self.query_result[self.query_start]
        except IndexError:
            first = {}
        return first

    def get_parents(self):
        if self.get_self().get('parents'):
            parents = MongoManager({'id': {"$in": self.get_self().get('parents')}}, sort="level")
            return parents
        return None

    def get_children_all(self):
        if self.get_self():
            return MongoManager({'$or': [{'lft': {'$gt': self.lft}, 'tree_id': self.tree_id, 'rght': {'$lt': self.rght}}], '$nor': [{'state': 3, 'hidden': True, 'published': False}]}, sort="level,weight")
        else:
            return []

    def get_paginator(self):
        try:
            page = int(self.query_page)
        except ValueError :
            self.query_page = page = 1
        try:
            num_pages = self.count() / self.query_limit
        except self.pymongo.errors.InvalidDocument:
            num_pages = 0

        paginator = {
            'num_pages': num_pages,
            'from': self.query_limit*page-self.query_limit,
            # 'from0': self.query_limit*page-self.query_limit-1,
            'to': self.query_limit*page+self.query_limit-self.query_limit,
            # 'to0': self.query_limit*page+self.query_limit-self.query_limit-1,
            'page': page,
            'page_range': range(1, num_pages+1)
        }
        return paginator

    def get_children(self):
        if self.get_self():
            return MongoManager({'parent':self.id, '$nor': [{'state': 3, 'hidden': True, 'published': False}]}, sort="level,weight")
        else:
            return []

    def parse_sort(self, string=None):
        # string = string or self.in_data.get('sort')
        if string:
            sort = []
            for val in string.split("&"):
                if val.startswith('-'):
                    sort.append((val[1:], self.pymongo.DESCENDING))
                else:
                    sort.append((val, self.pymongo.ASCENDING))
            return sort

    def get_query(self):
        return mark_safe(self.query)

    def pk(self):
        return self.id

    def mark_safe(self, data):
        if isinstance(data, (unicode, str)):
            return mark_safe(force_unicode(data))
        elif isinstance(data, (dict)):
            data = modict(data)
            for key, val in zip(data, data.values()):
                if key == 'serialized-object':
                    # data[key] = val
                    del(data[key])
                else:
                    data[key] = self.mark_safe(val)
            return data
        elif isinstance(data, (tuple, list)):
            tmp = []
            for val in data:
                tmp.append(self.mark_safe(val))
            return tmp
        return data

    # def __str__(self, key):
    #   return self.first.get('body') or self.first.get('data') or self.first.get('state')

    def __getattr__(self, key):
        # import debug
        # if hasattr(self.query_result, key):
        try:
            return getattr(self.query_result, key)
        except AttributeError:
            try:
                return  self.mark_safe(self.get_self().get(key, ""))
            except AttributeError:
                pass
                # return  self.mark_safe("")


    def __getitem__(self, key):
        return getattr(self, key)

    def __getslice__(self, index, end=None, sequence=None):
        if end:
            return self.query_result[index:end]
        return self.query_result[index]
    
    def __iter__(self):
        # import debug
        # for i in range(0, self.query_result.count()):#quer.y_result.skip(10).limit(20):
        #   yield self.mark_safe(self.query_result[i])
        for i in range(self.paginator['from'], self.paginator['to']):
            try:
                # self.query_start = i
                # yield self.query_result[i]
                # yield self
                yield self.mark_safe(self.query_result[i])
                # yield pagedict(self.query_result[i])
                # yield MongoManager({'id': 1})
            except IndexError:
                break
        # for r in self.query_result.skip(self.query_from).limit(self.query_from+self.query_limit):
        #     yield r
            # yield self.query_result.next()

    def object_list(self):
        # import debug
        return self#quer.y_result#quer.y_result#quer.y_result.skip(10).limit(20):

# Сообщаем всем модулям, связным со страницей, что страница удалена
def page_pre_delete(sender, **kwargs):
    obj = kwargs['instance']
    
    try:
        rel_inline_instances = scms.site.get_content_type(obj.type).get_fields()
        for inline in rel_inline_instances:
            inline.will_delete(object)
    except:
        pass
pre_delete.connect(page_pre_delete, sender=Page)

@receiver(post_save, sender=Slugs)
def page_mongo_save(sender, instance, **kwargs):
        '''
        from scms.models.pagemodel import Slugs
        for s in Slugs.objects.filter(language='ru'):
            s.save()
        '''
        # Serialization for mongodb
        db = get_mongo()
        if not db: 
            return 

        # for field_obj in scms.site.get_content_type(self.type).get_fields(self):
        #     pass
        # import debug
        slug = instance
        full_page = Page.objects.filter(pk=slug.page.id, slugs=slug).extra(select={
                        'title': '`scms_slugs`.`title`', 
                        'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                        'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (slug.language, page_state.MAIN),
                        'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (slug.page._meta.db_table, slug.page._meta.db_table),
                        })[0]
        # full_page = full_page.full_load(slug.language)
        tmp = full_page.__dict__
        page = {}

        for key, val in zip(tmp, tmp.values()):
            if isinstance(val, (list, tuple, dict, int, bool, long, float, str)) and not isinstance(val, (FieldData)):
                page[key] = val
            if isinstance(val, (datetime)):
                page[key] = val #datetime.strftime(val.now(), "%Y-%m-%d") # %H:%M:%S
            pass

        fields = {}
        # import debug
        # d = full_page._meta.related_objects
        # d = obj.related_model.__bases__
        for obj in full_page._meta.related_objects:
            if scms.models.pluginmodel.SCMSPluginModel in obj.related_model.__bases__ or \
                scms.models.pagemodel.Page in obj.related_model.__bases__:
                for d in obj.related_model.objects.filter(page=full_page):
                    key = d.field_name
                    data = {}
                    for k,v in zip(d.__dict__, d.__dict__.values()):
                        if isinstance(v, (str)) and not isinstance(v, (FieldData)):
                            data[k] = "%s" % v
                        elif isinstance(v, (list, tuple, dict, int, bool, long, float)) and not isinstance(v, (FieldData)):
                            data[k] = v
                        elif isinstance(v, (datetime)):
                            data[k] = v
                        else:
                            data[k] = "%s" % v
                    if not fields.get(key):
                        fields[key] = deepcopy(data)
                        fields[key]['0'] = deepcopy(data)
                        fields[key]['values'] = [deepcopy(data)]
                    else:
                        fields[key]['values'].append(deepcopy(data))

        # del(page['fields'])
        for key, val in zip(fields, fields.values()):
            page[key] = val
        # import debug
        # page['parents'] = [p.id for p in page['parents']]
        page['authors'] = [a.id for a in full_page.authors.all()]
        # page['parents'] = [p.id for p in full_page.parents] if hasattr(full_page, 'parents') else None
        parents =  full_page.get_ancestors(ascending=False)
        # parents =  page.get_ancestors(ascending=False).filter(slugs__language='%s' % lang).extra(select={
        #             'title': '`scms_slugs`.`title`', 
        #             'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
        #             'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
        #             'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (self._meta.db_table, self._meta.db_table),
        #             })
        page['parents'] = [p.id for p in parents]
        page['state'] = full_page.state
        page['pk'] = page['id']
        page['type'] = full_page.type
        page['alias'] = full_page.alias if full_page.alias[0] != '*' else full_page.alias[1:]
        page['title'] = slug.title
        page['slug'] = "%s" % slug
        page['slug'] = page['slug'].replace("//", "/")
        page['parent'] = full_page.parent_id if full_page.parent_id else None
        page['link'] = "/%s" % full_page.link
        page['link'] = page['link'].replace("/ru", "")
        page['parent_id'] = full_page.parent_id if full_page.parent_id else None
        page['language'] = slug.language
        page['slug_id'] = slug.id
        # page['serialized-object'] = Binary(cPickle.dumps(full_page.full_load)) # full_page не сохраняется если full_load
        page['serialized-object'] = Binary(dill.dumps(full_page.full_load)) # full_page не сохраняется если full_load
        result = db.pages.delete_many({"id": page['id'], 'language': slug.language})
        result = db.pages.update_one({'id': page['id'], 'language': slug.language}, {"$set":page})
        if not result.modified_count:
            result = db.pages.insert_one(page)
        for p in db.pages.find():
            pass
        return result

@receiver(pre_delete, sender=Slugs)
def page_mongo_delete(sender, instance, **kwargs):
        # Serialization for mongodb
        db = get_mongo()
        if not db: 
            return 
        result = db.pages.delete_many({
            "$or": [
                {"id": instance.id, 'language': instance.language}, 
                {"lft": {"$gt": instance.page.lft, "$lt": instance.page.rght}, 'tree_id': instance.page.tree_id, 'language': instance.language},
                {"parent_id": instance.page.id, 'language': instance.language},
                ] 
        })
        return result
