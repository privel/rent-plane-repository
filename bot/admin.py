from email.message import Message

from django.contrib import admin

from bot.forms import ProfileForm
from bot.models import Profile, Rent
from bot.models import Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'name')
    form = ProfileForm

@admin.register(Rent)
class RentAdmin(admin.ModelAdmin):
    list_display = ('id','profile','aerodrom', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'text', 'created_at')
    #
    # def get_queryset(self, request):
    #     return
