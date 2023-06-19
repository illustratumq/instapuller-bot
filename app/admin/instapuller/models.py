from datetime import datetime

from django.db import models
from django.forms import ModelForm, Textarea


class TimedBaseModel(models.Model):

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата останнього оновлення')


class User(TimedBaseModel):

    class Meta:
        db_table = 'users'
        verbose_name = 'користувач'
        verbose_name_plural = 'користувачі'

    UserStatusEnum = (
        ('ACTIVE', 'Підписка'),
        ('TRIAL', 'Пробний')
    )

    user_id = models.BigIntegerField(primary_key=True, verbose_name='Телеграм ID користувача')
    full_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Ім\'я користувача')
    status = models.CharField(choices=UserStatusEnum, null=False, default='TRIAL', verbose_name='Тарифний план')

    def __str__(self):
        return f'{self.full_name} {self.user_id}'

class Account(TimedBaseModel):

    class Meta:
        db_table = 'accounts'
        verbose_name = 'акаунт'
        verbose_name_plural = 'акаунти'

    AccountTypeEnum = (
        ('TECHNICAL', 'Технічний'),
        ('PARSING', 'Для париснгу'),
        ('POSTING', 'Для публікації')
    )

    AccountStatusEnum = (
        ('ACTIVE', 'Активний'),
        ('BANNED', 'Проблеми зі входом'),
        ('PAUSE', 'На паузі'),
        ('UNPAID', 'Не оплачений'),
    )

    account_id = models.BigAutoField(primary_key=True, verbose_name='ID Акаунту', db_column='account_id')
    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Власник',
                                db_column='user_id')
    username = models.CharField(max_length=255, null=False, verbose_name='Юзернейм')
    password = models.CharField(max_length=255, null=True, blank=True, verbose_name='Пароль',
                                help_text='не потрібний для акаунтів типу "для парсингу"')
    auth_key = models.CharField(max_length=255, null=True, blank=True, verbose_name='Ключ двоетапної перевірки',
                                help_text='без пробілів, не потрібний для акаунтів типу "для парсингу"')
    limit = models.IntegerField(default=25, verbose_name='Ліміт публікацій в день')
    free_action = models.IntegerField(default=25, verbose_name='К-ть вільний дій', help_text='рахується автоматично')
    type = models.CharField(choices=AccountTypeEnum, default='POSTING', null=False, verbose_name='Тип акаунту')
    status = models.CharField(choices=AccountStatusEnum, default='ACTIVE', null=False, verbose_name='Статус акаунту')
    subscript_date = models.DateTimeField(verbose_name='Дата останьої оплати підписки',
                                          null=True, blank=True, editable=True)
    subscript_days = models.IntegerField(default=30, verbose_name='Кількість днів у підписці')

    def __str__(self):
        return f'@{self.username}'


class Work(TimedBaseModel):

    class Meta:
        db_table = 'works'
        verbose_name = 'завдання'
        verbose_name_plural = 'завдання'

    WorkModeEnum = (
        ('ALL', 'Всі пости'),
        ('ONLY_NEW', 'Тільки нові пости'),
        ('ALL_AND_NEW', 'Всі та нові пости'),
        ('LAST_N', 'Останні X постів'),
    )

    WorkStatusEnum = (
        ('ACTIVE', 'Активне'),
        ('DONE',  'Виконане')
    )

    work_id = models.BigAutoField(primary_key=True, verbose_name='ID Завдання')
    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Власник',
                                db_column='user_id')
    mode = models.CharField(choices=WorkModeEnum, null=False, default='LAST_N')
    customer_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='work_customer_id',
                                    verbose_name='Акаунт на який публікуються пости', db_column='customer_id')
    executor_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='work_executor_id',
                                    verbose_name='Акаунт з якого скачуются пости', db_column='executor_id')
    status = models.CharField(choices=WorkStatusEnum, verbose_name='Статус завдання', default='ACTIVE')
    mediacount = models.BigIntegerField(default=0, verbose_name='Кількість постів на акаунті',
                                        help_text='рахується автоматично при парсингу, не рекомендується змінювати')
    limit = models.IntegerField(default=0, verbose_name='X постів для скачування',
                                help_text='Тільки для завдання типу "Останні X постів"')

    def __str__(self):
        return f'Завдання №{self.work_id}'

class Post(TimedBaseModel):

    class Meta:
        db_table = 'posts'
        verbose_name = 'пост'
        verbose_name_plural = 'пости'

    PostStatusEnum = (
        ('ACTIVE', 'Активний'),
        ('PLAN_DOWNLOAD', 'Планується скачування'),
        ('LOADING', 'Завантажується'),
        ('PLAN_PUBLIC', 'Планується публікація'),
        ('WAIT_PUBLIC', 'Очкікує на публікацію'),
        ('DONE', 'Опублікований'),
        ('PAUSE', 'Поставлений на паузу'),
    )

    post_id = models.CharField(max_length=15, primary_key=True, null=False, verbose_name='Інстаграм ID поста')
    user_id = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Власник', db_column='user_id')
    customer_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='post_customer_id',
                                    verbose_name='Акаунт на який публікується пост', db_column='customer_id')
    executor_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='post_executor_id',
                                    verbose_name='Акаунт з якого скачуєтся пост', db_column='executor_id')
    status = models.CharField(choices=PostStatusEnum, default='ACTIVE', null=False, verbose_name='Статус поста')
    caption = models.CharField(max_length=2200, null=True, blank=True, verbose_name='Текст до поста')
    mediacount = models.IntegerField(default=0, verbose_name='Кількість медіа в пості',
                                     help_text='автоматично рахується при скачуванні, не рекомендується редагувати')
    work_id = models.ForeignKey(Work, on_delete=models.SET_NULL, null=True, verbose_name='Завдання',
                                help_text='визначається автоматично, можна редагувати', db_column='work_id',
                                related_name='post_work_id')
    job_id = models.CharField(max_length=40, null=True, editable=False, verbose_name='Job ID',
                              help_text='технічна інформація про заплановану подію (скачування/публікація)')

    def __str__(self):
        return f'Пост {self.post_id}'

