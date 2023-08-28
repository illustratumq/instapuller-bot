from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import User, Account, Work, Post, Function, Proxy, Error, BaseForm


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = ('full_name', 'user_id', 'status', 'updated_at')
    list_filter = ('status', )
    search_fields = ('user_id__startswith', 'full_name__startswith')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-updated_at']

    def has_add_permission(self, request):
        return False

    fieldsets = (
        ('Персональна інформація', {
            'fields': ('user_id', 'full_name', 'status')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):

    list_display = ('username', 'password', 'view_user_link', 'status', 'account_id', 'updated_at')
    list_filter = ('status', 'type')
    search_fields = ('username__startswith', 'account_id')
    readonly_fields = ('created_at', 'updated_at', 'account_id')
    ordering = ['-updated_at']
    autocomplete_fields = ('user_id',)

    def view_user_link(self, obj):
        if obj.user_id:
            url = (
                    reverse('admin:instapuller_user_changelist') + f'{obj.user_id.user_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.user_id.full_name)

    view_user_link.short_description = 'Власник'

    fieldsets = (
        ('Основна інформація про акаунт', {
            'fields': ('account_id', 'user_id', 'status', 'type', ('limit', 'free_action'))
        }),
        ('Дані для авторизації', {
            'fields': ('username', 'password', 'auth_key')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'view_customer_link', 'view_executor_link', 'view_user_link', 'status', 'updated_at')
    list_filter = ('status', 'mode')
    search_fields = ('work_id__startswith', 'full_name__startswith')
    readonly_fields = ('created_at', 'updated_at', 'work_id')
    ordering = ['-updated_at']
    autocomplete_fields = ('user_id', 'customer_id', 'executor_id')

    def view_user_link(self, obj):
        if obj.user_id:
            url = (
                    reverse('admin:instapuller_user_changelist') + f'{obj.user_id.user_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.user_id.full_name)

    def view_customer_link(self, obj):
        if obj.customer_id:
            url = (
                    reverse('admin:instapuller_account_changelist') + f'{obj.customer_id.account_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.customer_id.username)

    def view_executor_link(self, obj):
        if obj.executor_id:
            url = (
                    reverse('admin:instapuller_account_changelist') + f'{obj.executor_id.account_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.executor_id.username)

    view_executor_link.short_description = 'Скачування з'
    view_customer_link.short_description = 'Публікація на'
    view_user_link.short_description = 'Власник'

    fieldsets = (
        ('Прив\'язаність завдання', {
            'fields': ('work_id', 'user_id', 'customer_id', 'executor_id')
        }),
        ('Тип та налаштування завдання', {
            'fields': ('status', ('mode', 'limit'), 'mediacount')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('post_id', 'view_customer_link', 'view_executor_link', 'view_user_link', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('post_id__startswith', 'user_id__startswith', 'customer_id__startswith',
                     'executor_id__startswith', 'work_id__startswith')
    readonly_fields = ('created_at', 'updated_at', 'job_id')
    ordering = ['-updated_at', '-customer_id']
    autocomplete_fields = ('user_id', 'customer_id', 'executor_id', 'work_id')

    def view_user_link(self, obj):
        if obj.user_id:
            url = (
                    reverse('admin:instapuller_user_changelist') + f'{obj.user_id.user_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.user_id.full_name)

    def view_customer_link(self, obj):
        if obj.customer_id:
            url = (
                    reverse('admin:instapuller_account_changelist') + f'{obj.customer_id.account_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.customer_id.username)

    def view_executor_link(self, obj):
        if obj.executor_id:
            url = (
                    reverse('admin:instapuller_account_changelist') + f'{obj.executor_id.account_id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.executor_id.username)

    view_executor_link.short_description = 'Скачування з'
    view_customer_link.short_description = 'Публікація на'
    view_user_link.short_description = 'Власник'

    fieldsets = (
        ('Прив\'язаність поста', {
            'fields': ('post_id', 'user_id', 'customer_id', 'executor_id', 'work_id', 'job_id')
        }),
        ('Дані поста', {
            'fields': ('status', 'mediacount', 'caption')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )


@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):

    form = BaseForm

    list_display = ('name', 'description', 'status')
    list_filter = ('status',)
    search_fields = ('name__startswith', )
    readonly_fields = ('created_at', 'updated_at', 'job_id', 'name')
    ordering = ['-updated_at']

    def has_add_permission(self, request):
        return False

    fieldsets = (
        ('Про функцію', {
            'fields': ('name', 'status')
        }),
        ('Додатково', {
            'fields': ('job_id', 'description')
        }),
        ('Періодичність запуску', {
            'fields': ('minutes', 'seconds')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'view_func_link', 'valid', 'updated_at')
    list_filter = ('valid', )
    search_fields = ('host__startswith', 'username__startswith')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-updated_at']
    autocomplete_fields = ('function_id', )

    def view_func_link(self, obj):
        if obj.function_id:
            url = (
                    reverse('admin:instapuller_function_changelist') + f'{obj.function_id.id}/change'
            )
            return format_html('<a href="{}">{}</a>', url, obj.function_id.name)
        else:
            return 'Не обрана'

    view_func_link.short_description = 'Функція'

    fieldsets = (
        ('Прив\'язаність та статус', {
            'fields': ('function_id', 'valid')
        }),
        ('Параметри проксі', {
            'fields': ('type', ('host', 'port'),  'reboot_url')  # ('login', 'password'),
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

@admin.register(Error)
class ErrorAdmin(admin.ModelAdmin):

    list_display = ('name', 'description', 'customer_id', 'updated_at')
    list_filter = ('name',)
    search_fields = ('name__startswith',)
    readonly_fields = ('created_at', 'updated_at', 'name', 'description', 'customer_id',
                       'executor_id', 'technical_id', 'proxy_id', 'work_id', 'screenshot', 'id')
    ordering = ['-updated_at']

    def has_add_permission(self, request):
        return False

    fieldsets = (
        ('Код помикли', {
            'fields': ('name', 'description')
        }),
        ('Залежності', {
            'fields': ('customer_id', 'executor_id', 'technical_id', 'proxy_id', 'work_id', 'screenshot')
        }),
        ('Дата створення та оновлення', {
            'fields': [('updated_at', 'created_at')]
        })
    )

    def has_delete_permission(self, request, obj=None):
        return False

