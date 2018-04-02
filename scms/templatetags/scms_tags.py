# encoding: utf-8
import re, scms, json
from django import template
from django.template import Library, Node
from django.template.loader import get_template
from django import VERSION
 
if VERSION[:3] >= (1, 8, 0):
	from django.template.base import FilterExpression
else:
	from django.template import FilterExpression

from django.template.defaultfilters import stringfilter
from collections import OrderedDict
from importlib import import_module
from django.utils.translation import get_language,  ugettext as _
from django.utils.encoding import smart_str, force_text
from scms.models.pagemodel import Page, MongoManager
from scms.utils import query_str_to_dict, get_query_string, get_mongo
register = Library()

class GetpagesNode(Node):
	def __init__(self, var, params, order=None, page=None, perpage=None):
		self.var = var
		self.params = params
		self.order = order
		self.page = page
		self.perpage = perpage 
	
	def render(self, context):
		# Определение текущей страницы пагинации
		if self.page:
			self.page = self.page.resolve(context, True) # Если отключен режим дебага для шаблонов, то данная строка вызывает исключение при повторной загрузке страницы
			self.page = self.page and int(self.page) or 1
		
		if isinstance(self.order, FilterExpression):
			self.order = self.order.resolve(context, True)
			self.order = self.order and self.order or 'weight'
		elif self.order == None:
			self.order = 'weight'

		filter_vars = {}
		for key, value in self.params.items():
			if key=='GET':
				for get_key, get_value in context['request'].GET.items():
					filter_vars[get_key] = get_value
			elif isinstance(value, FilterExpression):
				new_value = value.resolve(context, True)
				
				if not new_value and value.token == 'page_id': # На случай, если PageNotFound and raist Http404 
					value.token = 0
					
				if key=='parent' and new_value==0: # на случай, если пишенм не parent=None, а parent=0, чтобы конструкции приравнивались, полезно при with
					value.token = None

				filter_vars[key] = new_value and new_value or value.token
			else:
				filter_vars[key] = value
	
		p = Page()
		page_id = 'page_id' in context and context['page_id'] or 0 # На случай, если PageNotFound and raist Http404
		context[self.var] = p.get_pages(context.get('request'), page_id, self.order, self.page, self.perpage, language=None, filter_vars=filter_vars )
			
		return ''
#@register.tag(name="getpages")
def do_getpages(parser, token):
	"""
	Формат тега
	
	Было {% children children for page_id perpage 10 page pathvars.page types catitem %}
	Стало {% getpages pages perpage 10 page pathvars.page order weight params GET=&parent=page_id&type__in=catitem,catsect %}
	"""
	bits = token.contents.split()
	
	var = None
	order = None
	page = None
	perpage = None
	params = None
	
	var_name = None
	for n, bit in enumerate(bits):
		if n is 0:
			continue
		elif n is 1:
			var = bit
			continue
		else:
			if not var_name:
				var_name = bit
			else:
				if var_name == 'order':
					try:
						order = parser.compile_filter(bit)
					except:
						order = bit
				elif var_name == 'page':
					page = parser.compile_filter(bit) # TODO проверка на число  
				elif var_name == 'perpage':
					perpage = int(bit) # TODO проверка на число
				elif var_name == 'params':
					params = query_str_to_dict(bit)
					
					for key, value in params.items():
						params[key] = isinstance(value, str) and parser.compile_filter(str(value)) or value
										
				var_name = None   
	return GetpagesNode(var, params, order, page, perpage)               
do_getpages = register.tag("getpages", do_getpages)

