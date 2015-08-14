# coding=utf-8
from django.db import models
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.contrib.sitemaps import ping_google
from django.utils.translation import get_language
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from scms.utils.i18n import get_default_language
from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
import scms
import mptt

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
    
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', db_index=True, default=None)
    type   = models.CharField(_("Type"), max_length=16, blank=False, db_index=True)
    weight = models.IntegerField(_("Weight"), max_length=4, blank=False, db_index=True, default=0)
    published = models.BooleanField(_("Published"), default=True, blank=False, db_index=True)
    hidden = models.BooleanField(_("Hidden"), default=False, blank=False, db_index=True)
    expanded = models.BooleanField(_("Expanded"), default=False, blank=False, db_index=True)
    state = models.IntegerField(_("State"), max_length=1, blank=True, null=True, db_index=True, choices=state_choises)
    date = models.DateTimeField(_("Date"), default=datetime.now)
    modifed = models.DateTimeField(_("Modifed"), blank=True)
    authors = models.ManyToManyField(User, blank=True)
    
    class Meta:
        app_label = 'scms'
        verbose_name = _('page')
        verbose_name_plural = _('pages')
        ordering = ('weight', 'tree_id', 'lft', )
    
    def __unicode__(self):
        try:
            slug = Slugs.objects.get(page=self, language=get_language())
        except Slugs.DoesNotExist:
            return u'Страница'
        return slug.title

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
                page.fields = SortedDict()
                # Обращаемся к каждому плагину, чтобы тот встраивал данные в контекст, которые кешируются
                for field_obj in scms.site.get_content_type(page.type).get_fields(page):
                    values_lang = field_obj.lang_depended and lang or '' # Определяем язык для получения значений
                    
                    field_data = {}
                    field_data['plugin'] = field_obj
                    field_data['values'] = field_obj.get_context(page, values_lang) # Получаем значения
                    field_data.update(field_data['values']) # Сцелью доступность без использование values, values использовать для for
                    field_data['type'] = field_obj.__class__.__name__ # Сохраняем тип поля
                    
                    field_data['dynamic'] = getattr(field_obj, 'dynamic', False)
                    
                    setattr(page, field_obj.name, field_data) # Добавляем в атрибуты объекта
                    page.fields[field_obj.name] = field_data # Добавляем в словарь, чтобы можно было в темплейтах делать перечисление полей
                
                # Формирование родителей
                parents =  page.get_ancestors(ascending=False).filter(slugs__language='%s'%lang).extra(select={
                    'title': '`scms_slugs`.`title`', 
                    'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                    'link': 'CONCAT("%s", IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*","")))' % (lang_prefix, page_state.MAIN),
                    'nchildren': 'SELECT COUNT(*) FROM %s as p WHERE p.parent_id = %s.id' % (self._meta.db_table, self._meta.db_table),
                    })
                page.parents = [np for np in parents] + [page]
                
                # Формирование списка модулей для подгрузки. Сделано с целью оптимизации, чтобы каждый вызов не происходил import_modules
                page.modules = []
                for madule_name in ['l_%s-%s'%(page.type, self.pk), 'l_%s'%page.type, 'l_common']:
                    try:
                        mod = import_module('pages.' + madule_name)
                        page.modules.append(madule_name)
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
