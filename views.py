# coding=utf-8
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound
from scms.utils import get_language_from_request
from scms.models.pagemodel import Slugs, Page, page_state, MongoManager
from django.shortcuts import render_to_response
from django.conf import settings
from scms.utils.i18n import get_default_language
from scms.utils import get_destination
from django.utils.translation import ugettext_lazy as _, gettext
from django.utils.encoding import force_unicode
from django.core.cache import cache
from django.contrib import messages
import datetime
from importlib import import_module
#from django.core.files import File
#import os
import scms
from django.views.decorators.csrf import csrf_protect
# from django.core.context_processors import csrf
from django.db.models import Q
from django.template import RequestContext
from scms.utils import get_mongo

@csrf_protect
def scms_mongo_render(request, alias=''):
    # Формирование страницы
    db = get_mongo()
    if not db: 
        return scms_render(request, alias)
    import pymongo

    request.scms = {}
    
    lang = get_language_from_request(request)
    if alias:
        query = {'language':lang, '$or': [{'alias': '*/%s' % alias}, {'alias': '/%s' % alias}]}
        slug = MongoManager(query)
        is_front = False
        # import debug
        # Чтобы главная страница не дублировалась с двумя адресами
        if slug.state == page_state.MAIN:
            return HttpResponseRedirect('/')
    else:
        # slug = Slugs.objects.filter(page__state=page_state.MAIN, language=lang)[0] # Сделать выдачу исключения , что нет главной страницы
        slug = MongoManager({'state':1, 'language':lang})

        is_front = True
    # import debug
    if not slug.pk:
        raise Http404()
    elif slug.count() > 1:
        raise Http404('Exception: Slugs.MultipleObjectsReturned')

    if not slug.published and alias != 'search':
        raise Http404()

    # try:
    #     cp = Page(id=slug.page_id).full_load(request=request, only_cached=False) # объект текущей страницы
    # except Page.DoesNotExist:
    #     raise Http404()
    cp = slug

    is_inner = cp.parent_id and True or False
    pp = is_inner and MongoManager({'id':cp.parent_id}) or False
    
    
    request.scms['cp'] = cp

    lang_prefix = not lang == get_default_language() and ('/%s' % lang) or ''

    # Подготавливаем сервисные ссылки для быстрого доступа к админке
    scms_links = []

    if  request.user.id: # Чтобы лишние запросы к БД не создовались
        from scms.admin.pageadmin import PageAdmin
        pageadmin = PageAdmin(scms.models.pagemodel.Page, False)
        
        if pageadmin.has_change_permission(request, cp):
            getlang = not lang == get_default_language() and '&language=%s' % lang or ''
    
            scms_links.append({
                'name': _('Edit'), 
                'href': '/admin/scms/page/%s/?destination=alias%s' % (cp.pk, getlang)
            }) 
        
        if pageadmin.has_delete_permission(request, cp):
            link = pp and pp.link or '/'
            scms_links.append({
                'name': _('Delete'), 
                'href': '/admin/scms/page/%s/delete/?destination=%s' % (cp.pk, link ) 
            })
        # parent_content_type = scms.site.get_content_type(cp.type)
        # for children_name in parent_content_type.children:
        #     next_content_type = scms.site.get_content_type(children_name)
        #     if not pageadmin.has_add_permission(request, parent_page=cp, type=children_name):
        #         continue
        #     scms_links.append({
        #         'name': _('Create %s') % force_unicode(next_content_type.name),
        #         'href': '/admin/scms/page/add/?type=%s&parent=%s&destination=%s' % (next_content_type.id, cp.pk, get_destination(request) )                               
        #     })
        # if request.user.is_staff:
        #     scms_links.append({
        #         'name': _('Go to CMS'), 
        #         'href': '/admin/',
        #     }) 
    
    request.scms_page = cp # сохраняем в request текущую просматриваемую страницу, чтобы можно было ее использовать например в plugins.contact_form Чтобы знать с какой страницы отправлено сообщение

    context = {  'title': slug.title, 
                 'link': cp.link,
                 'page_id': cp.id, 
                 'parent_id': cp.parent_id,
                 'lang_prefix': lang_prefix,
                 'lang': lang,
                 'is_inner': is_inner, # т.е. если страница не в корне
                 'is_front': is_front,
                 'scms_links': scms_links,
                 'request': request,
                 'cp': cp,
                 'pp': pp,
                 'now': datetime.datetime.now().strftime("%Y-%m-%d %H:%M") ,
                 'breadcrumbs': cp.get_parents()
              }

    # context.update(csrf(request))
    # context.update(request)

    # Формируем обращаемся к страницам
    for source in ['%s-%s' % (cp.type, cp.id), cp.type, 'common']:
        try:
            mod = import_module('pages.' + source)
        except SyntaxError as err:
            raise SyntaxError(err)
        except ImportError:
            continue    
            
        prepare_func = getattr(mod, 'prepare')
        
        if prepare_func:
            result = prepare_func(request, context, alias)
            if result:
                return result
        
            
    subtype = request.GET.get('subtype', '')
    templates = ['page-%s-%s-%s-%s.html' % (cp.type, cp.id, lang, subtype),
                                   'page-%s-%s-%s.html' % (cp.type, cp.id, lang),
                                   'page-%s-%s-%s.html' % (cp.type, cp.id, subtype),
                                   'page-%s-%s.html' % (cp.type, cp.id),
                                   'page-%s-%s-%s.html' % (cp.type, lang, subtype), 
                                   'page-%s-%s.html' % (cp.type, lang), 
                                   'page-%s-%s.html' % (cp.type, subtype),
                                   'page-%s.html' % cp.type,
                                   'page-common-%s.html' % lang,
                                   'page-common.html',]
    response = render_to_response(templates, context, context_instance=RequestContext(request))
    
    
    #smart_cache.go(html_cache_fpathname, 0, depended_types=self.depended_types, adition_dependies=self.adition_dependies, delete_callback=None)
    # Сохранение сформированной страницы в кеш
    #try:
    #    dirname = os.path.dirname(html_cache_fpathname)
    #    if not os.path.exists(dirname):
    #        os.makedirs(dirname)
    #    html_cache_fhandle = open(html_cache_fpathname, 'w+')
    #    html_cache_fobj = File(html_cache_fhandle)
    #    html_cache_fobj.write(response.content)
    #    html_cache_fobj.close()
    #except OSError:
    #    pass    
    return response
    
