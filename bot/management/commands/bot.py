import logging
import time
from datetime import datetime, timedelta
from pyexpat.errors import messages

import pytz
import telebot

from telebot import types
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram_bot_calendar import DetailedTelegramCalendar

from bot.management.commands.dep.commands import aerodrom_available, get_or_create_profile, get_type_available_plane, \
    is_time_slot_available, get_unavailable_times, check_available_rent, get_type_available_plane_second, \
    get_or_create_plane
from bot.management.commands.dep.date.date_command import DateSelectionCommand
from bot.management.commands.storage import STATE_MAIN_MENU, STATE_BOOK_CHOOSE_PLANE, STATE_BOOK_CHOOSE_DATE_ON_FLY, \
    STATE_REGISTER_CHOOSE_AERODROM, STATE_SETTINGS, STATE_BOOK, user_state_stack, \
    user_booking, user_date_selection, available_booking_time, STATE_CHECK_ACTIVE_BOOKING, STATE_REGISTER_CHOOSE_DATE, \
    flight_data, STATE_REGISTER_FLIGHT_DETAILS, STATE_REGISTER_FLIGHT_INIT, current_date, user_counters, user_time, \
    user_liters, STATE_REGISTER_CHOOSE_TIME, STATE_REGISTER_CHOOSE_LITERS, STATE_REGISTER_START_HOBBS, \
    STATE_REGISTER_COUNT_LANDING, user_count_of_landing, STATE_REGISTER_CHOOSE_AERODROM_LANDING, \
    STATE_REGISTER_END_HOBBS, STATE_REGISTER_COMMENT, STATE_REGISTER_COMMENT123, STATE_REGISTER_FLIGHT_AUTO
from bot.models import Rent, Register_flight, Planes

bot = telebot.TeleBot(settings.TOKEN)


def select_time(message):
    chosen_date = user_booking.get("dateStart")  # Используем выбранную дату для бронирования
    type_plane = user_booking.get("type_plane")  # Используем выбранный тип самолета

    if not chosen_date or not type_plane:
        bot.send_message(message.chat.id, "Выберите дату и тип самолета сначала.")
        return

    unavailable_times = get_unavailable_times(chosen_date, type_plane)
    available_times = [time for time in available_booking_time if time not in unavailable_times]

    # Создаем клавиатуру с оставшимися доступными временами
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for time in available_times:
        keyboard.add(time)

    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        "Выберите доступное время полета:",
        reply_markup=keyboard
    )


date_selection_command = DateSelectionCommand(bot, select_time)


def push_user_state(user_id, state):
    if user_id not in user_state_stack:
        user_state_stack[user_id] = []
    if state not in user_state_stack[user_id]:
        user_state_stack[user_id].append(state)

    print(f"\n [DEBUG] PUSH: {user_id} -> {state} (stack: {user_state_stack[user_id]})")


def pop_user_state(user_id):
    if user_id in user_state_stack and user_state_stack[user_id]:
        removed_state = user_state_stack[user_id].pop()
        print(f"[DEBUG] POP: {user_id} <- {removed_state} (stack: {user_state_stack[user_id]})")
    return user_state_stack[user_id][-1] if user_state_stack[user_id] else STATE_MAIN_MENU


def get_current_user_state(user_id):
    return user_state_stack[user_id][-1] if user_id in user_state_stack and user_state_stack[
        user_id] else STATE_MAIN_MENU


