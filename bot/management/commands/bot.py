import telebot
from telebot import types
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date

from bot.management.commands.dep.commands import aerodrom_available, get_or_create_profile, \
    create_if_doesnt_exist_rent, delete_rent
from bot.models import Profile, Rent, Aerodrom

# Состояния пользователя
STATE_MAIN_MENU = "MAIN_MENU"

# бронирование полёта
STATE_BOOK = "BOOK"
STATE_BOOK_CHOOSE_PLANE = "BOOK_CHOOSE_PLANE"
STATE_BOOK_CHOOSE_DATE_ON_FLY = "BOOK_CHOOSE_TIME_ON_FLY"

# Регистрация полёта
STATE_REGISTER_FLY = "REGISTER_FLY"
STATE_REGISTER_CHOOSE_AERODROM = "REGISTER_CHOOSE_AERODROM"
STATE_REGISTER_CHOOSE_DATE = "REGISTER_CHOOSE_DATE"
STATE_REGISTER_CHOOSE_TIME = "REGISTER_CHOOSE_TIME"

STATE_SETTINGS = "SETTINGS"

STATE_CHECK_RESERVATIONS = "CHECK_RESERVATIONS"
STATE_RESERVATION_CHANGE_DELETE = "RESERVATION"

bot = telebot.TeleBot(settings.TOKEN)

# Словарь для хранения дат пользователей
user_dates = {}
user_times = {}
aerodromsList = []

# Словарь для хранения истории состояний пользователей
user_state_stack = {}


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


@log_error
@bot.message_handler(commands=['start'])
def start_command(message):
    push_user_state(message.from_user.id, STATE_MAIN_MENU)
    show_main_menu(message)
    profile = get_or_create_profile(message.from_user.id, message.from_user.username)
    create_if_doesnt_exist_rent(profile)


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
    keyboard.add("Самолёт 1", "Самолёт 2")
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

    try:
        Rent.objects.update(profile=profile, type_plane=chosen_plane)
    except Exception as e:
        pass

    calendar_command(message)


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


def calendar_command(message):
    current_date = date.today()
    calendar, step = DetailedTelegramCalendar(
        min_date=date(current_date.year, 1, 1),
        max_date=date(current_date.year, 12, 31),  # Ограничиваем выбор только текущим годом
        current_date=current_date  # Текущая дата как начальный месяц

    ).build()

    bot.send_message(
        message.chat.id,
        f"Выберите {LSTEP[step]}",
        reply_markup=calendar,
    )


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def handle_calendar_selection(call):
    result, key, step = DetailedTelegramCalendar(min_date=date.today()).process(call.data)

    # Проверяем, выбрана ли допустимая дата
    if result and result < date.today():
        # Если дата в прошлом, сообщаем пользователю, что выбор недопустим
        bot.answer_callback_query(call.id, "Нельзя выбрать дату в прошлом. Пожалуйста, выберите другую дату.")
        # Оставляем календарь на текущем шаге
        bot.edit_message_text(
            f"Выберите {LSTEP[step]}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=key
        )

    elif not result and key:
        # Оставляем календарь открытым, если выбор даты еще не завершен
        bot.edit_message_text(
            f"Выберите {LSTEP[step]}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=key
        )
    elif result:
        # Сохраняем корректную дату
        user_dates[call.from_user.id] = result
        bot.edit_message_text(
            f"Вы выбрали {result}. Дата сохранена!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        # push_user_state(call.from_user.id, STATE_MAIN_MENU)
        select_time(call.message)


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

    delete_rent(get_or_create_profile(message.from_user.id, message.from_user.username))


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


def select_time(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("09:00", "12:00", "15:00", "18:00")
    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        "Выберите время полёта:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text in ["09:00", "12:00", "15:00", "18:00"])
def handle_time_selection_registration(message):
    user_times[message.from_user.id] = message.text
    bot.send_message(
        message.chat.id,
        f"Вы выбрали время {message.text}. Регистрация завершена."
    )
    show_main_menu(message)


class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        bot.polling(none_stop=True)
