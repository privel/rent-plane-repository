from datetime import datetime

from django.db import models


class Profile(models.Model):
    external_id = models.PositiveIntegerField(
        verbose_name="ID в телеграм",
        unique=True,
    )

    name = models.TextField(verbose_name="Имя в телеграм")

    def __str__(self):
        return f'#{self.external_id} {self.name}'

    class Meta:
        verbose_name = "Профиль в телеграме"
        verbose_name_plural = "Профили в телеграме"


class Aerodrom(models.Model):
    nameAerodrom = models.CharField(max_length=255)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.nameAerodrom

    class Meta:
        verbose_name = "Аэродром"


class Rent(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.PROTECT)
    type_plane = models.CharField(max_length=255, default="TEST", unique=False)
    dateStart = models.DateField(default=None, null=True)
    timeStart = models.TimeField(default=None, null=True)
    timeEnd = models.TimeField(default=None, null=True)
    dateEnd = models.DateField(default=None, null=True)
    created_at = models.DateTimeField(verbose_name="Время создания записи", auto_now_add=True)

    def __str__(self):
        return f'Rent {self.pk} from {self.profile.name}'

    class Meta:
        verbose_name = "Бронь самолета"
        verbose_name_plural = "Бронь самолётов"


class PlaneManager(models.Manager):
    def available(self):
        return self.filter(available=True)

class Planes(models.Model):
    type_plane = models.CharField(max_length=255, default="Plane 1", verbose_name="Тип")
    available = models.BooleanField(default=True, verbose_name="Доступен")

    objects = PlaneManager()  # Используем новый менеджер

    def __str__(self):
        return f"{self.type_plane if self.available else None}"



    class Meta:
        verbose_name = "Самолёт"
        verbose_name_plural = "Самолёты"

class Register_flight(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.PROTECT, verbose_name="Профиль")
    type_plane = models.ForeignKey(
        Planes,
        on_delete=models.PROTECT,
        verbose_name="Тип",
        limit_choices_to={'available': True}  # Ограничиваем выбор доступных самолётов
    )

    date = models.DateField(default=None, null=True)
    time = models.TimeField(default=None, null=True)

    refueling = models.CharField(max_length=100, verbose_name="Заправка (литры)", default=None)
    hobbs_start = models.CharField(max_length=150, verbose_name="HOBBS начальный", default=None)
    aerodrom_start = models.CharField(max_length=200, verbose_name="Взлёт от куда", default=None)
    number_of_landings = models.PositiveSmallIntegerField(verbose_name="Количество посадок", default=None)
    aerodrom_end = models.CharField(max_length=200, verbose_name="Посадка где", default=None)
    hobbs_end = models.CharField(max_length=150, verbose_name="HOBBS конечный", default=None)
    commentary = models.CharField(max_length=300, verbose_name="Комментарий", default="Нет")

    def __str__(self):
        return f"Регистрация {self.pk} от {self.profile}"

    class Meta:
        verbose_name = 'Регистрация полёта'
        verbose_name_plural = 'Регистрация полётов'