class Function(TimedBaseModel):

    class Meta:
        db_table = 'functions'
        verbose_name = 'функція'
        verbose_name_plural = 'функції'

    FunctionStatusEnum = (
        ('ACTIVE', 'Активна'),
        ('PAUSED', 'Пауза'),
    )

    id = models.AutoField(primary_key=True, verbose_name='ID Функції')
    tag = models.CharField(max_length=50, null=False, unique=True, editable=False)
    name = models.CharField(max_length=50, null=False, verbose_name='Назва', editable=False)
    description = models.CharField(max_length=510, null=False, verbose_name='Опис')
    status = models.CharField(choices=FunctionStatusEnum, default='PAUSED', null=False, verbose_name='Статус виконання',
                              help_text='змініть для того щоб зупинити або запустити виконання функції')
    minutes = models.IntegerField(default=1, verbose_name='Хвилини', help_text='період активації функції')
    seconds = models.IntegerField(default=0, verbose_name='Секунди',
                                  help_text='період активації функції, додаються до хвилин')
    job_id = models.CharField(max_length=40, null=True, editable=False, verbose_name='Job ID',
                              help_text='технічна інформація про функцію')

    def __str__(self):
        return f'Функція {self.name}'

class Proxy(TimedBaseModel):

    class Meta:
        db_table = 'proxies'
        verbose_name = 'проксі'
        verbose_name_plural = 'проксі'

    ValidStatusEnum = (
        (True, 'Працює'),
        (False, 'Не працює')
    )

    id = models.AutoField(primary_key=True, verbose_name='ID Проксі', db_column='id')
    function_id = models.ForeignKey(Function, on_delete=models.SET_NULL, null=True, verbose_name='Функція',
                                    help_text='оберіть в якій функції буде використовуватись проксі',
                                    related_name='prox_function_id', db_column='function_id')
    host = models.CharField(max_length=100, null=False, verbose_name='Хост')
    port = models.CharField(max_length=10, null=False, verbose_name='Порт')
    type = models.CharField(max_length=100, null=False, verbose_name='Тип',
                            help_text='доступні варіанти socks5, https, http')
    login = models.CharField(max_length=100, null=True, blank=True, verbose_name='Юзернейм',
                             help_text='для проксі з авторизацією')
    password = models.CharField(max_length=100, null=True, blank=True, verbose_name='Пароль',
                                help_text='для проксі з авторизацією')
    valid = models.BooleanField(choices=ValidStatusEnum, default=False, verbose_name='Статус')
    reboot_url = models.CharField(max_length=255, null=True, verbose_name='Посилання на перезавантаженя', blank=True)
    last_using_date = models.DateTimeField(default=datetime.now(), verbose_name='Дата останнього використання',
                                           null=False)

    def __str__(self):
        return f'Проксі {self.host}:{self.port}'

class Error(TimedBaseModel):

    class Meta:
        db_table = 'errors'
        verbose_name = 'помилка'
        verbose_name_plural = 'помиллки'

    id = models.BigAutoField(primary_key=True, verbose_name='ID Помилки')
    name = models.CharField(max_length=150, null=False, verbose_name='Джерело')
    description = models.CharField(null=False, verbose_name='Опис помилки')
    job_id = models.CharField(max_length=40, null=True, editable=False, verbose_name='Job ID',
                              help_text='технічна інформація про роботу в якій виникла помилка')
    post_id = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, verbose_name='Пост', db_column='post_id')
    customer_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='err_customer_id',
                                    verbose_name='Акаунт на який публікується пост', db_column='customer_id')
    executor_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='err_executor_id',
                                    verbose_name='Акаунт з якого скачуєтся пост', db_column='executor_id')
    technical_id = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True,
                                     verbose_name='Акаунт який виконував технічну роботу', db_column='technical_id')
    work_id = models.ForeignKey(Work, on_delete=models.SET_NULL, null=True, verbose_name='Завдання',
                                db_column='work_id')
    proxy_id = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, verbose_name='Проксі',
                                 db_column='proxy_id')
    screenshot = models.CharField(max_length=255, null=True, verbose_name='Скріншот')


class BaseForm(ModelForm):
    class Meta:
        fields = '__all__'

        widgets = {
            'description': Textarea(attrs={'cols': 70, 'rows': 5}),
            'caption': Textarea(attrs={'cols': 50, 'rows': 5})
        }
