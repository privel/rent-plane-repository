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
        verbose_name = "Профиль в телеграм"


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
        verbose_name = "Rent plane"

