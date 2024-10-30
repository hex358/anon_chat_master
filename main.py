# IMPORTS
from pymongo import MongoClient
import ast

from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import F
from aiogram.methods.delete_messages import DeleteMessages

from randomizer import gen_alt

# LOAD ADDITIONAL FUNCTIONS
import funcs
from funcs import *
from wrappers import _big_report, _report, log

data = json.load(open('config.json', 'r'))
texts = json.load(open('base/messages.json', 'r', encoding='utf-8'))

# BOT SETUP AND START
_big_report("LAUNCHING")
_report("load", f"Loading MongoDB at {data["db_adress"]}")
client = MongoClient(data["db_adress"])
db = client['anon_chat']
users = db["users"]
userchats = db["chats"]

_report("load", "Loading bot")
default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(data["token"], default=default_properties)
funcs.bot = bot
dp = Dispatcher()

# COMMAND HANDLERS
@dp.message(Command('me'))
@log
async def profile_gen(msg: types.Message):
    await control_profile(msg.from_user.id, msg)

async def control_profile(user_id, message_to_answer, msg=False):
    if not msg:
        msg = await message_to_answer.answer(await my_profile(user_id))
    await profile_cell(msg, user_id, id_gen(8))
    reload_data = get_user_key(user_id, "profile_cell")
    await msg.edit_text(await my_profile(user_id), reply_markup=Inline.profile_control(Inline, user_id, reload_data))

@dp.message(Command('start'))
@log
async def start(msg: types.Message):
    if not locate_user(msg.from_user.id):
        await msg_with_hide(texts["welcome"], msg)
    else:
        await msg_with_hide(texts["welcome_alt"], msg)

@dp.message(Command('reg'))
@log
async def reg(msg: types.Message):
    user_id = msg.from_user.id
    usercode = gen_alt(6)
    if not locate_user(user_id):
        upload(users, set_up_user(user_id, usercode))
        await msg_with_hide(texts["reg_1"].format(u=usercode), msg)
    else:
        await msg_with_hide(texts["registered"].format(u=usercode), msg)

@dp.message(Command('menu'))
@log
async def menu(msg: types.Message):
    user_id = msg.from_user.id
    if not locate_user(user_id):
        await msg_with_hide(texts["reg_2"], msg)
        return
    await msg.answer(texts["u_main"], reply_markup=Inline.menu_a())

@dp.message(Command('create'))
@log
async def create(msg: types.Message):
    user_id = msg.from_user.id
    gen_name = gen(5)
    await set_up(gen_name, user_id)
    await msg_with_hide(texts["create"].format(id=gen_name), msg)
    append_key(users, {"orig": user_id}, {"joined": gen_name})

@dp.message(Command('export'))
@log
async def get(msg: types.Message):
    await load_get(msg.text.split(' ')[1], msg.from_user.id, msg)

@dp.message(Command('join'))
@log
async def join(msg: types.Message):
    args = msg.text.split(' ')[1:]
    user_id = msg.from_user.id
    chat_id = args[0]
    await join_id(user_id, chat_id, msg)

@dp.message(Command('open'))
@log
async def open_chat(msg: types.Message):
    args = msg.text.split(' ')[1:]
    user_id = msg.from_user.id
    chat_id = args[0]
    if chat_id in get_user_key(user_id, "joined"):
        desc = get_chat_key(chat_id, "description")
        host = get_chat_key(chat_id, "host")
        set_user_key(user_id, {"state": chat_id})
        await msg_with_hide(texts["open_1"].format(id=chat_id, desc=desc, host=host), msg)
        await asyncio.create_task(listener(msg, chat_id, 0.5, user_id))

@dp.message(Command('close'))
@log
async def close(msg: types.Message):
    user_id = msg.from_user.id
    set_user_key(user_id, {"state": "", "cooldown": 0})
    await msg_with_hide(texts["closed"], msg)

# ADMIN COMMANDS
@dp.message(Command('drop'))
@log
async def clear(msg: types.Message):
    if msg.from_user.id in data["admins"]:
        users.drop()
        userchats.drop()
        cache.drop()
        await msg.answer('Dropped databases')

@dp.message(Command('newsletter'))
@log
async def newsletter(msg: types.Message):
    content = msg.text.split(' ')[1]
    if msg.from_user.id in data["admins"]:
        await newsletter_handler(content)

@dp.message(Command('kill'))
@log
async def kill(msg):
    _big_report("KILLING BOT PROCESS")
    if msg.from_user.id in data["admins"]:
        await newsletter_handler("Bot was shut down")
        await dp.stop_polling()
        await bot.session.close()
    _big_report("BOT KILLED")

