from django.contrib import admin
from . models import Member, CustomSession

# Register your models here.
admin.site.register(Member)
admin.site.register(CustomSession)
