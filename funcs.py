import json
import asyncio
import math
import time
from datetime import datetime
import pytz
import pydantic

from aiogram import types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.serialization import deserialize_telegram_object_to_python
from aiogram.utils.media_group import MediaGroupBuilder

from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client["anon_chat"]
users = db["users"]
userchats = db["userchats"]
cache = db["cache"]

from randomizer import gen_split, gen, id_gen
from file_op import *
from button_gen import Inline, Keyboard
from wrappers import _big_report, _report, log

texts = json.load(open('base/messages.json', 'r', encoding='utf-8'))

# SAFE UPDATE
async def safe_update(bot):
    # update user states and settings safely
    for user in users.find():
        try:
            reset_sessions = {}
            for cell in ["state", "cooldown", "cooldown_timer"]:
                cell_data = key(users, {"orig": user["orig"]}, cell)
                if cell_data != "" and cell_data != 0:
                    reset_sessions[cell] = cell_data
                    set_user_key(user["orig"], {cell: "" if type(cell_data) == str else 0})
            user_id = int(user["orig"])
            if len(reset_sessions) != 0:
                await msg_with_hide(texts["reboot_bot"].format(interrupted=reset_sessions), None, id=user_id, bot=bot)
            else:
                await msg_with_hide(texts["reboot_bot_safe"], None, id=user_id, bot=bot)
        except Exception as e:
            _report("err", f"Failed to update user {e}", user=user["orig"])





# FUNCTION TO GENERATE HIDE BUTTON
async def hide_button_gen(msg, unique):
    return Inline.hide(Inline, unique)

# Save serialized objects to a file
async def save_serialized(msg, unique, type, user, special=False):
    if not special:
        content = json.dumps( deserialize_telegram_object_to_python(msg))
        create_cached(unique, type, user, content)
    else:
        content = []
        ids = []
        for element in msg:
            content.append( json.dumps(deserialize_telegram_object_to_python(element)) )
            ids.append(element.message_id)
        create_cached(unique, type, user, content, ids=ids)

# Load serialized objects from a file
async def load_serialized(bot):
    output = {}
    try:
        for cached in cache.find():
            msg = cached["content"]
            output[cached["id"]] = Message.model_validate(obj=json.loads(msg),context={"bot":bot})
        return output
    except Exception as e:
        return {}


async def serialize_one(content, bot):
    return Message.model_validate(obj=json.loads(content), context={"bot": bot})


# FUNCTION TO SEND MESSAGE WITH HIDE BUTTON
async def msg_with_hide(text, orig_message, id=False, bot=False):
    unique_id = id_gen(8)
    if not id:
        to_edit_msg = await orig_message.answer(text)
        await to_edit_msg.edit_text(text=text, reply_markup=await hide_button_gen(to_edit_msg, unique_id))
    else:
        to_edit_msg = await bot.send_message(id, text=text)
        await to_edit_msg.edit_text(text=text, reply_markup=await hide_button_gen(to_edit_msg, unique_id))
    await save_serialized(to_edit_msg, unique_id, "hide_cell", orig_message.from_user.id if orig_message else None)





# FUNCTION TO CREATE PROFILE CELL
async def profile_cell(msg, user, unique):
    await save_serialized(msg, unique, "profile_cell", user)
    set_user_key(user, {"profile_cell": unique})

# FUNCTION TO CREATE MEDIA CELL
async def media_cell(msg, user, unique):
    await save_serialized(msg, unique, "media_cell", user)
    set_user_key(user, {"media_cell": unique})

# FUNCTION TO GET CURRENT TIME IN LONDON TIMEZONE
async def get_time():
    london_tz = pytz.timezone('Europe/London')
    current_time_london = datetime.now(london_tz)
    return current_time_london.strftime("%Y-%m-%d_%H:%M:%S")

# FUNCTION TO HANDLE COOLDOWN TIMER
async def cooldown_writer(cooldown_path, msg):
    if get_user_key(cooldown_path, "cooldown_timer") != 1:
        set_user_key(cooldown_path, {"cooldown_timer": 1})
        msg = await msg.answer(texts["cooldown"].format(n=get_user_key(cooldown_path, 'cooldown')))
        while get_user_key(cooldown_path, 'cooldown') != 0:
            cd_update = get_user_key(cooldown_path, 'cooldown')
            await asyncio.sleep(0.1)
            cooldown = get_user_key(cooldown_path, 'cooldown')
            if cd_update != cooldown:
                await msg.edit_text(texts["cooldown"].format(n=cooldown))
        await msg.delete()
        set_user_key(cooldown_path, {"cooldown_timer": 0})

# FUNCTION TO CHECK IF USER IS BANNED
async def ban_check(user, chat, msg):
    if user in get_chat_key(chat, "banned"):
        await msg_with_hide(texts["banned"].format(chat=chat), msg)
        return True
    return False

