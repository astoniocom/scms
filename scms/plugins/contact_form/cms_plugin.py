# coding=utf-8
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from scms.plugin_base import SCMSPluginBase
from .models import ContactForm, ContactFormHistory
from .forms import FormContactForm

class ContactFormPlugin(SCMSPluginBase):
    template = 'admin/scms/page/edit_inline/tabular.html'
    model = ContactForm
    cfh = None
    
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
                 subject='Отправлено с сайта',
                 sender='noreply@fromsite.com',
                 append_content_func=None,
                 email_path = None,
                 type = 0,
                 show_weight = False): #0-- text, 1 -- html
        self.subject = subject
        self.sender = sender
        self.email_path = email_path
        self.type = type
        self.append_content_func = append_content_func
        filter_type = None
        super(ContactFormPlugin, self).__init__(name, verbose_name, verbose_name_plural, form, formset, extra, can_order, lang_depended, can_delete, max_num, template, filter_type, show_weight)
    
    def modify_page(self, page, request=None, language=None):
        #lang = language and language or get_language()
        fields = getattr(page, self.name, False)
        if not fields:
            return
        
        if request and request.method == 'POST' and ('%s-send' % self.name in request.POST or hasattr(request, 'contact_process')): #hasattr(request, 'contact_process') чтобы принудительно можно было вызвать обработку, например для ajax прверки
            if not hasattr(request, 'contact_processed_form'):
                sent_page = hasattr(request, 'scms_page') and request.scms_page or page
                form =  FormContactForm(request.POST, fields=fields)
                if form.is_valid():
                    message = []
                    for field_name, field in form.fields.items():
                        if field_name == 'captcha':
                            continue
                        if field.label:
                            message.append('%s: %s' % (field.label, form.cleaned_data[field_name]))
                    message.append('%s: %s (%s%s%s)' % (_('Sent from page'), sent_page.title, 'http://', request.META['HTTP_HOST'], request.path))
                    
                    # Если необходимо, добавляем произвольный контент функцией из настроек плагина.
                    if self.append_content_func:
                        message.append(self.append_content_func(request, sent_page, language))
                    
                    if self.type == 0:
                        message = '\r\n\r\n\r\n'.join(message)
                    elif self.type == 1:
                        message = '<br /><br /><br />'.join(message)
                    else:
                        message = ' '.join(message)
    
                    if self.email_path:
                        from scms.models.pagemodel import Page
                        p = Page(id=self.email_path['page']).full_load()
                        emailfield = getattr(p, self.email_path['field'], False)
                        if emailfield:
                            #try:
                                recipients = []
                                for nextemail in emailfield['values'].values():
                                    if nextemail['email']:
                                        recipients.append(str(nextemail['email']))
                                        self.cfh = ContactFormHistory(page=sent_page, alias=request.path, recipient=str(nextemail['email']), body=message, type=self.type)
                                        self.cfh.save()
                                if recipients:
                                    send_mail(self.subject, message, self.sender, recipients)
                            #except:
                            #    pass

                    form.data = {}
                request.contact_processed_form = form # Для того, чтобы небыло двойной обработки, если страница с идентификатором, на которой расположена форма загуржается несколько раз. Но и в тоже время, результат обработки формы остался
            else:
                form = request.contact_processed_form
        else:
            form = FormContactForm(fields=fields)

        # Так как далее происходит переопределение стандартных полей. для совместимости с (full_load из pagemodel) восстанавливаем эти поля.
        setattr(form, 'plugin', self)
        setattr(form, 'type', fields['type'])
        
        setattr(page, self.name, form)
