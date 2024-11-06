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





# Словарь для хранения дат пользователей
user_dates = {}
user_times = {}
aerodromsList = []

# Словарь для хранения истории состояний пользователей
user_state_stack = {}
user_date_selection = {}


user_booking = {}