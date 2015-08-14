# coding=utf-8
from scms.plugin_base import SCMSPluginBase
from models import TinyMCE
from django import forms
from django.utils.translation import ugettext_lazy as _
from tinymce.widgets import AdminTinyMCE
from django.utils.safestring import mark_safe
from django.forms.widgets import Textarea


class SCMSTinyMCEWidget(AdminTinyMCE):
    def __init__(self, attrs=None, page_id=None):
        super(SCMSTinyMCEWidget, self).__init__(attrs)
        self.page_id = page_id
        
    def render(self, name, value, attrs=None):
        from django.core import urlresolvers
        fb_url = urlresolvers.reverse('fb_browse', current_app='filebrowser')
        
        # Определяем значение переменной для js-кода, содержащее значение папки страницы по умаолчанию
        from scms.utils import build_page_folder_path
        if self.page_id:
            page_folder_js = build_page_folder_path(self.page_id, isrelative = True) #.replace('/','%5C') В виновс и линукс по-разному, иногда заменять надо, иногда -- нет, лучше не заменять, т.к. так хоть работает в двух ос# делаем замену, чтобы в бредкрамбсах файлброузера отображался путь не 'page/13', а 'page > 13'
        else:
            page_folder_js = ''

        # Определяем значение переменной для js-кода, содержащее значение к папке с файлами, например /media/files
        from filebrowser.settings import DIRECTORY
        from django.conf import settings
        import os 
        files_folder_js = os.path.join(settings.MEDIA_URL, DIRECTORY).replace('/', '\/')
        
        filebrowser_js = u"""
        <script type="text/javascript">
        function djangoTinyBrowser(field_name, url, type, win) {
          page_folder = "_page_folder_js_";
          if (url) {
            // Формируем относительный путь от корня папки с файлами
            var reg_template=/_files_folder_js_(.*)/;  
            arr_res = reg_template.exec(url);
            if (arr_res) {
              // Обрезаем имя файла
              slash_pos = arr_res[1].lastIndexOf("/"); 
              page_folder = arr_res[1].slice(0, slash_pos);
              //page_folder = page_folder.replace("/","%5C"); // В Linux не заменять
            }
            else {
              page_folder = '';
            }
            // Для тестов
            // alert(page_folder);
          }
          
          
          var url = '_fb_url_?pop=2&type=' + type + '&dir=' + page_folder; // pop=2 для того, чтобы соощить файлбровсеру, что вставка просиходит в тини
          tinyMCE.activeEditor.windowManager.open(
            {
              title: "Filebrowser",
              'file': url,
              'width': 820,
              'height': 500,
            },
            {
              'window': win,
              'input': field_name,
              'editor_id': tinyMCE.activeEditor.id
            }
          );
          return false;
        }
        </script>
        """.replace('_page_folder_js_', page_folder_js).replace('_files_folder_js_', files_folder_js).replace('_fb_url_', fb_url)
        
        result = super(SCMSTinyMCEWidget, self).render(name, value, attrs)
        return mark_safe(filebrowser_js + unicode(result).replace('djangoFileBrowser', 'djangoTinyBrowser') )


class TinyMCEPlugin(SCMSPluginBase):
    model = TinyMCE

    def __init__(self, 
                 name, 
                 verbose_name=None, 
                 verbose_name_plural=None, 
                 form=None, 
                 formset=None, 
                 extra=3, 
                 can_order=False, 
                 lang_depended=True, 
                 can_delete=True, 
                 max_num=1, 
                 template = None,
                 filter_type = None,
                 show_weight = False,
                 rows = 40,
                 is_show = True):
        self.rows = rows
        self.is_show = is_show
        super(TinyMCEPlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, filter_type, show_weight)
        
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'body':
            if self.is_show:
                return forms.CharField(label=_("Text"), widget=SCMSTinyMCEWidget({'style': 'width: 100%', 'rows': self.rows}, page_id=kwargs['request'].scms['page'].id), required=False)
            else:
                return forms.CharField(label=_("Text"), widget=Textarea({'style': 'width: 100%', 'rows': self.rows}), required=False)
        return super(TinyMCEPlugin, self).formfield_for_dbfield(db_field, **kwargs)
        
