import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from django.template import Context
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext, ContextTypes, CommandHandler, \
    CallbackQueryHandler
from asgiref.sync import sync_to_async

from bot.models import Message, Profile


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
async def do_echo(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text

    p, _ = await sync_to_async(Profile.objects.get_or_create)(
        external_id=chat_id,
        defaults={'name': update.message.from_user.username}
    )

    message_instance = Message(
        profile=p,
        text=text,
    )
    await sync_to_async(message_instance.save)()

    reply_text = "Your ID = {}\n\n{}".format(chat_id, text)
    await update.message.reply_text(text=reply_text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the conversation and asks the user about their gender."""
    reply_keyboard = [["Boy", "Girl", "Other"]]

    await update.message.reply_text(
        "Hi! My name is Professor Bot. I will hold a conversation with you. "
        "Send /cancel to stop talking to me.\n\n"
        "Are you a boy or a girl?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Boy or Girl?"
        ),
    )


async def handle_gender_response(update: Update, context: CallbackContext) -> None:
    """Обрабатывает ответ пользователя на вопрос о поле."""
    user_response = update.message.text  # Получаем текст сообщения пользователя

    if user_response == "Boy":
        reply_text = "Great! You selected Boy."
    elif user_response == "Girl":
        reply_text = "Awesome! You selected Girl."
    elif user_response == "Other":
        reply_text = "Good choice! You selected Other."
    else:
        # Обработка ответа, если он не соответствует ни одному из вариантов
        reply_text = "Please select an option from the keyboard."

    # Отправляем ответ пользователю
    await update.message.reply_text(reply_text)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")


class Command(BaseCommand):
    help = "Telegram Bot"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(settings.TOKEN).build()

        # Команда /start
        application.add_handler(CommandHandler("start", start_command))

        # Обработчик нажатий на inline-кнопки
        application.add_handler(CallbackQueryHandler(button))

        # Обработчик текстовых ответов (для ответа на вопрос о поле)
        gender_response_handler = MessageHandler(
            filters.TEXT & filters.Regex("^(Boy|Girl|Other)$"),  # Фильтр для текстовых сообщений
            handle_gender_response  # Функция для обработки ответа
        )
        application.add_handler(gender_response_handler)  # Добавляем его ПЕРЕД do_echo

        # Обработчик остальных текстовых сообщений (do_echo)
        message_handler = MessageHandler(
            filters.TEXT & ~filters.Regex("^(Boy|Girl|Other)$") & ~filters.COMMAND,
            do_echo
        )
        application.add_handler(message_handler)

        # Запуск polling
        application.run_polling()
