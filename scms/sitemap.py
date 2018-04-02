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
        # qs = Page.objects.filter(published=1, slugs__language__in=[lang[0] for lang in settings.SCMS_LANGUAGES]).order_by('id','slugs__alias').extra(select={
        #         'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
        #         'language': '`scms_slugs`.`language`',
        #         }).exclude(state__in=[page_state.EXTRAHIDDEN, page_state.IN_TRASH, page_state.SETTINGS]).exclude(slugs__alias=None)
        qs = Slugs.objects.filter(page__published=1, language__in=[lang[0] for lang in settings.SCMS_LANGUAGES]).order_by('id','alias').extra(select={
                'alias': 'IF (`scms_page`.`state` = %s, "/", REPLACE(`scms_slugs`.`alias`,"*",""))' % page_state.MAIN,
                'language': '`scms_slugs`.`language`',
                }).exclude(page__state__in=[page_state.EXTRAHIDDEN, page_state.IN_TRASH, page_state.SETTINGS]).exclude(alias=None).values("page__modifed", "language", "page__date", "id", "alias")
        return qs

    def lastmod(self, obj):
        return  obj.get("page__modifed") or obj.get("page__date")
    
    def location(self, obj):
        if obj.get("alias") == None: # Нарушена целосность БД и есть страницы, для которых нет Slug
            return '/' 
        if obj.get("language") == self.default_language or obj.get("language") is None:
            return obj.get("alias")
        else:
            return '/%s%s' % (obj.get("language"), obj.get("alias"))