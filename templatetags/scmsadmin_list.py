#encoding: utf-8
from django import template
from django.conf import settings
from collections import OrderedDict
from django.template import Library
from django.contrib.admin.templatetags.admin_list import result_list
from django import template
from django.template.defaultfilters import stringfilter

register = Library()

result_list = register.inclusion_tag("admin/scms/page/change_list_results.html")(result_list)

register = template.Library()

@register.filter(name='custom_app_label')
@stringfilter
def custom_app_label(value):
    custom_app_labels = {
        'Auth': 'Полномочия',
        'Parameters': 'Параметры',
        'Taxonomy': 'Определения',
        'Scms': 'Структура',
        'Plugins': 'Дополнительно',
        'Transporter': 'Рассписание маршруток',
        'Tour': 'Каталог туров',
        'Sites': 'Сайты',
        'Contact_Form': 'Форма связи',
        'Orders': 'Заказы',
        'Price': 'Прайс',
        'Uplad price': 'Загрузка прайса',
    }
    return custom_app_labels.get(value, value)

# from http://www.djangosnippets.org/snippets/1937/
def register_render_tag(renderer):
    """
    Decorator that creates a template tag using the given renderer as the 
    render function for the template tag node - the render function takes two 
    arguments - the template context and the tag token
    """
    def tag(parser, token):
        class TagNode(template.Node):
            def render(self, context):
                return renderer(context, token)
        return TagNode()
    for copy_attr in ("__dict__", "__doc__", "__name__"):
        setattr(tag, copy_attr, getattr(renderer, copy_attr))
    return register.tag(tag)

@register_render_tag
def admin_reorder(context, token):
    """
    Called in admin/base_site.html template override and applies custom ordering
    of apps/models defined by settings.ADMIN_REORDER
    """
    # sort key function - use index of item in order if exists, otherwise item
    sort = lambda order, item: (order.index(item), "") if item in order else (
        len(order), item)
    if "app_list" in context:
        # sort the app list
        try:
  		      order = OrderedDict(settings.ADMIN_REORDER)
        except AttributeError:
        	return ""
        else:
	        context["app_list"].sort(key=lambda app: sort(order.keys(),
	            app["app_url"].strip("/").split("/")[-1]))
	        for i, app in enumerate(context["app_list"]):
	            # sort the model list for each app
	            app_name = app["app_url"].strip("/").split("/")[-1]
	            if not app_name:
	                app_name = app["name"].lower()
	            model_order = [m.lower() for m in order.get(app_name, [])]
	            context["app_list"][i]["models"].sort(key=lambda model:
	            sort(model_order, model["admin_url"].strip("/").split("/")[-1]))
    return ""