class GetMongoNode(Node):
	def __init__(self, var, params, order=None, page=None, perpage=None):
		self.var = var
		self.params = params
		self.order = order
		self.page = page
		self.perpage = perpage 
	
	def render(self, context):
		# Определение текущей страницы пагинации
		if self.page:
			self.page = self.page.resolve(context, True)
			self.page = self.page and int(self.page) or 1
		
		if isinstance(self.order, FilterExpression):
			self.order = self.order.resolve(context, True)
			self.order = self.order and self.order or 'weight'
		elif self.order == None:
			self.order = 'weight'

		filter_vars = {}
		for key, value in self.params.items():
			if key=='GET':
				for get_key, get_value in context['request'].GET.items():
					filter_vars[get_key] = get_value
			elif isinstance(value, FilterExpression):
				new_value = value.resolve(context, True)
				
				if not new_value and value.token == 'page_id': # На случай, если PageNotFound and raist Http404 
					value.token = 0
					
				if key=='parent' and new_value==0: # на случай, если пишенм не parent=None, а parent=0, чтобы конструкции приравнивались, полезно при with
					value.token = None

				filter_vars[key] = new_value and new_value or value.token
			else:
				filter_vars[key] = value
	
		p = Page()
		page_id = 'page_id' in context and context['page_id'] or 0 # На случай, если PageNotFound and raist Http404
		context[self.var] = p.get_pages(context.get('request'), page_id, self.order, self.page, self.perpage, language=None, filter_vars=filter_vars )
			
		return ''


# Mongo queries
class MongoTag(object):
	pass

class GetMongoNode(Node):
	def __init__(self, bits, collection=None):
		db = get_mongo()
		if not db: 
			return 
		import pymongo
		self.pymongo = pymongo

		var = None
		order = None
		page = None
		perpage = None
		params = None
		self.kwargs = {}
		self.args = bits
		self.query = {}
		self.initial = {
			'query': "", 
			'sort': "weight", 
			'debug': False,
			'show_hidden': False,
			'limit': 1000,
			'from':0,
			'page':1
		}
		self.in_data = {}
		# context = self.context
		try:
			index_as = bits.index('as')
			self.as_var = bits[index_as+1]
			bits = bits[:index_as]
		except ValueError:
			self.as_var = False

		self.bits = bits
		 # self.format_string = format_string

	def get_var(self, val):
		try:
			val = template.Variable(val).resolve(self.context)
			return val
		except template.VariableDoesNotExist:
			return val

	def _parse_query(self, string):

		query = []
		string = string or self.in_data.get('query')
		for either in  string.split("|"):
			params = {}
			for var_data in either.split("&"):
				key, val = var_data.split("=")
				if key.endswith('__lte') or key.endswith('__gte') or key.endswith('__in') or key.endswith('__lt') or key.endswith('__gt'):
					key, method = key.split("__")
					method = "$%s" % method
					variables = []
					try:
						for v in self.get_var(val).split(','):
							v = v.strip()
							try:
								v = int(v)
							except ValueError:
								pass
							variables.append(v)
					except AttributeError:
						variables = self.get_var(val)
					if params.get(key):
						params[key][method] = variables
					else:
						params[key] = {method: variables}
				else:
					params[key] = self.get_var(val)
			if params:
				query.append(params)
		return query

	def parse_query(self, string=None):
		string = string or self.in_data.get('query')
		if string:
			query = self._parse_query(string)

			if query:
				query = {"$or":query}

			if not self.in_data.get('show_hidden') or self.in_data.get('exclude'):
				query["$nor"] = []
			if not self.in_data.get('show_hidden'):
				query['$nor'].append({'state':3, 'hidden': True, 'published':False})

			if self.in_data.get('exclude'):
				exclude = self._parse_query(self.in_data['exlude'])
				for e in exclude:
					query['$nor'].append(e)
						

		return query

	def render(self, context):
				
		self.context = context
		db = get_mongo()
		if not db: 
			return 

		var_name = None
		qarr = []
		for n, bit in enumerate(self.bits):
			if n <= 0:
				continue
			key = bit.split("=")[0]
			data = bit
			if key in self.initial:
				self.initial[key] = self.get_var(bit.split("=")[-1])
			else:
				qarr.append(bit)
		if qarr:
			self.in_data['query'] = "|".join(qarr)

		# Parse query
		# import debug

		query = {}
		self.initial['query'] = query = self.parse_query()
		
		sort = self.initial['sort']
		if self.initial['debug']:
			import debug
		
		# for r in result:
		# 	pass
		if self.as_var:
			# context[self.as_var] = json.dumps(query)
			# context[self.as_var] = as_var = MongoManager(query=query, sort=sort, parent=self)
			context[self.as_var] = as_var = MongoManager(context=context, **self.initial)
			return ''

		return result

@register.tag(name="getmongo")
def getmongo(parser, token):
	"""
	Формат тега
	
	{% getmongo parent=None&type__in=catsect,articles,contact,newssect,page as children %}
	"""
	bits = token.split_contents()
	return GetMongoNode(bits)