# Декоратор для логирования ошибок
def log_error(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = f'Error: {e}'
            print(error_message)
            raise e

    return inner


@bot.message_handler(
    func=lambda message: message.text in available_booking_time
)
def handle_time_selection(message):
    current_time_type = user_date_selection.get(message.chat.id)

    if current_time_type == "timeStart":
        user_booking["timeStart"] = message.text
        bot.send_message(
            message.chat.id,
            f"Вы выбрали время начала {message.text}.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # Теперь выводим доступные слоты для времени окончания
        date_selection_command.show_calendar(message.chat.id, "dateEnd")

    elif current_time_type == "timeEnd":
        user_booking["timeEnd"] = message.text
        bot.send_message(
            message.chat.id,
            f"Вы выбрали время окончания {message.text}."
        )
        finalize_booking(message.chat.id, message)


def finalize_booking(chat_id, message):
    """Проверка доступности и завершение бронирования"""
    profile = user_booking.get("profile")
    date_start = user_booking.get("dateStart")
    time_start = user_booking.get("timeStart")
    date_end = user_booking.get("dateEnd")
    time_end = user_booking.get("timeEnd")
    type_plane = user_booking.get("type_plane")

    bookings = Rent.objects.filter(profile=profile)

    if True:
        if (bookings.exists() and bookings.all().count() < 3) or not bookings.exists():
            # Проверка доступности слота с учетом типа самолета и временных пересечений
            if is_time_slot_available(profile, date_start, time_start, date_end, time_end, type_plane):
                Rent.objects.create(
                    profile=profile,
                    type_plane=type_plane,
                    dateStart=date_start,
                    timeStart=time_start,
                    dateEnd=date_end,
                    timeEnd=time_end
                )
                bot.send_message(chat_id, "Бронирование завершено!")
                print(f"Booking saved: {user_booking}")
            else:
                bot.send_message(chat_id,
                                 "Выбранное время для этого типа самолета уже занято. Пожалуйста, выберите другой интервал или самолет.")
        else:
            bot.send_message(chat_id, "Слишком много брони у одного аккаунта!")

    # Очищаем данные после завершения
    user_booking.clear()
    show_main_menu(message)


@log_error
@bot.message_handler(commands=['start'])
def start_command(message):
    push_user_state(message.from_user.id, STATE_MAIN_MENU)
    show_main_menu(message)

    profile = get_or_create_profile(message.from_user.id, message.from_user.username)

    user_booking['profile'] = profile

    # create_if_doesnt_exist_rent(profile)


def show_main_menu(message):
    # Очищаем стек состояний, чтобы пользователь был точно на главном экране
    user_state_stack[message.from_user.id] = [STATE_MAIN_MENU]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Забронировать", "Настройки")
    keyboard.add("Регистрация полёта")
    keyboard.add("Проверить активные брони")
    bot.send_message(message.chat.id, "Главное меню: Выберите операцию", reply_markup=keyboard)

    get_type_available_plane()


@bot.message_handler(func=lambda message: message.text == "Забронировать")
def handle_book(message):
    push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_PLANE)

    # profile = get_or_create_profile(message.from_user.id, message.from_user.username)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in get_type_available_plane():
        keyboard.add(i)

    keyboard.add("Отмена")
    bot.send_message(
        message.chat.id,
        "Вы выбрали 'Забронировать'. Процесс бронирования начат.\nВыберите самолёт\nНажмите 'Назад', чтобы вернуться.",
        reply_markup=keyboard
    )


# @bot.message_handler(func=lambda message: message.text in ["Самолёт 1", "Самолёт 2"])
@bot.message_handler(func=lambda message: message.text in (
        get_type_available_plane() if get_type_available_plane() != ["Сейчас нет доступного самолёта !"] else [
            'super random field oi oi oi Butcher ']))
def handle_book_choose_plane(message):
    push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_DATE_ON_FLY)

    # profile = get_or_create_profile(message.from_user.id, message.from_user.username)

    chosen_plane = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        f"Вы выбрали {chosen_plane}. Выбор сохранен.\nТеперь выберите дату полёта",
        reply_markup=keyboard
    )

    # Rent.objects.filter(profile=profile).update(type_plane=chosen_plane)
    user_booking['type_plane'] = chosen_plane
    print(user_booking)
    date_selection_command.show_calendar(message.chat.id, "dateStart")


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def handle_calendar_selection_dateStart(call):
    profile = get_or_create_profile(call.message.chat.id, call.message.chat.username)
    date_selection_command.handle_calendar_selection(call, profile)


def start_calendar(message):
    """Начинает процесс выбора даты, показывая календарь"""
    push_user_state(message.from_user.id, STATE_REGISTER_CHOOSE_DATE)

    year = current_date.year
    month = current_date.month
    markup = generate_calendar(year, month)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Назад")
    bot.send_message(message.chat.id, f"Теперь выберите дату:", reply_markup=keyboard)
    bot.send_message(message.chat.id, f"{year}-{month:02}", reply_markup=markup)


