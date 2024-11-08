from pyexpat.errors import messages

import telebot
from telebot import types
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram_bot_calendar import DetailedTelegramCalendar

from bot.management.commands.dep.commands import aerodrom_available, get_or_create_profile, get_type_available_plane, \
    is_time_slot_available, get_unavailable_times, check_available_rent
from bot.management.commands.dep.date.date_command import DateSelectionCommand
from bot.management.commands.storage import STATE_MAIN_MENU, STATE_BOOK_CHOOSE_PLANE, STATE_BOOK_CHOOSE_DATE_ON_FLY, \
    STATE_REGISTER_FLY, STATE_REGISTER_CHOOSE_AERODROM, STATE_SETTINGS, STATE_BOOK, user_state_stack, \
    user_booking, user_date_selection, available_booking_time, STATE_CHECK_ACTIVE_BOOKING
from bot.models import Rent

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
    print(f"[DEBUG] PUSH: {user_id} -> {state} (stack: {user_state_stack[user_id]})")


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


# Handle time selection for both timeStart and timeEnd
# @bot.message_handler(
#     func=lambda message: message.text in available_booking_time
# )
# def handle_time_selection(message):
#     current_time_type = user_date_selection.get(message.chat.id)
#
#     if current_time_type == "timeStart":
#         user_booking["timeStart"] = message.text
#         bot.send_message(
#             message.chat.id,
#             f"Вы выбрали время начала {message.text}.",
#             reply_markup=types.ReplyKeyboardRemove()
#         )
#         # Now prompt for dateEnd
#         date_selection_command.show_calendar(message.chat.id, "dateEnd")
#
#     elif current_time_type == "timeEnd":
#         user_booking["timeEnd"] = message.text
#         bot.send_message(
#             message.chat.id,
#             f"Вы выбрали время окончания {message.text}."
#         )
#         # Finalize booking
#         finalize_booking(message.chat.id, message)

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


@bot.message_handler(func=lambda message: message.text == "Регистрация полёта")
def handle_registration_fly(message):
    push_user_state(message.from_user.id, STATE_REGISTER_FLY)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Самолёт 3", "Самолёт 4")
    keyboard.add('Назад')

    bot.send_message(message.chat.id,
                     "Вы выбрали 'Регистрацию полёта' Процесс регистрации начат \n"
                     f" Выберите самолёт \n"
                     "Нажмите 'Назад', чтобы вернуться.",
                     reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text in ["Самолёт 3", "Самолёт 4"])
def handle_book_choose_plane(message):
    push_user_state(message.from_user.id, STATE_REGISTER_CHOOSE_AERODROM)
    chosen_plane = message.text

    aerodromeList = aerodrom_available()

    print(aerodromeList)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for nameaero in aerodromeList:
        keyboard.add(nameaero)

    keyboard.add("Обновить", "Назад")
    if chosen_plane != "Обновить":
        bot.send_message(
            message.chat.id,
            f"Вы выбрали {chosen_plane}. Выбор сохранен.\nТеперь выберите аэродром",
            reply_markup=keyboard
        )
    elif chosen_plane == "Обновить":
        bot.send_message(
            message.chat.id,
            f"Вы обновили страницу.",
            reply_markup=keyboard
        )


@bot.message_handler(func=lambda message: message.text == "Обновить")
def handle_update_aerodrom(message):
    handle_book_choose_plane(message)


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
    booking_pk = call.data.split('_')[3]  # Получаем только PK
    print(booking_pk)
    try:
        Rent.objects.get(pk=int(booking_pk)).delete()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Запись успешно удалена.")
    except Rent.DoesNotExist:
        bot.send_message(call.message.chat.id, "Ошибка: Запись не найдена или уже удалена.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при удалении записи: {e}")

    # Возврат в главное меню после удаления
    show_main_menu(call.message)



@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def handle_cancel_booking(call):
    # Возврат в главное меню при отмене
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Действие отменено.")
    show_main_menu(call.message)



@bot.message_handler(func=lambda message: message.text == "Отмена")
def handle_cancel(message):
    user_booking.clear()
    show_main_menu(message)


@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_back(message):
    previous_state = pop_user_state(message.from_user.id)

    # Проверяем состояние после возврата и выводим нужное меню
    if previous_state == STATE_MAIN_MENU:
        show_main_menu(message)


    elif previous_state == STATE_BOOK:
        handle_book(message)
    elif previous_state == STATE_BOOK_CHOOSE_PLANE:
        handle_book(message)  # Возврат на меню выбора самолета

    elif previous_state == STATE_BOOK_CHOOSE_DATE_ON_FLY:
        handle_book_choose_plane(message)  # Вернёт на выбор самолёта

    elif previous_state == STATE_REGISTER_FLY:
        handle_registration_fly(message)


    elif previous_state == STATE_SETTINGS:
        handle_settings(message)
    else:
        # Если состояние не определено, возвращаем на главный экран
        show_main_menu(message)


class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        bot.polling(none_stop=True)
