from datetime import datetime, timedelta

from bot.models import Aerodrom, Profile, Rent, Planes

from django.db.models import Q


def aerodrom_available():
    aerodrom_names = Aerodrom.objects.filter(available=True).values_list('nameAerodrom', flat=True)

    return list(aerodrom_names)


# Вспомогательная функция для получения или создания профиля
def get_or_create_profile(user_id, username):
    try:
        profile = Profile.objects.get(external_id=user_id)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(external_id=user_id, name=username)
        print(f"{profile} created user")
    return profile

# Вспомогательная функция для получения или создания профиля
def get_or_create_plane(type_plane):
    try:
        plane = Planes.objects.get(type_plane=type_plane)
    except Planes.DoesNotExist:
        plane = Planes.objects.create(type_plane=type_plane, available=True)
        print(f"{plane} created user")
    return plane


def create_if_doesnt_exist_rent(profile):
    try:
        Rent.objects.get(profile=profile)
    except Rent.DoesNotExist:
        Rent.objects.create(profile=profile)


def delete_rent(profile):
    try:
        Rent.objects.filter(profile=profile).delete()
    except Rent.DoesNotExist:
        pass


def save_rent(dictionary_booking):
    Rent.objects.create(profile=dictionary_booking['profile'], type_plane=dictionary_booking['type_plane'],
                        dateStart=dictionary_booking['dateStart'], timeStart=dictionary_booking['timeStart'],
                        timeEnd=dictionary_booking['timeEnd'], dateEnd=dictionary_booking['dateEnd'])
    print("CREATE BOOKING")


def get_type_available_plane():
    planes = Planes.objects.all()
    planes_list = []
    for plane in planes:
        if plane.available:
            planes_list.append(plane.type_plane)

    if not planes_list:
        return (["Сейчас нет доступного самолёта !"])
    return planes_list


def get_type_available_plane_second():
    planes = Planes.objects.all()
    planes_list = []
    for plane in planes:
        if plane.available:
            planes_list.append(plane.type_plane + "‎")

    if not planes_list:
        return (["Сейчас нет доступного самолёта !"])
    return planes_list


def is_time_slot_available(profile, date_start, time_start, date_end, time_end, type_plane):
    """Проверяет доступность временного слота для конкретной даты, времени и типа самолета."""

    # Преобразуем time_start и time_end в объекты datetime.time
    time_start = datetime.strptime(time_start, "%H:%M").time() if isinstance(time_start, str) else time_start
    time_end = datetime.strptime(time_end, "%H:%M").time() if isinstance(time_end, str) else time_end

    overlapping_bookings = Rent.objects.filter(
        type_plane=type_plane,
        dateStart__lte=date_end,
        dateEnd__gte=date_start,
    ).exclude(
        profile=profile,
        dateStart=date_start,
        timeStart=time_start,
        dateEnd=date_end,
        timeEnd=time_end
    )

    for booking in overlapping_bookings:
        if (
                (booking.dateStart == date_start and booking.timeStart <= time_end and booking.timeEnd >= time_start) or
                (booking.dateEnd == date_end and booking.timeStart <= time_end and booking.timeEnd >= time_start)
        ):
            return False
    return True


def get_unavailable_times(date, type_plane):
    """Возвращает список занятых временных слотов для конкретной даты и типа самолета."""
    bookings = Rent.objects.filter(
        dateStart__lte=date,
        dateEnd__gte=date,
        type_plane=type_plane
    ).values_list('timeStart', 'timeEnd')

    unavailable_times = set()
    for time_start, time_end in bookings:
        current_time = time_start
        while current_time < time_end:
            unavailable_times.add(current_time.strftime("%H:%M"))
            current_time = (datetime.combine(date, current_time) + timedelta(hours=1)).time()

    return unavailable_times

def check_available_rent(profile):
    bookings = Rent.objects.filter(profile=profile)
    counter = 0
    books = []
    if bookings.exists():
        for booking in bookings:
            counter += 1
            booking_details = (
                f"№{counter} {booking.pk}\n"
                f" Дата начала: {booking.dateStart}\n"
                f" Время начала: {booking.timeStart}\n"
                f" Дата окончания: {booking.dateEnd}\n"
                f" Время окончания: {booking.timeEnd}\n"
                f" Тип самолета: {booking.type_plane}\n\n"
            )
            books.append(booking_details)
        print(f"Found {counter} bookings for profile {profile.external_id}.")  # Логируем найденные записи
        return (counter, books)
    else:
        print(f"No active bookings found for profile {profile.external_id}.")  # Логируем отсутствие записей
        return (0, ["Активных бронирований не найдено."])