def generate_calendar(year, month):
    """Генерирует календарь на основе заданного года и месяца, выравнивая дни недели"""
    markup = types.InlineKeyboardMarkup()

    # Название месяца и навигация
    row = [
        types.InlineKeyboardButton("<<", callback_data=f"change_month {year} {month - 1}"),
        types.InlineKeyboardButton(f"{year}-{month:02}", callback_data="ignore"),
        types.InlineKeyboardButton(">>", callback_data=f"change_month {year} {month + 1}")
    ]
    markup.row(*row)

    # Дни недели
    days_row = [types.InlineKeyboardButton(day, callback_data="ignore") for day in
                ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]]
    markup.row(*days_row)

    # Дни месяца с выравниванием
    first_day = datetime(year, month, 1)
    start_day = first_day.weekday()  # Определяем, с какого дня недели начинается месяц
    days_in_month = (first_day.replace(month=month % 12 + 1, day=1) - timedelta(days=1)).day

    # Пустые кнопки до первого дня месяца
    days = [types.InlineKeyboardButton(" ", callback_data="ignore")] * ((start_day + 1) % 7)

    # Кнопки с днями месяца
    for day in range(1, days_in_month + 1):
        days.append(types.InlineKeyboardButton(str(day), callback_data=f"select_date {year} {month} {day}"))
        if len(days) % 7 == 0:
            markup.row(*days)
            days = []
    if days:
        markup.row(*days)

    # Кнопка назад
    # markup.row(types.InlineKeyboardButton("Назад", callback_data="back_to_menu"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith("change_month"))
