from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import date
from telebot import TeleBot, types
from bot.management.commands.storage import user_date_selection, user_booking


class DateSelectionCommand:

    def __init__(self, bot: TeleBot, select_time_func):
        self.bot = bot
        self.select_time = select_time_func  # Store select_time function

    def show_calendar(self, chat_id, date_type):
        # Save date type for the user
        user_date_selection[chat_id] = date_type

        current_date = date.today()

        # Determine min_date based on whether it's dateEnd and if dateStart is already selected
        if date_type == "dateEnd" and "dateStart" in user_booking:
            min_date = user_booking["dateStart"]  # Set minimum date for dateEnd as dateStart
        else:
            min_date = date(current_date.year, 1, 1)

        calendar, step = DetailedTelegramCalendar(
            min_date=min_date,
            max_date=date(current_date.year, 12, 31),
            current_date=current_date
        ).build()

        self.bot.send_message(
            chat_id,
            f"Выберите {LSTEP[step]}",
            reply_markup=calendar,
        )

    def handle_calendar_selection(self, call, profile):
        # Determine min_date for dateEnd selection based on dateStart
        date_type = user_date_selection.get(call.message.chat.id, "dateStart")
        if date_type == "dateEnd" and "dateStart" in user_booking:
            min_date = user_booking["dateStart"]
        else:
            min_date = date.today()

        # Use the adjusted min_date in the calendar processing
        result, key, step = DetailedTelegramCalendar(min_date=min_date).process(call.data)

        if result and result < date.today():
            self.bot.answer_callback_query(call.id, "Нельзя выбрать дату в прошлом. Пожалуйста, выберите другую дату.")
            self.bot.edit_message_text(
                f"Выберите {LSTEP[step]}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=key
            )
        elif not result and key:
            self.bot.edit_message_text(
                f"Выберите {LSTEP[step]}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=key
            )
        elif result:
            # Get the date type for the user (dateStart or dateEnd)
            field_to_update = {"dateStart": result} if date_type == "dateStart" else {"dateEnd": result}

            # Store date selection in user_booking
            user_booking[date_type] = field_to_update[date_type]
            print(user_booking)

            self.bot.edit_message_text(
                f"Вы выбрали {result}. Дата сохранена!",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

            # Determine the next step in the booking flow
            if date_type == "dateStart":
                # Switch to choosing timeStart after dateStart
                user_date_selection[call.message.chat.id] = "timeStart"
                self.bot.send_message(call.message.chat.id, "Теперь выберите время начала полёта.")
                self.select_time(call.message)  # Show time selection for timeStart

            elif date_type == "dateEnd":
                # Finalize with timeEnd after dateEnd
                user_date_selection[call.message.chat.id] = "timeEnd"
                self.bot.send_message(call.message.chat.id, "Теперь выберите время окончания полёта.")
                self.select_time(call.message)  # Show time selection for timeEnd
            else:
                # Clear date selection if no more steps
                del user_date_selection[call.message.chat.id]