class PageloadNode(Node):
	def __init__(self, var, page, language):
		self.var = var
		self.page = page
		self.language = language
	
	def render(self, context):
		page_id = self.page.resolve(context, True)
		
		if self.language:
			language = self.language.resolve(context, True)
			language = language==None and self.language.token or language
			
		else:
			language = None

		request = 'request' in context and context['request'] or None # На случай, если, например raise Http404
		context[self.var] = Page(id=page_id).full_load(request=request, language=language, only_cached=False)
		return ''
	
#@register.tag(name="pageload")
def do_pageload(parser, token):
	bits = token.contents.split()
	
	var = None
	page = None
	language = None

	var_name = None
	for n, bit in enumerate(bits):
		if n is 0:
			continue
		elif n is 1:
			page = parser.compile_filter(bit)
			continue
		else:
			if not var_name:
				var_name = bit
			else:
				if var_name == 'in':
					var = bit
				elif var_name == 'language':
					language = parser.compile_filter(bit) 
					
				var_name = None   
	return PageloadNode(var, page, language)
do_pageload = register.tag("pageload", do_pageload)

class QueryStringNode(Node):
	def __init__(self, param_to_add, param_to_remove):
		self.param_to_add = param_to_add
		self.param_to_remove = param_to_remove
	
	def render(self, context):
		param_to_add = {}
		for key, value in self.param_to_add.items():
			new_key = key
			if isinstance(key, FilterExpression):
				new_key = key.resolve(context, True)
				new_key = new_key==None and key.token or new_key
				
			if isinstance(value, FilterExpression):
				new_value = value.resolve(context, True)
				param_to_add[new_key] = new_value==None and value.token or new_value
			else:
				param_to_add[new_key] = value 
		
		param_to_remove = []
		for value in self.param_to_remove:
			if isinstance(value, FilterExpression):
				new_value = value.resolve(context, True)
				param_to_remove.append(new_value==None and value.token or new_value)
		
		return get_query_string(context['request'].GET, param_to_add, param_to_remove)
	
#@register.tag(name="query_string")
def do_query_string(parser, token):
	"""
	Allows the addition and removal of query string parameters.

	Usage:
	http://www.url.com/{% query_string "param_to_add=value&param_to_add=value" "param_to_remove, params_to_remove" %}
	"""
	bits = token.contents.split()

	param_to_add = {}
	for key, value in query_str_to_dict(bits[1][1:-1]).items():
		new_key = isinstance(key, str) and parser.compile_filter(str(key)) or key
		param_to_add[new_key] = isinstance(value, str) and parser.compile_filter(str(value)) or value

	param_to_remove = []
	for value in bits[2][1:-1].split(','):
		param_to_remove.append( isinstance(value, str) and parser.compile_filter(str(value)) or value ) 

	return QueryStringNode(param_to_add, param_to_remove)               
do_query_string = register.tag("query_string", do_query_string)

class GetFiltersNode(Node):
	def __init__(self, var, page):
		self.var = var
		self.page = page
	
	def render(self, context):
		page_id = self.page.resolve(context, True)
		
		if page_id:
			lang = get_language()
			request = 'request' in context and context['request'] or None # На случай, если, например raise Http404 
			page = Page(id=page_id).full_load(request=request)
			results = OrderedDict()

			# Формируем объект виртуальной страниы-потомка текущей страниы, чтобы можно было определить динамические поля родительских страниц
			vir_page = Page(parent=page, lft=page.lft+1, rght=page.rght-1, tree_id=page.tree_id)

			# Пробегаем все возможные типы контента, которые могут быть потомками для page
			# И получаем все поля этого типа контента, на основании виртуальной страницы vir_page
			# Если в настройках для поля указано, что его можно фильтровать, поле возвращает фильтр
			for content_type in scms.site.get_content_type(page.type).children:
				for field_obj in scms.site.get_content_type(content_type).get_fields(vir_page): # page используется в этой функции, т.к., например, для плагина fields, список возвращаемых полей зависит от страницы
					filter_data = field_obj.get_filters(page, lang, request)
					if filter_data:
						results[field_obj.name] = filter_data
						
			context[self.var] = results
		
		return ''
		