def change_month(call):
    """Обработчик изменения месяца"""
    try:
        _, year, month = call.data.split()
        year, month = int(year), int(month)
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        markup = generate_calendar(year, month)
        bot.edit_message_text(f"Выберите дату: {year}-{month:02}", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
    except ValueError:
        bot.answer_callback_query(call.id, "Ошибка при обработке данных. Попробуйте снова.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("select_date"))
def select_date(call):
    """Обработчик выбора конкретной даты"""
    try:
        _, year, month, day = call.data.split()
        year, month, day = int(year), int(month), int(day)
        selected_date = datetime(year, month, day).date()
        bot.edit_message_text(f"Вы выбрали дату: {selected_date}", call.message.chat.id, call.message.message_id)
        flight_data[call.message.chat.id]['date'] = selected_date

        select_time_register(call.message)


    except ValueError:
        bot.answer_callback_query(call.id, "Ошибка при обработке выбранной даты. Попробуйте снова.")


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    """Обработчик для кнопки 'Назад'"""
    bot.edit_message_text("Вы вернулись в меню.", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def ignore_callback(call):
    """Игнорирует нажатия на дни недели и прочие элементы интерфейса"""
    pass


# Обработчик для команды "Регистрация полёта"
@bot.message_handler(func=lambda message: message.text == "Регистрация полёта")
def start_register_flight(message):
    user_id = message.from_user.id
    push_user_state(user_id, STATE_REGISTER_FLIGHT_INIT)
    profile = get_or_create_profile(user_id, message.from_user.username)

    # Инициализируем flight_data[user_id] как словарь, если он не существует
    if user_id not in flight_data:
        flight_data[user_id] = {}

    # Добавляем профиль в данные полета
    flight_data[user_id]['profile'] = profile

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for plane in get_type_available_plane_second():
        keyboard.add(plane)
    keyboard.add("Отмена")

    bot.send_message(message.chat.id, "Выберите тип самолёта для регистрации полёта:", reply_markup=keyboard)


# Обработчик для выбора самолёта
@bot.message_handler(func=lambda message: message.text in get_type_available_plane_second())
def handle_plane_selection(message):
    user_id = message.from_user.id
    current_state = get_current_user_state(user_id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Заполнить дату и время")
    keyboard.add("Автозаполнение даты и времени")
    keyboard.add("Назад")
    flight_data[message.from_user.id]['type_plane'] = get_or_create_plane(message.text[:-1])

    push_user_state(user_id, STATE_REGISTER_FLIGHT_DETAILS)
    bot.send_message(message.chat.id, f"Вы выбрали тип: {message.text[:-1]} \n"
                                      f"", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text in ["Заполнить дату", "Заполнить в ручную"])
def handle_edit_date(message):
    push_user_state(message.chat.id, STATE_REGISTER_FLIGHT_AUTO)
    start_calendar(message)


@bot.message_handler(func=lambda message: message.text == "Автозаполнение даты и времени")
def handle_auto_date(message):
    selected_date = datetime(current_date.year, current_date.month, current_date.day).date()

    moscow_tz = pytz.timezone('Europe/Moscow')
    c = datetime.now(moscow_tz)
    time_now = c.strftime('%H:%M')

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Подтвердить")
    keyboard.add("Заполнить в ручную")
    keyboard.add("Назад")

    bot.send_message(message.chat.id, f"Автозаполнение даты: {selected_date} \n"
                                      f" Время: {time_now} \n"
                                      f"Подтвердите дату и время", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Подтвердить")
def handle_aproved_date_auto(message):
    selected_date = datetime(current_date.year, current_date.month, current_date.day).date()
    moscow_tz = pytz.timezone('Europe/Moscow')
    c = datetime.now(moscow_tz)
    time_now = c.strftime('%H:%M')
    flight_data[message.chat.id]['date'] = selected_date
    flight_data[message.chat.id]['time'] = time_now
    bot.send_message(message.chat.id, "Вы успешно подтвердили дату и время",
                     reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("Назад"))

    select_refueling_register(message)

    # select_time_register(message)


def select_time_register(message):
    push_user_state(message.chat.id, STATE_REGISTER_CHOOSE_TIME)

    user_id = message.chat.id
    current_hour = datetime.now().hour  # Устанавливаем час на текущее время
    # Инициализируем значение счётчиков для пользователя: текущий час и минуты
    user_time[user_id] = {'hour': current_hour, 'minute': 0}

    # Отправляем сообщение с кнопками для выбора часа
    bot.send_message(
        message.chat.id,
        "Укажите время полёта \nУкажите час",
        reply_markup=create_hour_keyboard(user_time[user_id]['hour'])
    )


def create_hour_keyboard(hour):
    """Создаёт клавиатуру для установки часов"""
    keyboard = types.InlineKeyboardMarkup()

    # Кнопки для увеличения, уменьшения и подтверждения времени
    add_five = types.InlineKeyboardButton(text="+5", callback_data="add_five_hour")
    add_one = types.InlineKeyboardButton(text="+1", callback_data="add_one_hour")
    hour_counter = types.InlineKeyboardButton(text=f"{hour:02d}", callback_data="hour_counter")
    minus_five = types.InlineKeyboardButton(text="-5", callback_data="minus_five_hour")
    minus_one = types.InlineKeyboardButton(text="-1", callback_data="minus_one_hour")
    confirm = types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_hour")

    # Добавляем кнопки в клавиатуру
    keyboard.row(minus_five, hour_counter, add_five)
    keyboard.row(minus_one, confirm, add_one)

    return keyboard


def create_minute_keyboard(minute):
    """Создаёт клавиатуру для установки минут"""
    keyboard = types.InlineKeyboardMarkup()

    # Кнопки для увеличения/уменьшения на 5 и 1 минуту, а также подтверждение времени
    add_five = types.InlineKeyboardButton(text="+5", callback_data="add_five_minute")
    add_one = types.InlineKeyboardButton(text="+1", callback_data="add_one_minute")
    minute_counter = types.InlineKeyboardButton(text=f"{minute:02d}", callback_data="minute_counter")
    minus_five = types.InlineKeyboardButton(text="-5", callback_data="minus_five_minute")
    minus_one = types.InlineKeyboardButton(text="-1", callback_data="minus_one_minute")
    confirm = types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_minute")

    # Добавляем кнопки в клавиатуру
    keyboard.row(minus_five, minute_counter, add_five)
    keyboard.row(minus_one, confirm, add_one)

    return keyboard


@bot.callback_query_handler(
    func=lambda call: call.data in ["add_five_hour", "add_one_hour", "minus_five_hour", "minus_one_hour",
                                    "confirm_hour"])
def handle_hour_buttons(call):
    user_id = call.message.chat.id

    # Инициализируем значение счётчика, если оно отсутствует
    if user_id not in user_time:
        user_time[user_id] = {'hour': datetime.now().hour, 'minute': 0}

    previous_hour = user_time[user_id]['hour']  # Запоминаем текущее значение

    # Обработка нажатия на кнопки для часов
    if call.data == "add_five_hour":
        user_time[user_id]['hour'] = (user_time[user_id]['hour'] + 5) % 24
    elif call.data == "add_one_hour":
        user_time[user_id]['hour'] = (user_time[user_id]['hour'] + 1) % 24
    elif call.data == "minus_five_hour":
        user_time[user_id]['hour'] = (user_time[user_id]['hour'] - 5) % 24 if user_time[user_id]['hour'] >= 5 else 0
    elif call.data == "minus_one_hour":
        user_time[user_id]['hour'] = (user_time[user_id]['hour'] - 1) % 24 if user_time[user_id]['hour'] > 0 else 0
    elif call.data == "confirm_hour":
        bot.answer_callback_query(call.id, f"Вы подтвердили час: {user_time[user_id]['hour']:02d}")
        # Удаляем сообщение с клавиатурой после подтверждения
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Теперь укажите минуты",
                         reply_markup=create_minute_keyboard(user_time[user_id]['minute']))

    # Проверка, изменилось ли значение часов, чтобы избежать ошибки "message is not modified"
    if previous_hour != user_time[user_id]['hour']:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_hour_keyboard(user_time[user_id]['hour'])
        )


@bot.callback_query_handler(
    func=lambda call: call.data in ["add_five_minute", "add_one_minute", "minus_five_minute", "minus_one_minute",
                                    "confirm_minute"])
def handle_minute_buttons(call):
    user_id = call.message.chat.id

    # Инициализируем значение счётчика минут, если оно отсутствует
    if user_id not in user_time:
        user_time[user_id] = {'hour': datetime.now().hour, 'minute': 0}

    previous_minute = user_time[user_id]['minute']  # Запоминаем текущее значение минут

    # Обработка нажатия на кнопки для минут
    if call.data == "add_five_minute":
        user_time[user_id]['minute'] = (user_time[user_id]['minute'] + 5) % 60
    elif call.data == "add_one_minute":
        user_time[user_id]['minute'] = (user_time[user_id]['minute'] + 1) % 60
    elif call.data == "minus_five_minute":
        user_time[user_id]['minute'] = (user_time[user_id]['minute'] - 5) % 60 if user_time[user_id][
                                                                                      'minute'] >= 5 else 0
    elif call.data == "minus_one_minute":
        user_time[user_id]['minute'] = (user_time[user_id]['minute'] - 1) % 60 if user_time[user_id][
                                                                                      'minute'] > 0 else 0
    elif call.data == "confirm_minute":
        bot.answer_callback_query(call.id,
                                  f"Вы подтвердили время: {user_time[user_id]['hour']:02d}:{user_time[user_id]['minute']:02d}")
        # Удаляем сообщение с клавиатурой после подтверждения
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id,
                         f"Вы выбрали время полета: {user_time[user_id]['hour']:02d}:{user_time[user_id]['minute']:02d}")
        flight_data[call.message.chat.id][
            'time'] = f"{user_time[user_id]['hour']:02d}:{user_time[user_id]['minute']:02d}"

        select_refueling_register(call.message)  # Переход к выбору литров заправки

    # Проверка, изменилось ли значение минут, чтобы избежать ошибки "message is not modified"
    if previous_minute != user_time[user_id]['minute']:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_minute_keyboard(user_time[user_id]['minute'])
        )


def select_refueling_register(message):
    push_user_state(message.chat.id, STATE_REGISTER_CHOOSE_LITERS)
    user_id = message.chat.id
    user_liters[user_id] = 0

    bot.send_message(message.chat.id, "Сколько литров было заправлено ?",
                     reply_markup=create_keyboard_for_refuling(user_liters[user_id]))


def create_keyboard_for_refuling(liters):
    keyboard = types.InlineKeyboardMarkup()

    # Кнопки для увеличения, уменьшения и подтверждения времени
    add_ten = types.InlineKeyboardButton(text="+10", callback_data="add_five_liters")
    add_one = types.InlineKeyboardButton(text="+1", callback_data="add_one_liter")
    liters_counter = types.InlineKeyboardButton(text=f"{liters}", callback_data="liters_counter")
    minus_ten = types.InlineKeyboardButton(text="-10", callback_data="minus_five_liters")
    minus_one = types.InlineKeyboardButton(text="-1", callback_data="minus_one_liter")
    confirm = types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_liters")

    # Добавляем кнопки в клавиатуру
    keyboard.row(minus_ten, liters_counter, add_ten)
    keyboard.row(minus_one, confirm, add_one)

    return keyboard


@bot.callback_query_handler(
    func=lambda call: call.data in ["add_five_liters", "add_one_liter", "minus_five_liters", "minus_one_liter",
                                    "confirm_liters"])
def handle_refueling_buttons(call):
    user_id = call.message.chat.id

    # Инициализируем значение счётчика литров, если оно отсутствует
    if user_id not in user_liters:
        user_liters[user_id] = 0

    previous_liters = user_liters[user_id]  # Запоминаем текущее значение литров

    # Обработка нажатия на кнопки для литров
    if call.data == "add_five_liters":
        user_liters[user_id] += 10
    elif call.data == "add_one_liter":
        user_liters[user_id] += 1
    elif call.data == "minus_five_liters":
        user_liters[user_id] = max(0, user_liters[user_id] - 10)
    elif call.data == "minus_one_liter":
        user_liters[user_id] = max(0, user_liters[user_id] - 1)
    elif call.data == "confirm_liters":
        bot.answer_callback_query(call.id, f"Вы подтвердили количество литров: {user_liters[user_id]}")
        # Удаляем сообщение с клавиатурой после подтверждения
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"Вы выбрали количество литров: {user_liters[user_id]}")
        flight_data[call.message.chat.id]['refueling'] = user_liters[user_id]

        get_hobbs_start(call.message)

    if previous_liters != user_liters[user_id]:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_keyboard_for_refuling(user_liters[user_id])
        )