# FUNCTION TO LOAD CHAT DATA
async def load_get(to_get_id, user_id, msg, callback=False):
    user_id = int(user_id)
    unique = id_gen(8)
    set_user_key(user_id, {"getting": to_get_id})
    set_user_key(user_id, {"chat_slice": 0})
    set_user_key(user_id, {"media_cell": 0})
    set_user_key(user_id, {"status_opened": 0})
    set_user_key(user_id, {"media_id": unique})

    data = await get_chat_sliced(to_get_id, 256, user_id)
    chat = data[0]
    sources = data[1][0]
    max = len(chat)
    precent = math.ceil(1 / max * 100)
    content = " ".join(chat[0])

    message_text = texts["page_template"].format(page=1, max=max, precent=precent, text=content)
    buttons = Inline.up(Inline,
                        0 if sources else -1,
                        get_user_key(msg.from_user.id if not callback else callback.from_user.id, "getting"),
                        unique) if max != 1 else None

    await msg.answer(message_text, reply_markup=buttons)



# FUNCTION TO DELETE CHAT DATA
async def delete_chat(chat):
    for user in users.find():
        joined = get_user_key(user["orig"], "joined")
        host = get_user_key(user["orig"], "host")
        while chat in joined:
            joined.remove(chat)
            set_user_key(user["orig"], {"joined": joined})
        while chat in host:
            host.remove(chat)
            set_user_key(user["orig"], {"host": host})
    userchats.delete_one({"name": chat})

# FUNCTION TO REFRESH USER STATUS
async def status_refresh(user):
    set_user_key(user, {"last_online": time.time()})

# FUNCTION TO GET USER PROFILE
async def my_profile(user):
    date = get_user_key(user, "date_joined")
    desc = get_user_key(user, "description")
    return texts["my_profile"].format(user=await get_usercode(user),
                                      date=datetime.fromtimestamp(int(date)),
                                      chats=", ".join( [f"<code>{chat}</code>" for chat in get_user_key(user, "joined")] ),
                                      msg_count=get_user_key(user, "msg_count"),
                                      desc=desc if len(desc) > 0 else "[Описание здесь]")

# FUNCTION TO GENERATE STATUS MESSAGE BASED ON TIME DIFFERENCE
def get_end(number):
    number = number % 10
    if number == 1:
        return ""
    elif number > 1 and number <= 4:
        return "а"
    elif number > 4 and number <= 9 or number == 0:
        return "ов"


async def status_gen(diff):
    if diff < 300:
        status = texts["o_online"]
    elif diff < 3600:
        status = texts["o_recent"]
    elif diff < 86400:
        count_hours = round(diff/3600)
        status = texts["o_not_long"].format(time=count_hours, end=get_end(count_hours))
    else:
        status = texts["o_long"].format(time=datetime.fromtimestamp(last_online))
    return status

# FUNCTION TO FORMAT USER PROFILE
async def profile_format(user, from_user):
    last_online = get_user_key(user, "last_online")
    diff = time.time() - last_online
    status = await status_gen(diff)
    date = get_user_key(user, "date_joined")
    date = datetime.fromtimestamp(int(date))
    shared = ''
    count = get_user_key(user, "msg_count")
    other_user_chats = get_user_key(user, "joined")
    for chat in get_user_key(from_user, "joined"):
        if chat in other_user_chats:
            shared += f"<code>{chat}</code>, "
    description = get_user_key(user, "description")
    return texts["profile"].format(user=await get_usercode(user), status=status, date=date, shared_chats=shared, msg_count=count, desc=description if len(description) > 0 else "[Описание здесь]")

# FUNCTION TO GENERATE USER PROFILE
async def generate_profile(user, msg, callback):
    if callback:
        await callback.message.answer(await profile_format(user, callback.from_user.id))
    else:
        await msg.answer(await profile_format(user, msg.from_user.id))

# FUNCTION TO CREATE ALTERNATIVE ENTRY
async def alt_create(id, msg):
    gen_name = gen(5)
    await set_up(gen_name, id)
    append_key(users, {"orig":id},{"joined":gen_name})
    await msg_with_hide(texts["create"].format(id=gen_name), msg)

# FUNCTION TO WRITE MESSAGE
async def message_write(msg):
    await status_refresh(msg.from_user.id)
    msg_count = get_user_key(msg.from_user.id, "msg_count")
    msg_count += 1
    set_user_key(msg.from_user.id, {"msg_count": msg_count})
    time_now, id, username, sent, cooldown = await set_msg_data(msg)
    if cooldown == 0:
        chat_id = get_user_key(username, "state")
        usercode = get_user_key(username, "id")
        count = get_chat_key(chat_id, "message_count")
        messages = get_chat_key(chat_id, "messages")
        messages.append(texts["write_template"].format(user=usercode, date=time_now, text=msg.text, src=""))
        set_chat_key(chat_id, {"message_count": count + 1, "messages": messages})
        await asyncio.create_task(cd(username, 3))
    else:
        await cooldown_writer(username, msg)

