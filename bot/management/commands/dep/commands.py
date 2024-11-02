from asgiref.sync import sync_to_async

from bot.models import Message, Profile, Rent
from telegram import Update, ReplyKeyboardMarkup


async def check_records_user(update: Update):
    keyboard = [
        ['Изменить'],
    ]

    try:
        # Retrieve the profile asynchronously
        profile = await sync_to_async(Profile.objects.get)(external_id=update.message.chat_id)

        # Retrieve all Rent records related to this profile
        rent_records = await sync_to_async(list)(Rent.objects.filter(profile=profile))

        # Check if there are any records and construct the response
        if rent_records:
            reply_text = "Active bookings:\n" + "\n".join(
                f"Rent ID: {rent.pk}, Aerodrom: {rent.aerodrom}, Created At: {rent.created_at}"
                for rent in rent_records
            )
        else:
            reply_text = "No active bookings found for this user."

    except Profile.DoesNotExist:
        reply_text = "Profile not found."

    await update.message.reply_text(reply_text,
                                    reply_markup=ReplyKeyboardMarkup(
                                        keyboard,
                                        resize_keyboard=True,
                                        one_time_keyboard=True), )