def get_hobbs_start(message):
    push_user_state(message.chat.id, STATE_REGISTER_START_HOBBS)
    bot.send_message(message.chat.id, "Введите значение HOBBS пример (12345.67)")


# Обработчик для значения HOBBS
@bot.message_handler(func=lambda message: get_current_user_state(message.from_user.id) == STATE_REGISTER_START_HOBBS)
def handle_hobbs_start(message):
    print(f"[DEBUG] Handling HOBBS input for user {message.chat.id}")
    hobbs_start_value = message.text  # Получаем введенное значение
    try:
        # Проверяем, что введенное значение является числом
        hobbs_start_value = float(hobbs_start_value)
        flight_data[message.chat.id]['hobbs_start'] = hobbs_start_value
        print()
        print(f"[DEBUG] HOBBS start value set to {hobbs_start_value} for user {message.from_user.id}")

        bot.send_message(message.chat.id, f"Вы ввели значение HOBBS: {hobbs_start_value}")
        pop_user_state(message.from_user.id)
        print()
        print(f"[DEBUG] State popped for user {message.from_user.id}")

        select_aerodrome_start(message)

    except ValueError:
        # Если введено не число, запрашиваем ввод снова
        bot.send_message(message.chat.id, "Пожалуйста, введите числовое значение HOBBS.")
        print()
        print(f"[DEBUG] Invalid input for HOBBS by user {message.from_user.id}")


