from pyrogram import filters

user_steps = {}

def login_filter_func(_, __, message):
    # Sabse pehle check karo ki from_user exist karta bhi hai ya nahi
    if not message.from_user:
        return False
    user_id = message.from_user.id
    return user_id in user_steps

login_in_progress = filters.create(login_filter_func)

def set_user_step(user_id, step=None):
    if step:
        user_steps[user_id] = step
    else:
        user_steps.pop(user_id, None)


def get_user_step(user_id):
    return user_steps.get(user_id)