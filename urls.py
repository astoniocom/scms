import django, tinymce
from django.contrib import admin
from django.conf import settings
from django.conf.urls import include, url
from scms.views import scms_render, scms_clearcache, scms_treerebuild, scms_mongo_render
from filebrowser.sites import site
# from filebrowser.sites import site as fb_site

urlpatterns = [
    # url(r'^media/(.*)$', django.views.static.serve, {'document_root': settings.CURRENT_TEMPLATE_MEDIA }),
    # url(r'^(img/.*)$', django.views.static.serve, {'document_root': settings.CURRENT_TEMPLATE_DIR }),
    # url(r'^(_base\.css)$', django.views.static.serve, {'document_root': settings.CURRENT_TEMPLATE_DIR }),
    # url(r'^files/(.*)$', django.views.static.serve, {'document_root': settings.MEDIA_ROOT }),
    # url(r'^(static/admin/css/changelists.css)$', django.views.static.serve, {'document_root': settings.SITE_ROOT }),
    # url(r'^static/admin/(.*)$', django.views.static.serve, {'document_root': 'x:/Python27/Lib/site-packages/django/contrib/admin/static/admin/'}),
    # url(r'^static/filebrowser/(.*)$', django.views.static.serve, {'document_root': 'x:/Python27/Lib/site-packages/filebrowser/static/filebrowser'}),
    # url(r'^filebrowser/media/(.*)$', django.views.static.serve, {'document_root': 'x:/Python27/Lib/site-packages/filebrowser/media/filebrowser'}),
    # url(r'^tiny_mce/media/(.*)$', django.views.static.serve, {'document_root': 'x:/Python27/Lib/site-packages/tinymce/media/tiny_mce'}),
    # url(r'^scms/media/(.*)$',  django.views.static.serve, {'document_root': 'x:/Python27/Lib/site-packages/scms/media/scms'}),
    url(r'^tinymce/', include('tinymce.urls')),
    url(r'^admin/', admin.site.urls),

    # url(r'^grappelli/', include('grappelli.urls')),
    # url(r'^admin/filebrowser/', include("filebrowser.site.urls")),
    url(r'^admin/filebrowser/', site.urls),
    url(r'^clearcache$', scms_clearcache, name='scms-clearcache'),
    url(r'^treerebuild$', scms_treerebuild, name='scms-treerebuild'),
    url(r'^(.*)$', scms_render, name='scms-render'),
    # url(r'^(.*)$', scms_mongo_render, name='scms-render'),
]# + fb_site.urls[0]

