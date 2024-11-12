# Состояния пользователя
from datetime import datetime

STATE_MAIN_MENU = "MAIN_MENU"

# бронирование полёта
STATE_BOOK = "BOOK"
STATE_BOOK_CHOOSE_PLANE = "BOOK_CHOOSE_PLANE"
STATE_BOOK_CHOOSE_DATE_ON_FLY = "BOOK_CHOOSE_TIME_ON_FLY"

# Регистрация полёта
STATE_REGISTER_FLIGHT_INIT = "REGISTER_FLIGHT_INIT"
STATE_REGISTER_FLIGHT_DETAILS = "REGISTER_FLIGHT_DETAILS"
STATE_REGISTER_CHOOSE_DATE = "REGISTER_CHOOSE_DATE"
STATE_REGISTER_CHOOSE_TIME = "REGISTER_CHOOSE_TIME"
STATE_REGISTER_CHOOSE_LITERS = "REGISTER_CHOOSE_LITERS"
STATE_REGISTER_START_HOBBS = "REGISTER_START_HOBBS"
STATE_REGISTER_CHOOSE_AERODROM = "REGISTER_CHOOSE_AERODROM"
STATE_REGISTER_COUNT_LANDING = "REGISTER_COUNT_LANDING"
STATE_REGISTER_CHOOSE_AERODROM_LANDING = "REGISTER_CHOOSE_AERODROM_LANDING"
STATE_REGISTER_END_HOBBS = "REGISTER_END_HOBBS"
STATE_REGISTER_COMMENT123 = "REGISTER_COMMENT123"
STATE_REGISTER_COMMENT = "REGISTER_COMMENTS"

STATE_SETTINGS = "SETTINGS"

STATE_CHECK_RESERVATIONS = "CHECK_RESERVATIONS"
STATE_RESERVATION_CHANGE_DELETE = "RESERVATION"


STATE_CHECK_ACTIVE_BOOKING = "CHECK_ACTIVE_BOOKING"



user_state_stack = {}

# Словарь для хранения промежуточных данных регистрации полёта
flight_data = {}



# Словарь для хранения дат пользователей
user_dates = {}
user_times = {}
aerodromsList = []

# Словарь для хранения истории состояний пользователей
user_state_stack = {}
user_date_selection = {}

user_booking = {}

available_booking_time = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00",
                          "17:00", "18:00"]

current_date = datetime.now()

user_counters = {}
user_time = {}
user_liters = {}
user_hobbs = {}
user_count_of_landing = {}