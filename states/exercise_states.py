from aiogram.fsm.state import State, StatesGroup

class ExerciseStates(StatesGroup):
    waiting_for_category = State()
    viewing_exercise = State()
    searching = State()

class AddExerciseStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_title = State()
    waiting_for_video = State()
    waiting_for_description = State() 