# FUNCTION TO SEND PHOTO
async def send_photo(msg, usercode, time_now, photo, chat_id):
    await status_refresh(msg.from_user.id)
    msg_count = get_user_key(msg.from_user.id, "msg_count")
    msg_count += 1
    set_user_key(msg.from_user.id, {"msg_count": msg_count})
    messages = get_chat_key(chat_id, "messages")
    messages.append(texts["write_template"].format(user=usercode, date=time_now, text=msg.caption if msg.caption else " ", src=photo))
    set_chat_key(chat_id, {"messages": messages})


# FUNCTION TO JOIN CHAT
async def join_id(id, chat_id, msg):
    try:
        if int(id) in get_chat_key(chat_id, "banned"):
            await msg_with_hide(texts["banned"].format(chat=chat_id), msg)
            return 0
    except:
        await msg_with_hide(texts["fake_chat"], msg)
        return 0
    if chat_id in get_user_key(id, "joined"):
        await msg_with_hide(texts["already_joined"], msg)
        return 0
    if locate_chat(chat_id):
        if int(id) in get_chat_key(chat_id, "access"):
            append_key(users, {"orig": id}, {"joined": chat_id})
            await msg_with_hide(texts["join"].format(id=chat_id), msg)
            if get_chat_key(chat_id, "message_count") > 0:
                await msg_with_hide(texts["open_2"].format(id=chat_id), msg)
        else:
            await msg_with_hide(texts["no_join"].format(chat=chat_id), msg)

# FUNCTION TO ALLOW USER IN CHAT
async def process_allow(user, chat, msg):
    list_allowed = get_chat_key(chat, "access")
    orig_id = await get_orig_id(user)
    if orig_id is None:
        await msg_with_hide(texts["fake_user"], msg)
        return 0
    list_allowed.append(int(orig_id))
    set_chat_key(chat, {"access": list_allowed})

# FUNCTION TO MAKE USER ADMIN
async def make_admin(id, chat, msg):
    append_key("users", {"orig": id}, {"admin": int(id)})

# FUNCTION TO SEND MESSAGE ASYNCHRONOUSLY
async def send_message_async(bot, id, text):
    await bot.send_message(id, text)

# FUNCTION TO SET MESSAGE DATA
async def set_msg_data(msg):
    time_now = await get_time()
    id = msg.from_user.id
    sent = 0
    cooldown = get_user_key(id, "cooldown")
    return time_now, id, id, sent, cooldown

# FUNCTION TO SET UP NEW CHAT
async def set_up(id, creator):
    if not locate_chat(id):
        append_key(users, {"orig": creator}, {"host": id})
        content = {
            "name": id,
            "admin": [creator],
            "access": [creator],
            "message_count": 0,
            "banned": [],
            "description": "[Описание отсутствует]",
            "host": creator,
            "messages": []
        }
        upload(userchats, content)
    else:
        pass

def set_up_user(id, usercode):
    content = {
        "orig": id,
        "id": usercode,
        "host": [],
        "joined": [],
        "state": "",
        "redacting": "",
        "on_panel": "",
        "cooldown": 0,
        "reg_time": 0,
        "chat_slice": 0,
        "to_change": 0,
        "getting": [],
        "cooldown_timer": 0,
        "date_joined": time.time(),
        "last_online": time.time(),
        "description": "",
        "msg_count": 0,
        "profile_cell": 0,
        "media_cell": 0,
        "media_id": 0
    }
    return content

# FUNCTION TO HANDLE COOLDOWN
async def cd(edit_path, length):
    for second in range(length + 1):
        set_user_key(edit_path, {"cooldown": length - second})
        await asyncio.sleep(1)

# FUNCTION TO DELETE ADMIN
async def delete_admin(user, chat, msg):
    if await ban_check(user, chat, msg):
        return 0
    admins = get_chat_key(chat, "admin")
    user = int(user)
    while user in admins:
        admins.remove(user)
    set_chat_key(chat, {"admin": admins})
    await msg_with_hide(texts["success"].format(chat=chat), msg)

# FUNCTION TO CHECK AND EDIT MESSAGE
async def edit_check(msg, username):
    cooldown = get_user_key(username, "cooldown")
    sent = await msg.answer(texts["cooldown"].format(n=cooldown))
    while cooldown != 0:
        cooldown = get_user_key(username, "cooldown")
        tick = get_user_key(username, "cooldown")
        if cooldown != tick:
            await sent.edit_text(texts["cooldown"].format(n=cooldown))
    await sent.delete()

