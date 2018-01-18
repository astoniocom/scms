import re
from django.utils.cache import patch_vary_headers
from django.utils import translation
from django.conf import settings
from scms.utils.i18n import get_default_language

SUB = re.compile(r'<a([^>]+)href="/(?!(%s|%s|%s))([^"]*)"([^>]*)>' % (
    "|".join(map(lambda l: l[0] + "/" , settings.SCMS_LANGUAGES)),
    settings.MEDIA_URL[1:],
    settings.STATIC_URL[1:]
))

SUB2 = re.compile(r'<form([^>]+)action="/(?!(%s|%s|%s))([^"]*)"([^>]*)>' % (
    "|".join(map(lambda l: l[0] + "/" , settings.SCMS_LANGUAGES)),
     settings.MEDIA_URL[1:],
     settings.STATIC_URL[1:]
))

SUPPORTED = dict(settings.SCMS_LANGUAGES)

START_SUB = re.compile(r"^/(%s)/.*" % "|".join(map(lambda l: l[0], settings.SCMS_LANGUAGES)))

def has_lang_prefix(path):
    check = START_SUB.match(path)
    if check is not None:
        return check.group(1)
    else:
        return False

class MultilingualURLMiddleware:
    def get_language_from_request (self,request):
        lang = None
        changed = False
        prefix = has_lang_prefix(request.path_info)
        if prefix:
            request.path = "/" + "/".join(request.path.split("/")[2:])
            request.path_info = "/" + "/".join(request.path_info.split("/")[2:]) 
            t = prefix
            if t in SUPPORTED:
                lang = t
                #if hasattr(request, "session"):
                #    request.session["django_language"] = lang
                #else:
                #    request.set_cookie("django_language", lang)
                changed = True
        #else:
        #    lang = translation.get_language_from_request(request)
        #if not changed:
            #if hasattr(request, "session"):
            #    lang = request.session.get("django_language", None)
            #    if lang in SUPPORTED and lang is not None:
            #        return lang
            #elif "django_language" in request.COOKIES.keys():
            #    lang = request.COOKIES.get("django_language", None)
            #    if lang in SUPPORTED and lang is not None:
            #        return lang
            #if not lang:
            #    lang = translation.get_language_from_request(request)
        if not lang:
            lang = get_default_language()
        return lang
    
    def process_request(self, request):
        language = self.get_language_from_request(request)
        translation.activate(language)
        dd = translation.get_language()
        request.LANGUAGE_CODE = language #translation.get_language()
        #w=1/0

    def process_response(self, request, response):
        patch_vary_headers(response, ("Accept-Language",))
        translation.deactivate()
        path = unicode(request.path)
        if not path.startswith(settings.MEDIA_URL) and \
                not path.startswith(settings.STATIC_URL) and \
                response.status_code == 200 and \
                response._headers['content-type'][1].split(';')[0] == "text/html":
            try:
                decoded_response = response.content.decode('utf-8')
            except UnicodeDecodeError:
                decoded_response = response.content
            response.content = SUB.sub(r'<a\1href="/%s/\3"\4>' % request.LANGUAGE_CODE, decoded_response)
            response.content = SUB2.sub(r'<form\1action="/%s/\3"\4>' % request.LANGUAGE_CODE, decoded_response)
        if (response.status_code == 301 or response.status_code == 302 ):
            location = response._headers['location']
            prefix = has_lang_prefix(location[1])
            if not prefix and location[1].startswith("/") and \
                not request.LANGUAGE_CODE == get_default_language() and \
                not location[1].startswith(settings.MEDIA_URL) and \
                not location[1].startswith(settings.STATIC_URL):
                response._headers['location'] = (location[0], "/%s%s" % (request.LANGUAGE_CODE, location[1]))
        return response
