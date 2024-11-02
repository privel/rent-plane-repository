import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from django.template import Context
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext, ContextTypes, CommandHandler
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
    await update.message.reply_text(f"Hello {update.message.from_user.username}")




class Command(BaseCommand):
    help = "Telegram Bot"

    def handle(self, *args, **options):

        application = ApplicationBuilder().token(settings.TOKEN).build()


        message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, do_echo)
        application.add_handler(message_handler)
        application.add_handler(CommandHandler("start", start_command))


        application.run_polling()