@register.tag(name="getfilters")
def do_getfilters(parser, token):
	bits = token.contents.split()

	page = parser.compile_filter(bits[3])
	var = bits[1]

	return GetFiltersNode(var, page)
#do_getfilters = register.tag("getfilters", do_getfilters)

@register.simple_tag(name="debug")
def debug(value):
	import debug


class ExecpyNode(Node):
	def __init__(self, modulename):
		self.modulename = modulename
	
	def render(self, context):
		# Формируем обращаемся к страницам
		for source in ['%s-%s'%(self.modulename, context['page_id']), self.modulename,]:
			try:
				mod = import_module('pages.' + source)
				#try:
				prepare_func = getattr(mod, 'prepare')
				
				
				result = prepare_func(context['request'], context, '')
				if result:
					return result
				#except AttributeError:
				#    continue
			except ImportError:
				continue        
		return ''
	
#@register.tag(name="execpy")
def do_execpy(parser, token):
	bits = token.contents.split()
	modulename = bits[1]
	return ExecpyNode(modulename)
do_pageload = register.tag("execpy", do_execpy)


def intspace(value):
	"""
	Converts an integer to a string containing commas every three digits.
	For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
	"""
	orig = force_text(value)
	new = re.sub("^(-?\d+)(\d{3})", '\g<1> \g<2>', orig)
	if orig == new:
		return new
	else:
		return intspace(new)
intspace.is_safe = True
register.filter(intspace)

@register.filter()
def split(text, splitter=' '):
	if not text:
		text = ''
	text = text.split(splitter)
	return text

@register.filter()
def pop(arr):
	return arr.pop()

from django.conf import settings

from PIL import Image, ImageDraw, ImageFont
import os
import hashlib

@register.filter()
def debug(obj, *args, **kwargs):
	'''
	Функция debug
	'''
	import debug
	return obj

@register.simple_tag
def txt2img(*args, **kwargs):
	#{% txt2img 'Код.' cp.field_catitem_code.0.body fontsize=14 reload=True bg="#eee" color="#444" format="png" sep="" %}
	sep = kwargs.get('sep', " ")
	text = u"%s" % sep.join(args)
	#text.encode('cp1251')
	#text = text.decode('cp1251')
	fontsize = kwargs.get('fontsize', 14)
	bg = kwargs.get('bg', "#ffffff")
	color = kwargs.get('color', "#000000")
	font = kwargs.get('font', "tahoma.ttf")
	#font = kwargs.get('font', "DejaVuSans.ttf")
	format = kwargs.get('format', "jpeg")
	quality = kwargs.get('quality', "100")
	height = kwargs.get('height', 16)
	img_dir = settings.MEDIA_ROOT + "/txt2img/"
	img_name_temp = text + "-" + bg.strip("#") + "-" + color.strip("#") + "-" + str(fontsize)
	hash = hashlib.sha1(img_name_temp.encode('utf-8')).hexdigest()
	img_subdir = "%s/%s/" % (hash[0:2], hash[2:4])
	img_name = "%s.%s" % (hash, format)
	if not os.path.exists(img_dir + img_subdir): 
		os.makedirs(img_dir + img_subdir)
	if os.path.exists(img_dir + img_subdir + img_name) and not kwargs.get('reload'):
		pass
	else:   
		font_size = fontsize
		fnt = ImageFont.truetype(img_dir + font, int(font_size))
		w, h= fnt.getsize(text)
		img = Image.new('RGBA', (w, height), bg)
		draw = ImageDraw.Draw(img)
		draw.fontmode = "0" 
		draw.text((0,0), text, font=fnt, fill=color)
		img.save(img_dir + img_subdir + img_name, format=format, quality=quality)  
	imgtag = '%stxt2img/%s/%s' % (settings.MEDIA_URL, img_subdir, img_name)
	return imgtag

@register.filter(name='custom_app_label')
@stringfilter
def custom_app_label(value):
	custom_app_labels = {
		'Auth': _('Auth'),
		'Scms': _('Content'),
		'Plugins': _('Plugins'),
		'Sites': _('Sites'),
		'Contact_Form': _('Contact Form'),
		'Tour': _('Tours'),
	}
	return custom_app_labels.get(value, value)