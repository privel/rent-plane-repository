from django.db import models

class Profile(models.Model):
    external_id = models.PositiveIntegerField(
        verbose_name="ID person in TG",
        unique = True,
    )

    name = models.TextField(verbose_name="Name TG")

    def __str__(self):
        return f'#{self.external_id} {self.name}'

    class Meta:
        verbose_name = "TG Profile"


class Message(models.Model):
    profile = models.ForeignKey(
        to ='bot.Profile',
        verbose_name='TG Profile',
        on_delete=models.PROTECT,
    )
    text = models.TextField(verbose_name="Text TG")
    created_at = models.DateTimeField(verbose_name="Time of receipt",auto_now_add=True)

    def __str__(self):
        return f'message {self.pk} from {self.profile}'

    class Meta:
        verbose_name = "TG Mesasge"
        verbose_name_plural = "TG Mesasges"