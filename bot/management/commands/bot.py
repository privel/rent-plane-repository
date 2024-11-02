import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from django.template import Context
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext, ContextTypes, CommandHandler, \
    CallbackQueryHandler
from asgiref.sync import sync_to_async

from bot.management.commands.dep.commands import check_records_user
from bot.models import Message, Profile, Rent


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

async def start_command(update: Update, context: CallbackContext) -> None:
    reply_keyboard = [
        ['Забронировать', 'Настройки'],
        ['Проверить активные брони']
    ]

    await update.message.reply_text(
        f"Привет {update.message.from_user.username}!\nВыберите операцию",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )


async def handle_book(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Вы выбрали 'Забронировать'. Процесс бронирования начат.")

async def handle_settings(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Вы выбрали 'Настройки'. Здесь можно изменить параметры.")

async def handle_check_reservations(update: Update, context: CallbackContext) -> None:
    await check_records_user(update)  # Вызов функции для проверки активных броней


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")


class Command(BaseCommand):
    help = "Telegram Bot"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(settings.TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))

        application.add_handler(CallbackQueryHandler(button))


        application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Забронировать$"), handle_book))
        application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Настройки$"), handle_settings))
        application.add_handler(
            MessageHandler(filters.TEXT & filters.Regex("^Проверить активные брони$"), handle_check_reservations))

        # Запуск polling
        application.run_polling()