@csrf_protect
def scms_render(request, alias=''):
    
    # Подготовка имени файла для механизма кеширования целых страниц
    #html_cache_fname = alias and alias or 'index'
    #if request.environ['QUERY_STRING']:
    #    html_cache_fname = html_cache_fname + '&&&' + request.environ['QUERY_STRING']
    #html_cache_fpathname = settings.SITE_ROOT + settings.TMP_DIR + 'html_cache/' + html_cache_fname + '.html'
    
    # Попытка загрузки кеша из файла
    #try:
    #    html_cache_fhandle = open(html_cache_fpathname, 'r')
    #    html_cache_fobj = File(html_cache_fhandle)
    #    content = html_cache_fobj.read()
    #    html_cache_fobj.close()
    #    return HttpResponse(content)
    #except IOError:
    #    pass
    
    
    
    # Формирование страницы
    request.scms = {}
    
    lang = get_language_from_request(request)
    
    try:
        if alias:
            #slug = Slugs.objects.get(alias__regex=r'^[\*]?/%s$' % alias, language=lang)
            slug = Slugs.objects.get(Q(alias='*/%s' % alias) | Q(alias='/%s' % alias), language=lang) #, page__published=True)
            is_front = False
            
            # Чтобы главная страница не дублировалась с двумя адресами
            if slug.page.state == page_state.MAIN:
                return HttpResponseRedirect('/')
        else:
            slug = Slugs.objects.filter(page__state=page_state.MAIN, language=lang)[0] # Сделать выдачу исключения , что нет главной страницы
            is_front = True
    except Slugs.DoesNotExist:
        raise Http404()
    except Slugs.MultipleObjectsReturned:
        raise Http404('Exception: Slugs.MultipleObjectsReturned')

    if not slug.page.published and alias != 'search':
        raise Http404()

    try:
        cp = Page(id=slug.page_id).full_load(request=request, only_cached=False) # объект текущей страницы
    except Page.DoesNotExist:
        raise Http404()

    is_inner = cp.parent_id and True or False
    pp = is_inner and Page(id=cp.parent_id).full_load(request=request) or False
    
    
    request.scms['cp'] = cp

    lang_prefix = not lang == get_default_language() and ('/%s' % lang) or ''

    # Подготавливаем сервисные ссылки для быстрого доступа к админке
    scms_links = []
    if request.user.id: # Чтобы лишние запросы к БД не создовались
        from scms.admin.pageadmin import PageAdmin
        pageadmin = PageAdmin(scms.models.pagemodel.Page, False)
        
        if pageadmin.has_change_permission(request, cp):
            getlang = not lang == get_default_language() and '&language=%s' % lang or ''
    
            scms_links.append({
                'name': _('Edit'), 
                'href': '/admin/scms/page/%s/?destination=alias%s' % (cp.pk, getlang)
            }) 
    
        if pageadmin.has_delete_permission(request, cp):
            link = pp and pp.link or '/'
            scms_links.append({
                'name': _('Delete'), 
                'href': '/admin/scms/page/%s/delete/?destination=%s' % (cp.pk, link ) 
            })
        parent_content_type = scms.site.get_content_type(cp.type)
        for children_name in parent_content_type.children:
            next_content_type = scms.site.get_content_type(children_name)
            if not pageadmin.has_add_permission(request, parent_page=cp, type=children_name):
                continue
            scms_links.append({
                'name': _('Create %s') % force_unicode(next_content_type.name),
                'href': '/admin/scms/page/add/?type=%s&parent=%s&destination=%s' % (next_content_type.id, cp.pk, get_destination(request) )                               
            })
        if request.user.is_staff:
            scms_links.append({
                'name': _('Go to CMS'), 
                'href': '/admin/',
            }) 
    
    request.scms_page = cp # сохраняем в request текущую просматриваемую страницу, чтобы можно было ее использовать например в plugins.contact_form Чтобы знать с какой страницы отправлено сообщение

    context = {  'title': slug.title, 
                 'link': cp.link,
                 'page_id': slug.page_id, 
                 'parent_id': cp.parent_id,
                 'lang_prefix': lang_prefix,
                 'lang': lang,
                 'is_inner': is_inner, # т.е. если страница не в корне
                 'is_front': is_front,
                 'scms_links': scms_links,
                 'request': request,
                 'cp': cp,
                 'pp': pp,
                 'now': datetime.datetime.now().strftime("%Y-%m-%d %H:%M") ,
                 'breadcrumbs': cp.parents,
              }
    # import debug
    # context.update(csrf(request))
    # context.update(dict(request))

    # Формируем обращаемся к страницам
    for source in ['%s-%s'%(cp.type, cp.id), cp.type, 'common']:
        try:
            mod = import_module('pages.' + source)
        except SyntaxError as err:
            raise SyntaxError(err)
        except ImportError:
            continue    
            
        prepare_func = getattr(mod, 'prepare')
        
        if prepare_func:
            result = prepare_func(request, context, alias)
            if result:
                return result
        
            
    subtype = request.GET.get('subtype', '')
    
    
    response = render_to_response(['page-%s-%s-%s-%s.html' % (cp.type, cp.id, lang, subtype),
                                   'page-%s-%s-%s.html' % (cp.type, cp.id, lang),
                                   'page-%s-%s-%s.html' % (cp.type, cp.id, subtype),
                                   'page-%s-%s.html' % (cp.type, cp.id),
                                   'page-%s-%s-%s.html' % (cp.type, lang, subtype), 
                                   'page-%s-%s.html' % (cp.type, lang), 
                                   'page-%s-%s.html' % (cp.type, subtype),
                                   'page-%s.html' % cp.type,
                                   'page-common-%s.html' % lang,
                                   'page-common.html',], context, context_instance=RequestContext(request))
    
    
    #smart_cache.go(html_cache_fpathname, 0, depended_types=self.depended_types, adition_dependies=self.adition_dependies, delete_callback=None)
    # Сохранение сформированной страницы в кеш
    #try:
    #    dirname = os.path.dirname(html_cache_fpathname)
    #    if not os.path.exists(dirname):
    #        os.makedirs(dirname)
    #    html_cache_fhandle = open(html_cache_fpathname, 'w+')
    #    html_cache_fobj = File(html_cache_fhandle)
    #    html_cache_fobj.write(response.content)
    #    html_cache_fobj.close()
    #except OSError:
    #    pass    
    return response
    
    
def scms_clearcache(request, alias=''):
    if request.user.id:
        cache.clear()
        
        if 'smart_cache' in settings.INSTALLED_APPS:
            import smart_cache
            smart_cache.empty()
        
        messages.info(request, gettext('Cache is cleared'))
        return HttpResponseRedirect('/admin/')
    else:
        return HttpResponseNotFound()
        
def scms_treerebuild(request, alias=''):
    if request.user.id:
        Page._tree_manager.rebuild()
        messages.info(request, gettext('Tree is rebuilded'))
        return HttpResponseRedirect('/admin/')
    else:
        return HttpResponseNotFound()