# Функция для запроса ввода аэродрома
def select_aerodrome_start(message):
    push_user_state(message.chat.id, STATE_REGISTER_CHOOSE_AERODROM)
    bot.send_message(message.chat.id, "Введите название аэродрома отправления")


# Обработчик для ввода названия аэродрома
@bot.message_handler(
    func=lambda message: get_current_user_state(message.from_user.id) == STATE_REGISTER_CHOOSE_AERODROM)
def handle_aerodrome_start(message):
    push_user_state(message.chat.id, STATE_REGISTER_COUNT_LANDING)
    aerodrome_name = message.text
    flight_data[message.chat.id]['aerodrome_start'] = aerodrome_name

    bot.send_message(message.chat.id, f"Вы ввели название аэродрома: {aerodrome_name}")
    select_count_of_landing(message)


def select_count_of_landing(message):
    user_count_of_landing[message.chat.id] = 0

    bot.send_message(message.chat.id, "теперь укажите количество посадок ",
                     reply_markup=create_keyboard_count_of_landing(user_count_of_landing[message.chat.id]))


def create_keyboard_count_of_landing(counter):
    keyboard = types.InlineKeyboardMarkup()

    # Кнопки для увеличения, уменьшения и подтверждения времени

    add_one = types.InlineKeyboardButton(text="+1", callback_data="add_one_landing")
    liters_counter = types.InlineKeyboardButton(text=f"{counter}", callback_data="landing_counter")
    minus_one = types.InlineKeyboardButton(text="-1", callback_data="minus_one_landing")
    confirm = types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_landing")

    # Добавляем кнопки в клавиатуру
    keyboard.row(minus_one, liters_counter, add_one)
    keyboard.row(confirm)

    return keyboard


@bot.callback_query_handler(
    func=lambda call: call.data in ["add_one_landing", "landing_counter", "minus_one_landing", "confirm_landing"])
