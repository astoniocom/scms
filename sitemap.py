# coding=utf-8
from django.contrib.sitemaps import Sitemap
from scms.models import Page, Slugs, page_state
from scms.utils.i18n import get_default_language
from django.conf import settings

class SCMSSitemap(Sitemap):
    #changefreq = "never"
    #priority = 0.5

    def items(self):
        self.default_language = get_default_language()
        qs = Page.objects.filter(published=1, slugs__language__in=[lang[0] for lang in settings.SCMS_LANGUAGES]).order_by('id','slugs__alias').extra(select={
                'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                'language': '`scms_slugs`.`language`',
                }).exclude(state__in=[page_state.EXTRAHIDDEN, page_state.IN_TRASH, page_state.SETTINGS]).exclude(slugs__alias=None)
        len(qs) # Почему то по разному считается len(qs) и qs.count. И коунт считается не правильно из Sitemap.paginator. А если мы тут делаем len, то считается всё правильно. Google: django count and len different
        return qs

    def lastmod(self, obj):
        return  obj.modifed and obj.modifed or obj.date
    
    def location(self, obj):
        if obj.alias == None: # Нарушена целосность БД и есть страницы, для которых нет Slug
            return '/' 
        if obj.language == self.default_language or obj.language is None:
            return obj.alias
        else:
            return '/%s%s' % (obj.language, obj.alias)