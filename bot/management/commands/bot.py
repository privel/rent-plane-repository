import telebot
from telebot import types
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date
from bot.models import Message, Profile, Rent

# Состояния пользователя
STATE_MAIN_MENU = "MAIN_MENU"

# бронирование полёта
STATE_BOOK = "BOOK"
STATE_BOOK_CHOOSE_PLANE = "BOOK_CHOOSE_PLANE"
STATE_BOOK_CHOOSE_DATE_ON_FLY = "BOOK_CHOOSE_TIME_ON_FLY"

# Регистрация полёта
STATE_REGISTER_FLY = "REGISTER_FLY"


STATE_SETTINGS = "SETTINGS"

STATE_CHECK_RESERVATIONS = "CHECK_RESERVATIONS"
STATE_RESERVATION_CHANGE_DELETE = "RESERVATION"

bot = telebot.TeleBot(settings.TOKEN)

# Словарь для хранения дат пользователей
user_dates = {}

# Словарь для хранения истории состояний пользователей
user_state_stack = {}

def push_user_state(user_id, state):
    if user_id not in user_state_stack:
        user_state_stack[user_id] = []
    if state not in user_state_stack[user_id] :
        user_state_stack[user_id].append(state)
    # print(f"[DEBUG] PUSH: {user_id} -> {state} (stack: {user_state_stack[user_id]})")


def pop_user_state(user_id):
    if user_id in user_state_stack and user_state_stack[user_id]:
        removed_state = user_state_stack[user_id].pop()
        # print(f"[DEBUG] POP: {user_id} <- {removed_state} (stack: {user_state_stack[user_id]})")
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Самолёт 1", "Самолёт 2")
    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        "Вы выбрали 'Забронировать'. Процесс бронирования начат.\nВыберите самолёт\nНажмите 'Назад', чтобы вернуться.",
        reply_markup=keyboard
    )



@bot.message_handler(func=lambda message: message.text in ["Самолёт 1", "Самолёт 2"])
def handle_book_choose_plane(message):
    push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_DATE_ON_FLY)
    chosen_plane = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Назад")
    bot.send_message(
        message.chat.id,
        f"Вы выбрали {chosen_plane}. Выбор сохранен.\nТеперь выберите дату полёта",
        reply_markup=keyboard
    )

    calendar_command(message)


@bot.message_handler(func=lambda message: message.text == "Настройки")
def handle_settings(message):
    push_user_state(message.from_user.id, STATE_SETTINGS)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Назад")
    bot.send_message(message.chat.id, "Вы выбрали 'Настройки'. Нажмите 'Назад', чтобы вернуться.",
                     reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_back(message):
    # Получаем текущее состояние после удаления верхнего элемента стека
    previous_state = pop_user_state(message.from_user.id)

    # Отладочный вывод
    #print(f"[DEBUG] BACK BUTTON: previous_state = {previous_state}")

    # Проверяем состояние после возврата и выводим нужное меню
    if previous_state == STATE_MAIN_MENU:
        show_main_menu(message)


    elif previous_state == STATE_BOOK:
        handle_book(message)
    elif previous_state == STATE_BOOK_CHOOSE_PLANE:
        handle_book(message)  # Возврат на меню выбора самолета
    elif previous_state == STATE_BOOK_CHOOSE_DATE_ON_FLY:
        handle_book_choose_plane(message)  # Вернёт на выбор самолёта


    elif previous_state == STATE_SETTINGS:
        handle_settings(message)
    else:
        # Если состояние не определено, возвращаем на главный экран
        show_main_menu(message)


# @bot.message_handler(func=lambda message: message.text == "Настройки123")
def calendar_command(message):
    # push_user_state(message.from_user.id, STATE_BOOK_CHOOSE_DATE_ON_FLY)
    current_year = date.today().year
    calendar, step = DetailedTelegramCalendar(min_date=date(current_year, 1, 1),
                                              current_date=date(current_year, 1, 1)).build()

    bot.send_message(
        message.chat.id,
        f"Выберите {LSTEP[step]}",
        reply_markup=calendar
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
        push_user_state(call.from_user.id, STATE_MAIN_MENU)


class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        bot.polling(none_stop=True)