def handle_refueling_buttons(call):
    user_id = call.message.chat.id

    # Инициализируем значение счётчика литров, если оно отсутствует
    if user_id not in user_count_of_landing:
        user_count_of_landing[user_id] = 0

    previous_landing_count = user_count_of_landing[user_id]  # Запоминаем текущее значение литров

    if call.data == "add_one_landing":
        user_count_of_landing[user_id] += 1
    elif call.data == "minus_one_landing":
        user_count_of_landing[user_id] = max(0, user_count_of_landing[user_id] - 1)
    elif call.data == "confirm_landing":
        bot.answer_callback_query(call.id, f"Вы подтвердили количество посадок: {user_count_of_landing[user_id]}")
        # Удаляем сообщение с клавиатурой после подтверждения
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, f"Вы выбрали количество посадок: {user_count_of_landing[user_id]}")
        flight_data[call.message.chat.id]['number_of_landings'] = user_count_of_landing[user_id]
        print()
        print(flight_data)
        select_aerodrome_end(call.message)

    if previous_landing_count != user_count_of_landing[user_id]:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_keyboard_count_of_landing(user_count_of_landing[user_id])
        )


def select_aerodrome_end(message):
    push_user_state(message.chat.id, STATE_REGISTER_CHOOSE_AERODROM_LANDING)
    bot.send_message(message.chat.id, "Введите название аэродрома посадки")
    print()
    print(f"[DEBUG] State set to STATE_REGISTER_AERODROME_END for user {message.chat.id}")


# Обработчик для ввода названия аэродрома
@bot.message_handler(
    func=lambda message: get_current_user_state(message.from_user.id) == STATE_REGISTER_CHOOSE_AERODROM_LANDING)
def handle_aerodrome_end(message):
    aerodrome_name = message.text
    flight_data[message.chat.id]['aerodrome_end'] = aerodrome_name

    bot.send_message(message.chat.id, f"Вы ввели название аэродрома: {aerodrome_name}")
    get_hobbs_end(message)


def get_hobbs_end(message):
    push_user_state(message.chat.id, STATE_REGISTER_END_HOBBS)
    bot.send_message(message.chat.id, "Введите конечное значение HOBBS пример (12345.67)")


# Обработчик для значения HOBBS
@bot.message_handler(func=lambda message: get_current_user_state(message.from_user.id) == STATE_REGISTER_END_HOBBS)
def handle_hobbs_end(message):
    hobbs_end_value = message.text  # Получаем введенное значение
    try:
        # Проверяем, что введенное значение является числом
        hobbs_start_value = float(hobbs_end_value)
        flight_data[message.chat.id]['hobbs_end'] = hobbs_start_value
        bot.send_message(message.chat.id, f"Вы ввели значение HOBBS: {hobbs_start_value}")
        add_comments_for_register(message)


    except ValueError:
        # Если введено не число, запрашиваем ввод снова
        bot.send_message(message.chat.id, "Пожалуйста, введите конечное числовое значение HOBBS.")
        print()
        print(f"[DEBUG] Invalid input for HOBBS by user {message.from_user.id}")


def add_comments_for_register(message):
    push_user_state(message.chat.id, STATE_REGISTER_COMMENT123)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Оставить комментарий")
    keyboard.add("Сохранить")

    flight_data[message.chat.id]['commentary'] = "Нет"

    bot.send_message(message.chat.id, "Теперь оставьте комментарий \n"
                                      "Если хотите сохранить без комментария нажмите сохранить", reply_markup=keyboard)


@bot.message_handler(func=lambda message: (message.text == "Оставить комментарий") and (
        get_current_user_state(message.from_user.id) == STATE_REGISTER_COMMENT123))
def handle_paste_comments(message):
    push_user_state(message.chat.id, STATE_REGISTER_COMMENT)
    bot.send_message(message.chat.id, "Напишите ниже ваш комментарий", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: get_current_user_state(message.from_user.id) == STATE_REGISTER_COMMENT)
def comments(message):
    comments = message.text

    flight_data[message.chat.id]['commentary'] = comments
    bot.send_message(message.chat.id, "Ваш ответ сохранён, данные внесены в базу")

    save_flight_data(message)


@bot.message_handler(func=lambda message: message.text == "Сохранить")
def save_flight_data(message):
    user_id = message.from_user.id

    data = flight_data[user_id]

    Register_flight.objects.create(
        profile=data['profile'],
        type_plane=Planes.objects.get(type_plane=data['type_plane']),
        date=data['date'],
        time=data['time'],
        refueling=data['refueling'],
        hobbs_start=data['hobbs_start'],
        aerodrom_start=data['aerodrome_start'],
        number_of_landings=data['number_of_landings'],
        aerodrom_end=data['aerodrome_end'],
        hobbs_end=data['hobbs_end'],
        commentary=data['commentary']
    )

    bot.send_message(message.chat.id, "Регистрация полёта завершена и сохранена!")
    flight_data[user_id].clear()
    show_main_menu(message)
    print(flight_data)


