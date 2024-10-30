from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from math import sin
import json
from pymongo import MongoClient
from assets.randomizer import gen_split, gen
from assets.file_op import get_user_key, get_chat_key, append_key, set_user_key, set_chat_key

client = MongoClient('mongodb://localhost:27017/')
db = client['anon_chat']
users = db["users"]
userchats = db["userchats"]

texts = json.load(open('base/messages.json', 'r', encoding='utf-8'))

def usercode(id):
    user = users.find_one({"orig": id})
    return user["id"] if user else None

class Inline:
    def book_emoji(self, chat):
        return str(round(abs(sin(int(chat))) * 4))

    def control_panel(self, chat, callback, user):
        builder = InlineKeyboardBuilder()
        if not user in get_chat_key(chat, "banned"):
            builder.add(types.InlineKeyboardButton(
                text=texts["b_open"],
                callback_data=f"alt_open:{chat}:{callback.message.chat.id}")
            )
            builder.add(types.InlineKeyboardButton(
                text=texts["b_export"],
                callback_data=f"get:{chat}:{callback.from_user.id}")
            )
            builder.add(types.InlineKeyboardButton(
                text=texts["b_users"],
                callback_data="menu:users_list")
            )
            if user in get_chat_key(chat, "admin"):
                builder.add(types.InlineKeyboardButton(
                    text=texts["b_give_access"],
                    callback_data="allow")
                )
                builder.add(types.InlineKeyboardButton(
                    text=texts["b_set_desc"],
                    callback_data=f"set_desc:{chat}")
                )
            if chat in get_user_key(user, "host"):
                builder.add(types.InlineKeyboardButton(
                    text=texts["b_delete"],
                    callback_data=f"menu:delete_chat:{chat}")
                )

        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:list")
        )
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()

    def arrows(self,slice_pos,chat,message_id,opened=False):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="slice_down")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["next"],
            callback_data="slice_up")
        )
        if opened:
            builder.add(types.InlineKeyboardButton(
                text=f"Скрыть медиа",
                callback_data=f"hide_get_data:{message_id}:0")
            )
        elif slice_pos+1:
            builder.add(types.InlineKeyboardButton(
                text=f"Просмотр медиа",
                callback_data=f"get_data:{chat}:{slice_pos}:0")
            )
        builder.adjust(2)
        return builder.as_markup()

    def up(self,slice_pos,chat,message_id,opened=False):
        builder = InlineKeyboardBuilder()
        print(slice_pos)
        builder.add(types.InlineKeyboardButton(
            text=texts["next"],
            callback_data="slice_up")
        )
        if opened:
            builder.add(types.InlineKeyboardButton(
                text=f"Скрыть медиа",
                callback_data=f"hide_get_data:{message_id}:1")
            )
        elif slice_pos+1:
            builder.add(types.InlineKeyboardButton(
                text=f"Просмотр медиа",
                callback_data=f"get_data:{chat}:{slice_pos}:1")
            )
        builder.adjust(1,1)
        return builder.as_markup()

    def down(self,slice_pos,chat,message_id,opened=False):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data=f"slice_down")
        )
        if opened:
            builder.add(types.InlineKeyboardButton(
                text=f"Скрыть медиа",
                callback_data=f"hide_get_data:{message_id}:-1")
            )
        elif slice_pos+1:
            builder.add(types.InlineKeyboardButton(
                text=f"Просмотр медиа",
                callback_data=f"get_data:{chat}:{slice_pos}:-1")
            )
        builder.adjust(1)
        return builder.as_markup()

    def menu_a():
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["b_chats"],
            callback_data="menu:chats")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["b_profile"],
            callback_data="menu:your_profile")
        )
        builder.adjust(1)
        return builder.as_markup()

    def delete_ask(self, chat, callback):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["yes"],
            callback_data=f"menu:delete:{chat}")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["no"],
            callback_data=f"menu:chatpanel:{chat}:{callback.message.chat.id}")
        )
        builder.adjust(2)
        return builder.as_markup()

    def deleted_prev(self):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:list")
        )
        builder.adjust(1)
        return builder.as_markup()

    def menu_chats():
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["b_chat_select"],
            callback_data="menu:list")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["b_create"],
            callback_data="create")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["b_join"],
            callback_data="menu:join")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:main")
        )
        builder.adjust(2, 2)
        return builder.as_markup()

    def profile_control(self, user, reload_msg):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["p_desc"],
            callback_data=f"desc:{user}")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["p_reload"],
            callback_data=f"reload:{reload_msg}")
        )
        builder.adjust(2, 2)
        return builder.as_markup()

    def menu_back_chats():
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:chats")
        )
        builder.adjust(1)
        return builder.as_markup()

    def joined_gen(self, callback):
        builder = InlineKeyboardBuilder()
        for chat in get_user_key(callback.from_user.id, "joined"):
            try:
                builder.add(types.InlineKeyboardButton(
                    text=f'{chat} {texts["book_" + self.book_emoji(Inline, chat)]}',
                    callback_data=f"menu:chatpanel:{chat}:{callback.message.chat.id}"
                ))
            except Exception as e:
                print(e)
                pass

        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:chats")
        )
        builder.adjust(2)
        return builder.as_markup()

    def hide(self, message_id):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text=texts["hide"],
            callback_data=f"hide_msg:{message_id}")
        )
        builder.adjust(2)
        return builder.as_markup()

    def users_gen(self, callback, chat):
        builder = InlineKeyboardBuilder()
        for user in get_chat_key(chat, "access"):
            if not user == callback.from_user.id:
                builder.add(types.InlineKeyboardButton(
                    text=f'👤 {usercode(user)}',
                    callback_data=f"menu:user_control:{user}:{chat}"
                ))

        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data=f"menu:chatpanel:{chat}")
        )
        builder.adjust(2)
        return builder.as_markup()

    def user_control(self, callback, user, from_chat):
        user = int(user)
        builder = InlineKeyboardBuilder()
        if (callback.from_user.id in get_chat_key(from_chat, "admin") and
                (not user in get_chat_key(from_chat, "admin")) or
                from_chat in get_user_key(callback.from_user.id, "host")):
            builder.add(types.InlineKeyboardButton(
                text=texts["b_ban"],
                callback_data=f"to_ban:{user}:{from_chat}")
            )

        if (from_chat in get_user_key(callback.from_user.id, "host")
                and user in get_chat_key(from_chat, "admin")):
            builder.add(types.InlineKeyboardButton(
                text=texts["b_delete_admin"],
                callback_data=f"menu:delete_admin:{user}:{from_chat}")
            )
        elif from_chat in get_user_key(callback.from_user.id, "host"):
            builder.add(types.InlineKeyboardButton(
                text=texts["b_admin"],
                callback_data=f"to_admin:{user}:{from_chat}")
            )

        builder.add(types.InlineKeyboardButton(
            text=texts["b_other_profile"],
            callback_data=f"menu:profile:{user}")
        )
        builder.add(types.InlineKeyboardButton(
            text=texts["prev"],
            callback_data="menu:users_list")
        )
        builder.adjust(2, 2, 1)
        return builder.as_markup()

class Keyboard:
    pass
