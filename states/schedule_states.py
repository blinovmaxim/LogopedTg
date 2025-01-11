from aiogram.fsm.state import State, StatesGroup

class ScheduleStates(StatesGroup):
    selecting_date = State()
    selecting_hours = State()
    confirming_hours = State()
    blocking_date = State()
    blocking_time = State() 