@bot.message_handler(func=lambda message: message.text == "Настройки")
def handle_settings(message):
    push_user_state(message.from_user.id, STATE_SETTINGS)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Назад")
    bot.send_message(message.chat.id, "Вы выбрали 'Настройки'. Нажмите 'Назад', чтобы вернуться.",
                     reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Проверить активные брони")
def handle_check_booking(message):
    push_user_state(message.from_user.id, STATE_CHECK_ACTIVE_BOOKING)
    bot.send_message(message.chat.id, "Идет проверка...")
    profile = get_or_create_profile(message.from_user.id, message.from_user.username)
    show_items = check_available_rent(profile)

    if show_items[0] == 0:
        bot.send_message(message.chat.id, "Активных бронирований не найдено.")
        return

    # Создаем текст и кнопки для каждого бронирования
    booking_details_text = "Ваши активные брони:\n\n"
    keyboard = types.InlineKeyboardMarkup()
    for i, booking_detail in enumerate(show_items[1]):
        booking_pk = booking_detail.split()[1]  # Получаем только ID из текста
        booking_details_text += booking_detail  # Добавляем каждый элемент в общий текст

        # Убираем префикс и передаем только PK в callback_data
        btn_change = types.InlineKeyboardButton(f'Изменить №{i + 1}', callback_data=f'change_booking_{booking_pk}')
        keyboard.add(btn_change)

    bot.send_message(message.chat.id, booking_details_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('change_booking_'))
def handle_change_booking(call):
    # Извлекаем только числовой PK из callback_data
    _, booking_pk = call.data.split('_', 1)
    print(f"[DEBUG] Selected booking PK for change: {booking_pk}")

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Вы выбрали запись с PK={booking_pk}. Что вы хотите сделать?")

    # Кнопки для удаления или отмены
    btn_delete = types.InlineKeyboardButton('Удалить', callback_data=f'delete_booking_{booking_pk}')
    btn_cancel = types.InlineKeyboardButton('Отмена', callback_data='cancel_booking')
    keyboard = types.InlineKeyboardMarkup().add(btn_delete, btn_cancel)

    bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_booking_'))
def handle_delete_booking(call):
    booking_pk = call.data.split('_')[3]
    print(booking_pk)
    try:
        Rent.objects.get(pk=int(booking_pk)).delete()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Запись успешно удалена.")
    except Rent.DoesNotExist:
        bot.send_message(call.message.chat.id, "Ошибка: Запись не найдена или уже удалена.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при удалении записи: {e}")

    show_main_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def handle_cancel_booking(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Действие отменено.")
    show_main_menu(call.message)


@bot.message_handler(func=lambda message: message.text == "Отмена")
def handle_cancel(message):
    user_booking.clear()
    flight_data[message.chat.id].clear()
    print(flight_data)
    print("Cancel")
    show_main_menu(message)


@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_back(message):
    previous_state = pop_user_state(message.from_user.id)

    if previous_state == STATE_MAIN_MENU:
        show_main_menu(message)


    elif previous_state == STATE_BOOK:
        handle_book(message)
    elif previous_state == STATE_BOOK_CHOOSE_PLANE:
        handle_book(message)  # Возврат на меню выбора самолета

    elif previous_state == STATE_BOOK_CHOOSE_DATE_ON_FLY:
        handle_book_choose_plane(message)  # Вернёт на выбор самолёта

    elif previous_state == STATE_REGISTER_FLIGHT_INIT:
        start_register_flight(message)

    elif previous_state == STATE_REGISTER_FLIGHT_DETAILS:
        start_register_flight(message)
    elif previous_state == STATE_REGISTER_FLIGHT_AUTO:
        start_register_flight(message)

    elif previous_state == STATE_REGISTER_CHOOSE_DATE:
        start_calendar(message)

    elif previous_state == STATE_REGISTER_CHOOSE_TIME:
        select_time_register(message)

    elif previous_state == STATE_REGISTER_CHOOSE_LITERS:
        select_refueling_register(message)




    elif previous_state == STATE_SETTINGS:
        handle_settings(message)
    else:

        show_main_menu(message)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        while True:
            try:
                logger.info("Запуск бота...")
                bot.polling(none_stop=True, interval=1, timeout=60)
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                logger.info("Перезапуск через 5 секунд...")
                time.sleep(5)  # Пауза перед перезапуском