# CALLBACK REACTIONS
@dp.callback_query(lambda query: query.data.startswith('hide_get_data'))
@log
async def delete_media_callback(callback: types.CallbackQuery):
    args = callback.data.split(":")
    await delete_media(int(args[1]), callback.from_user.id, callback.message,int(args[2]))

async def delete_media(id,user,msg,modifier):
    chat = get_user_key(user, "getting")
    ids = get_cached(id, "media_cell", "ids")
    slice = get_user_key(user, "media_cell")
    data = await get_chat_sliced(chat, 256, user)
    sources = data[1][slice]

    if modifier == 0:
        buttons = Inline.arrows(Inline, slice if sources else -1, chat, id, opened=0)
    elif modifier == -1:
        buttons = Inline.down(Inline, slice if sources else -1, chat, id, opened=0)
    else:
        buttons = Inline.up(Inline, slice if sources else -1, chat, id, opened=0)

    await msg.edit_reply_markup(reply_markup=buttons)

    await bot.delete_messages(chat_id=msg.chat.id, message_ids=ids)
    set_user_key(user, {"status_opened": 0})
    set_user_key(user, {"media_cell": 0})
    delete_key(cache, {"id": id, "type": "media_cell"})


@dp.callback_query(lambda query: query.data.startswith('get_data'))
@log
async def get_data(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    set_user_key(user_id, {"status_opened": 1})
    chat, slice, modifier = callback.data.split(':')[1:4]
    slice, modifier = int(slice), int(modifier)
    unique = get_user_key(user_id, "media_id")

    data = await get_chat_sliced(chat, 256, user_id)
    sources = data[1][slice]
    media_group = MediaGroupBuilder(caption=f"Изображения чата {chat}")

    for source in sources:
        media_group.add_photo(media=source)

    msg_to_save = await callback.message.answer_media_group(media=media_group.build())

    if modifier == 0:
        buttons = Inline.arrows(Inline, slice if sources else -1, chat, unique, opened=1)
    elif modifier == -1:
        buttons = Inline.down(Inline, slice if sources else -1, chat, unique, opened=1)
    else:
        buttons = Inline.up(Inline, slice if sources else -1, chat, unique, opened=1)

    await callback.message.edit_reply_markup(reply_markup=buttons)
    await save_serialized(msg_to_save, unique, "media_cell", user_id, special=True)



async def handle_slice(callback, direction):
    user_id = callback.from_user.id
    unique = get_user_key(user_id, "media_id")
    slice, max_page, precent, content, sources = await modulate_slice(callback, direction)
    sources = sources[slice]

    status_opened = get_user_key(user_id, "status_opened")
    if status_opened:
        if direction == -1 and slice == 0:
            await delete_media(unique, user_id, callback.message, 1)
        elif direction == 1 and slice == max_page - 1:
            await delete_media(unique, user_id, callback.message, -1)
        else:
            await delete_media(unique, user_id, callback.message, 0)
    status_opened = 0

    message_text = texts["page_template"].format(page=slice + 1, max=max_page, precent=precent, text=content)
    buttons = Inline.arrows(Inline, slice if sources else -1, get_user_key(user_id, "getting"), unique,
                            opened=status_opened)

    if (direction == -1 and slice == 0) or (direction == 1 and slice == max_page - 1):
        buttons = Inline.up(Inline, slice if sources else -1, get_user_key(user_id, "getting"), unique,
                            opened=status_opened) if direction == -1 else Inline.down(Inline, slice if sources else -1,
                                                                                      get_user_key(user_id, "getting"),
                                                                                      unique, opened=status_opened)

    await callback.message.edit_text(message_text, reply_markup=buttons)


@dp.callback_query(lambda query: query.data == "slice_down")
@log
async def down(callback: types.CallbackQuery):
    await handle_slice(callback, -1)


@dp.callback_query(lambda query: query.data == "slice_up")
@log
async def up(callback: types.CallbackQuery):
    await handle_slice(callback, 1)

@dp.message(F.text)
@log
async def echo_message(msg: types.Message):
    user_id = msg.from_user.id
    state = get_user_key(user_id, "state")
    if state:
        if '<' in msg.text or '>' in msg.text:
            await msg_with_hide(texts["format_error"], msg)
            return
        await message_write(msg)

    current = get_user_key(user_id, "on_panel")
    if current == "allow":
        if await process_allow(msg.text, get_user_key(user_id, "redacting"), msg):
            await msg_with_hide(texts["success"], msg)
        set_user_key(user_id, {"on_panel": ""})
    elif current == "desc":
        set_user_key(user_id, {"description": msg.text, "on_panel": ""})
        await msg_with_hide(texts["success"], msg)
    elif current.split(':')[0] == "set_desc_chat":
        set_chat_key(current.split(':')[1], {"description": msg.text})
        set_user_key(user_id, {"on_panel": ""})
        await msg_with_hide(texts["success"], msg)
    elif current == "new_admin":
        await make_admin(msg.text, get_user_key(user_id, "redacting"), msg)
        await msg_with_hide(texts["success"], msg)
    elif current == "ban":
        await ban(msg.text, get_user_key(user_id, "redacting"), msg, bot)
        await msg_with_hide(texts["success"], msg)
    elif current == "joining":
        await join_id(user_id, msg.text, msg)
    set_user_key(user_id, {"on_panel": ""})

@dp.message(F.photo)
@log
async def echo_photo(msg: types.Message):
    time_now, user_id, username, sent, cooldown = await set_msg_data(msg)
    if not cooldown:
        chat_id = get_user_key(user_id, "state")
        usercode = get_user_key(user_id, "id")
        count = get_chat_key(chat_id, "message_count")
        if chat_id:
            set_chat_key(chat_id, {"message_count": count + 1})
            photo = msg.photo[-1].file_id
            await send_photo(msg, usercode, time_now, photo, chat_id)
            await asyncio.create_task(cd(user_id, 3))
    else:
        await cooldown_writer(user_id, msg)

# CALLBACK FUNCTIONS
@dp.callback_query(lambda query: query.data == "userlist")
@log
async def get_user_list(callback: types.CallbackQuery):
    output = 'Пользователи:'
    redacting = get_user_key(callback.from_user.id, "redacting")
    for user in get_chat_key(redacting, "access"):
        output += f'\n{get_user_key(user, "id")}'
    await callback.message.answer(output)

@dp.callback_query(lambda query: query.data == "allow")
@log
async def allow_user(callback: types.CallbackQuery):
    await msg_with_hide(texts["allow_ask"], callback.message)
    set_user_key(callback.from_user.id, {"on_panel": "allow"})

@dp.callback_query(lambda query: query.data.startswith('set_desc'))
@log
async def set_desc_chat(callback: types.CallbackQuery):
    args = callback.data.split(':')
    set_user_key(callback.from_user.id, {"on_panel": f"set_desc_chat:{args[1]}"})
    await msg_with_hide(texts["chat_desc_input"], callback.message)

@dp.callback_query(lambda query: query.data == "make_admin")
@log
async def new_admin(callback: types.CallbackQuery):
    args = callback.data.split(':')
    await bot.send_message(callback.from_user.id, texts["admin_ask"])
    set_user_key(callback.from_user.id, {"redacting": args[1], "on_panel": "new_admin"})

@dp.callback_query(lambda query: query.data == "ban_user")
@log
async def ban_user(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, texts["ban_ask"])
    set_user_key(callback.from_user.id, {"on_panel": "ban"})

@dp.callback_query(lambda query: query.data == "create")
@log
async def create_button(callback: types.CallbackQuery):
    await alt_create(callback.from_user.id, callback.message)

@dp.callback_query(lambda query: query.data.startswith('alt_open'))
@log
async def alt_open(callback: types.CallbackQuery):
    args = callback.data.split(':')
    chat_id = args[1]
    user_id = callback.from_user.id
    if chat_id in get_user_key(user_id, "joined"):
        desc = get_chat_key(chat_id, "description")
        host = await get_usercode(get_chat_key(chat_id, "host"))
        set_user_key(user_id, {"state": chat_id})
        await msg_with_hide(texts["open_1"].format(id=chat_id, desc=desc, host=host), callback.message)
        await asyncio.create_task(listener(callback.message, chat_id, 0.5, user_id))

@dp.callback_query(lambda query: query.data.startswith('hide_msg'))
@log
async def hide_msg(callback: types.CallbackQuery):
    args = callback.data.split(':')
    deserialized = get_cached(int(args[1]), "hide_cell", "content")
    msg = await serialize_one(deserialized, bot)
    delete_key(cache, {"id": int(args[1]), "type": "hide_cell"})
    await msg.delete()

@dp.callback_query(lambda query: query.data.startswith('get'))
@log
async def get_button(callback: types.CallbackQuery):
    args = callback.data.split(':')
    await load_get(args[1], args[2], callback.message, callback)

@dp.callback_query(lambda query: query.data.startswith('to_admin'))
@log
async def alt_admin(callback: types.CallbackQuery):
    args = callback.data.split(':')
    if int(args[1]) not in get_chat_key(args[2], "banned"):
        await make_admin(int(args[1]), args[2], callback.message)
        await msg_with_hide(texts["success"], callback.message)

@dp.callback_query(lambda query: query.data.startswith('to_ban'))
@log
async def alt_ban(callback: types.CallbackQuery):
    args = callback.data.split(':')
    await ban(await get_usercode(args[1]), args[2], callback.message, bot)

@dp.callback_query(lambda query: query.data.startswith('reload'))
@log
async def reload_profile(callback: types.CallbackQuery):
    args = callback.data.split(':')
    data = get_cached(int(args[1]), "profile_cell", "content")
    msg = await serialize_one(data, bot)
    await control_profile(callback.from_user.id, callback.message, msg=msg)

@dp.callback_query(lambda query: query.data.startswith('desc'))
@log
async def desc_set(callback: types.CallbackQuery):
    set_user_key(callback.from_user.id, {"on_panel": "desc"})
    await msg_with_hide(texts["desc_input"], callback.message)

async def button_match(current, button, callback, args):
    buttons = []
    await status_refresh(callback.from_user.id)
    content = " "
    match button:
        case 'main':
            content = texts["u_main"]
            buttons = Inline.menu_a()
        case 'chats':
            content = texts["u_chats"]
            set_user_key(callback.from_user.id, {"on_panel": "", "redacting": ""})
            buttons = Inline.menu_chats()
        case 'create':
            content = False
            buttons = Inline.menu_back_chats()
            await alt_create(callback.from_user.id, callback.message)
        case 'open':
            content = texts["u_select"]
            buttons = Inline.joined_gen()
        case 'redact':
            content = texts["u_chat_select"]
            buttons = None
        case 'join':
            content = False
            set_user_key(callback.from_user.id, {"on_panel": "joining"})
            await msg_with_hide(texts["join_ask"], callback.message)
        case 'chatpanel':
            set_user_key(callback.from_user.id, {"redacting": args[2]})
            desc = get_chat_key(args[2], "description")
            host = await get_usercode(get_chat_key(args[2], "host"))
            msgs = get_chat_key(args[2], "message_count")
            content = texts["chat_control"].format(book=texts[f"book_{Inline.book_emoji(Inline, args[2])}"], host=host, msgs=msgs, id=args[2], desc=desc)
            buttons = Inline.control_panel(Inline, args[2], callback, callback.from_user.id)
        case 'profile':
            content = False
            buttons = None
            await generate_profile(args[-1], False, callback)
        case 'list':
            content = texts["u_chat_list"]
            buttons = None
        case 'your_profile':
            content = False
            buttons = False
            await control_profile(callback.from_user.id, callback.message)
        case 'users_list':
            content = texts["user_select"]
            buttons = None
        case 'delete':
            await delete_chat(args[-1])
            content = texts["success"]
            buttons = Inline.deleted_prev(Inline)
        case 'delete_chat':
            content = texts["delete_ask"]
            buttons = Inline.delete_ask(Inline, args[2], callback)
        case 'delete_admin':
            content = False
            buttons = False
            await delete_admin(args[2], args[3], callback.message)
        case 'user_control':
            content = texts["user_control"].format(book=texts[f"book_{Inline.book_emoji(Inline, args[3])}"], user=await get_usercode(args[2]), chat=args[3])
            buttons = Inline.user_control(Inline, callback, args[2], args[3])
    return [content, buttons]

@dp.callback_query(lambda query: query.data.startswith('menu'))
@log
async def menu(callback: types.CallbackQuery):
    args = callback.data.split(':')
    button = args[1]
    current = callback.message.text
    output = await button_match(current, button, callback, args)
    content = output[0]
    buttons = output[1]
    if button == 'list':
        buttons = Inline.joined_gen(Inline, callback)
    elif button == 'users_list':
        buttons = Inline.users_gen(Inline, callback, get_user_key(callback.from_user.id, "redacting"))
    if content:
        await callback.message.edit_text(text=content, reply_markup=buttons)

async def newsletter_handler(content):
    for user in users.find():
        try:
            await bot.send_message(user["orig"], content)
            _report("load", "Sent newsletter", user["orig"])
        except:
            _report("load", "Error while sending newsletter", user["orig"])

# POLLING
async def main():
    _report("load", "Safe update")
    await safe_update(bot)
    _big_report("BOT LAUNCHED")
    await dp.start_polling(bot)

if __name__  == "__main__":
    asyncio.run(main())