# coding=utf-8
from django.conf import settings
from i18n import get_default_language
import os
from django.utils.safestring import mark_safe
from django.utils.http import urlquote
from django.core.exceptions import FieldError
from django.utils.encoding import iri_to_uri
from urllib import quote

def get_language_from_request(request, current_page=None):
	#from scms.models import Page
	"""
	Return the most obvious language according the request
	"""
	# import debug
	language = request.GET.get('language') or request.POST.get('language')

	if language:
		if not language in dict(settings.SCMS_LANGUAGES).keys():
			language = None
		
	if language is None:
		language = getattr(request, 'LANGUAGE_CODE')
		
	if language:
		if not language in dict(settings.SCMS_LANGUAGES).keys():
			language = None

	if language is None:
		language = get_default_language()

	return language
		   
def build_page_folder_path(id, isrelative = False):
	# from filebrowser.settings import DIRECTORY, MEDIA_ROOT
	relative = 'page/%s/' % id
	# absolute = os.path.join(MEDIA_ROOT, DIRECTORY, relative)
	absolute = os.path.join(settings.MEDIA_ROOT, relative)

	return isrelative and relative or absolute


def qs_is_able_param(model, param, value):
	try:
		tmp_qs = model.objects.filter(**{param: value})
		return True
	except FieldError:
		return False
			
def queryset_from_dict(qs, get_or_post, params_prefix=None, params_exclude=(), params_use=() ):
	"""
	Функция изменения QuerySet 'qs' на основании словаря переменных из POST или GET запроса 'get_or_post'.
	params_prefix -- если установлен, будут обрабатываться только те переменные, который начинаются с этого префикса
	params_exclude -- если установлен этот параметр, переменные с ним учитываться не будут.
	params_use -- если установлен этот параметр, будут использоваться только те параметры, которые есть в этом списке.
	 
	"""
	from django.utils.encoding import smart_str
	

	exclude_params = {}
	
	# Сворачиваем аргументы с тремя нижними подчеркиваниями, типа taxonomy__terms__and___field_size
	temp_dict = {}
	for key, value in get_or_post.items():
		if key in settings.SCMS_QUERYSET_FROM_DICT_IGNORE_VARS or value=='': # value='' на случай value=&value2=ss
			continue
		
		if not key.find('___') == -1:
			newkey = key.split('___')[0]
			temp_dict[newkey] = temp_dict.has_key(newkey) and '%s,%s' % (temp_dict[newkey],value) or value 
		else:
			temp_dict[key] = value
	lookup_param = {}
	for key, value in temp_dict.items():
		
		key = smart_str(key) # на случаай, если key в каком-нибудь юникоде преобразовываем в простую строку
		#key = smart_str(key)

		if params_prefix:
			if key.startswith(params_prefix):
				key = key[len(params_prefix):] #TODO key без префикс
			else:
				continue #иначе переменную не обрабатываем

		if (params_exclude and key in params_exclude) or (params_use and key not in params_use):
			continue

		if key.endswith('__in'):
			value = smart_str(value)
			lookup_param[key] = value.split(',')
		elif key.endswith('__notin'):
			value = smart_str(value)
			key = key.replace('__notin', '__in')
			exclude_params[key] = value.split(',')
		elif key.endswith('__and'):
			value = smart_str(value)
			real_key = key[:-5]
			sub_qs = None
			for value in value.split(','):
				if not value or not qs_is_able_param(qs.model, real_key, value): # На случай запятой в конце или ,,
					continue
				subfilters = {}
				subfilters[real_key] = value
				if sub_qs is not None:
					subfilters['pk__in'] = sub_qs
				sub_qs = qs.model.objects.filter(**subfilters)
			
			if sub_qs is not None: # Т.к. может быть просто пустой результат запроса, а может быть Ноне
				qs = qs.filter(pk__in=sub_qs)
		else:
			if qs_is_able_param(qs.model, key, value):
				lookup_param[key] = value

	qs = qs.filter(**lookup_param)

	if exclude_params:
		qs = qs.exclude(**exclude_params)
	return qs
	#except:
	#    pass    
	

def get_query_string(p, new_params=None, remove=None, addq=True):
	"""
	Add and remove query parameters. From `django.contrib.admin`.
	"""
	p = p.copy()
	if new_params is None: new_params = {}
	if remove is None: remove = []
	for r in remove:
		for k in p.keys():
			#if k.startswith(r):
			if k == r:
				del p[k]
	for k, v in new_params.items():
		if k in p and not v:
			del p[k]
		elif v:
			p[k] = v
	
	for k, v in p.items():
		if isinstance(v, unicode):
			p[k] = v
		else:
			p[k] = quote(str(v)) # Конвертируем символы в url формат
				
	result = '&'.join([u'%s=%s' % (k, v) for k, v in p.items()]).replace(' ', '%20')
	result = (addq and result) and '?' + result or result
	return result and mark_safe(result) or ''

def build_array_str(str_in='', add=[], remove=[]):
	"""
	Функция формирования из строки вида 1,4,7 строку вида 1,3,5 
	при условии, если add = [3,5] и remove = [7]
	"""
	# Создаем список существующих значений + добавляемых значений
	list = str_in.split(',') + [str(k) for k in add]

	result = [] 
	# Создаем список значений, без их дубликатов на основании исписка list без элементов из remove и без пустых элементов 
	for value in [value for value in list if value not in [str(k) for k in remove] and value]:
		if result.count(value) == 0:
			result.append(value)

	return ','.join(result)


def query_str_to_dict(ext_params_str):
	result = {}
	# Формирование дополнительных полей
	if ext_params_str:
		params = ext_params_str.split('&')
		for param in params:
			key, value = param.split('=')
			if key and value:
				try:
					value = int(value)
				except ValueError:
					if value=='True':
						value=True
					elif value=='False':
						value=False
					elif value=='None':
						value=None                        
				#строка есть строка
				key = str(key)
				result[key] = value
	return result

def get_destination(request):
	destination = request.META['PATH_INFO']
	if request.META['QUERY_STRING']:
		destination += '?%s' % request.META['QUERY_STRING']
	return urlquote(destination)


def pluginsubqs_to_str(field, subqs):
	subqs = subqs.extra(select={field:field}, where=["page_id = `scms_page`.`id`"])[:1]
	subqs.query.default_cols = False
	return str(subqs.query)

def get_mongo():
	'''
	Return mongo db if it's was set
	'''
	MONGODB = settings.DATABASES.get('mongodb')
	if not MONGODB or not MONGODB['ACTIVE']:
		return
	from pymongo import MongoClient
	client = MongoClient()
	db = client[MONGODB['DB']]
	return db
