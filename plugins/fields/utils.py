# coding=utf-8
from django.utils.importlib import import_module

def get_classplugin_from_str(type_str):
    try:
        dot = type_str.rindex('.')
    except ValueError:
        return None
    p_module, p_classname = type_str[:dot], type_str[dot+1:]
    
    try:
        mod = import_module(p_module)
    except ImportError, e:
        return None
    
    try:
        return getattr(mod, p_classname)
    except AttributeError:
        return None
    