# FUNCTION TO GET USER CODE
async def get_usercode(id):
    user = users.find_one({"orig": id})
    return user["id"] if user else None

# FUNCTION TO GET ORIGINAL USER ID
async def get_orig_id(usercode):
    user = users.find_one({"id": usercode})
    return user["orig"] if user else None

# FUNCTION TO GET SLICED CHAT MESSAGES
async def get_chat_sliced(chat, sliceby, id):
    usercode = await get_orig_id(id)
    messages = get_chat_key(chat, "messages")
    output = []
    column = []
    attachments = {}
    slicer = 0
    slice_pos = 0
    attachments[0] = []
    for message in messages:
        user, date, src, *text_parts = message.split(' ')
        text = " ".join(text_parts)
        usertype = await get_usertype(int(id), user, int(chat))

        if src != "":
            attachments[slice_pos].append(src)
            text += " [Медиа] "
            slicer += 10

        row = texts["safe_message_template"].format(usercode=user, content=text, usertype=usertype) + '\n\n'

        column.append(row)
        slicer += len(row)

        if slicer > sliceby:
            slice_pos += 1
            attachments[slice_pos] = []
            output.append(column)
            column = []
            slicer = 0

    if column:
        output.append(column)
    print(attachments)
    return [output, attachments]


# FUNCTION TO MODULATE CHAT SLICE
async def modulate_slice(msg_orig, add):
    user_id = msg_orig.from_user.id
    to_get_id = get_user_key(user_id, "getting")
    data = await get_chat_sliced(to_get_id, 256, user_id)
    chat = data[0]
    sources = data[1]

    slice = get_user_key(user_id, "chat_slice")+add
    set_user_key(user_id, {"chat_slice": slice})
    set_user_key(user_id, {"media_cell": slice})

    max = len(chat)
    precent = math.ceil((slice + 1) / max * 100)
    content = " ".join(chat[slice])
    return int(slice), max, precent, content, sources

# FUNCTION TO SET CHAT DESCRIPTION (PLACEHOLDER)
async def set_desc(user, desc):
    pass

# FUNCTION TO BAN USER FROM CHAT
async def ban(user, ban_from, msg, bot):
    if await ban_check(user, ban_from, msg):
        return 0
    chat_access = get_chat_key(ban_from, "access")
    chat_admin = get_chat_key(ban_from, "admin")
    chat_banned = get_chat_key(ban_from, "banned")
    orig_id = await get_orig_id(user)
    user_join = get_user_key(orig_id, "joined")
    for user in chat_access:
        if int(orig_id) == user:
            chat_access.remove(user)
    for user in chat_admin:
        if int(orig_id) == user:
            chat_admin.remove(user)
    for chat in user_join:
        if ban_from == chat:
            user_join.remove(ban_from)
    chat_banned.append(int(orig_id))
    set_chat_key(ban_from, {"access": chat_access, "admin": chat_admin, "banned": chat_banned})
    set_user_key(orig_id, {"joined": user_join})
    if get_user_key(orig_id, "redacting") == ban_from:
        set_user_key(orig_id, {"on_panel": ""})
    await msg_with_hide(texts["banned_spec"].format(user=await get_usercode(user), chat=ban_from), msg)

# FUNCTION TO GET USER TYPE IN CHAT
async def get_usertype(user_1, user_2, chat_id):
    user_1 = await get_usercode(user_1)
    if user_1 == user_2:
        usertype = "Вы"
    elif await get_orig_id(user_2) in get_chat_key(chat_id, "admin"):
        usertype = "Админ"
    else:
        usertype = "Пользователь"
    return usertype

# FUNCTION TO LISTEN FOR NEW MESSAGES
async def listener(msg: types.Message, chat_id, update_freq, user_id):
    msg_chat_id = msg.chat.id
    usercode = await get_usercode(user_id)
    await asyncio.sleep(update_freq)
    while get_user_key(user_id, "state") == chat_id:
        tick_0 = get_chat_key(chat_id, "messages")
        await asyncio.sleep(update_freq)
        tick_1 = get_chat_key(chat_id, "messages")
        if tick_0 != tick_1:
            counter = len(tick_0)
            length = counter
            for counter in range(len(tick_1) - counter):
                u_msg = tick_1[counter + length]
                split_template = u_msg.split(' ')
                user = split_template[0]
                date = split_template[1]
                src = split_template[2]
                text = " ".join(split_template[3:])
                usertype = await get_usertype(user_id, user, chat_id)
                if src == "":
                    await msg.answer(texts["message_template"].format(usercode=user, content=text, arg=usertype))
                else:
                    await msg.answer_photo(photo=src, caption=texts["message_template"].format(usercode=user, content=text, arg=usertype))
