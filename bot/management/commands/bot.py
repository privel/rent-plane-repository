import telebot
from telebot import types
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date

from bot.management.commands.dep.commands import aerodrom_available, get_or_create_profile, \
    delete_rent, save_rent
from bot.management.commands.dep.date.date_command import DateSelectionCommand
from bot.management.commands.storage import STATE_MAIN_MENU, STATE_BOOK_CHOOSE_PLANE, STATE_BOOK_CHOOSE_DATE_ON_FLY, \
    STATE_REGISTER_FLY, STATE_REGISTER_CHOOSE_AERODROM, STATE_SETTINGS, STATE_BOOK, user_state_stack, user_times, \
    user_booking, user_date_selection
from bot.models import Profile, Rent, Aerodrom

bot = telebot.TeleBot(settings.TOKEN)


def select_time(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00")
    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        "Выберите время полёта:",
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


# Handle time selection for both timeStart and timeEnd
@bot.message_handler(
    func=lambda message: message.text in ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00",
                                          "17:00", "18:00"]
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
        # Now prompt for dateEnd
        date_selection_command.show_calendar(message.chat.id, "dateEnd")

    elif current_time_type == "timeEnd":
        user_booking["timeEnd"] = message.text
        bot.send_message(
            message.chat.id,
            f"Вы выбрали время окончания {message.text}."
        )
        # Finalize booking
        finalize_booking(message.chat.id, message)


def finalize_booking(chat_id, message):
    """Function to finalize and save the booking to the database."""
    profile = user_booking.get("profile")
    if profile:
        # Create a new Rent entry without replacing existing ones
        Rent.objects.create(
            profile=profile,
            type_plane=user_booking.get("type_plane"),
            dateStart=user_booking.get("dateStart"),
            timeStart=user_booking.get("timeStart"),
            dateEnd=user_booking.get("dateEnd"),
            timeEnd=user_booking.get("timeEnd")
        )
        print(f"Booking saved: {user_booking}")
        user_booking.clear()

    bot.send_message(chat_id, "Бронирование завершено!")

    # Clear user booking data after saving
    # save_rent(user_booking)

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


@bot.message_handler(func=lambda message: message.text == "Забронировать")
def handle_book(message):
    push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_PLANE)

    profile = get_or_create_profile(message.from_user.id, message.from_user.username)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Самолёт 1")
    keyboard.add("Отмена")
    bot.send_message(
        message.chat.id,
        "Вы выбрали 'Забронировать'. Процесс бронирования начат.\nВыберите самолёт\nНажмите 'Назад', чтобы вернуться.",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text in ["Самолёт 1", "Самолёт 2"])
def handle_book_choose_plane(message):
    push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_DATE_ON_FLY)

    profile = get_or_create_profile(message.from_user.id, message.from_user.username)

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

    aerodromsList = aerodrom_available()

    print(aerodromsList)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for nameaero in aerodromsList:
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


@bot.message_handler(func=lambda message: message.text == "Отмена")
def handle_cancel(message):
    show_main_menu(message)




@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_back(message):
    # Получаем текущее состояние после удаления верхнего элемента стека
    previous_state = pop_user_state(message.from_user.id)

    # Отладочный вывод
    # print(f"[DEBUG] BACK BUTTON: previous_state = {previous_state}")

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
