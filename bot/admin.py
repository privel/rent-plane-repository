from email.message import Message

from django.contrib import admin

from bot.forms import ProfileForm
from bot.models import Profile, Rent, Planes, Register_flight


# from bot.models import Message


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'name')
    form = ProfileForm


@admin.register(Rent)
class RentAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'type_plane', 'dateStart', 'timeStart', 'dateEnd', 'timeEnd', 'created_at')


@admin.register(Planes)
class PlanesAdmin(admin.ModelAdmin):
    list_display = ('id', 'type_plane', 'available')


@admin.register(Register_flight)
class Register_flightAdmin(admin.ModelAdmin):
    list_display = (
    'id', 'profile', 'type_plane', 'date', 'time', 'refueling', 'hobbs_start', 'aerodrom_start', 'number_of_landings',
    'aerodrom_end', 'hobbs_end', 'commentary')

# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('id', 'profile', 'text', 'created_at')
#     #
# def get_queryset(self, request):
#     return
