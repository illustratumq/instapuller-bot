from django.contrib import admin
from django.urls import path

admin.site.site_header = 'Адмін панель InstaPullerBot'
admin.site.index_title = 'Головне меню'

urlpatterns = [
    path('admin/', admin.site.urls),
]
