from django.conf.urls import patterns, include, url
from scms.views import scms_render, scms_clearcache, scms_treerebuild

urlpatterns = patterns('',
    url(r'^clearcache$', scms_clearcache, name='scms-clearcache'),
    url(r'^treerebuild$', scms_treerebuild, name='scms-treerebuild'),
    url(r'^(.*)$', scms_render, name='scms-render'),
)

