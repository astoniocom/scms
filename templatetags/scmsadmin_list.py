#encoding: utf-8
from django.template import Library
from django.contrib.admin.templatetags.admin_list import result_list

register = Library()
result_list = register.inclusion_tag("admin/scms/page/change_list_results.html")(result_list)