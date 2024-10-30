import json
from pymongo import MongoClient
import os

client = MongoClient('mongodb://localhost:27017/')
db = client['anon_chat']
users = db["users"]
userchats = db["chats"]
cache = db["cache"]

def upload(collection,content):
    collection.insert_one(content)

def key(collection, location, to_get):
    return collection.find_one(location)[to_get]


def set_key(collection, location, set):
    filter = location
    updated = {"$set": set}
    collection.update_one(filter, updated)

def set_user_key(user, set):
    filter = {"orig": user}
    updated = {"$set": set}
    users.update_one(filter, updated)

def get_user_key(user, to_get):
    return users.find_one({"orig": user})[to_get]

def get_chat_key(chat, to_get):
    return userchats.find_one({"name": str(chat)})[to_get]

def set_chat_key(chat, set):
    filter = {"name": chat}
    updated = {"$set": set}
    userchats.update_one(filter, updated)

def update_cached(id, type, set):
    filter = {"id": id, "type": type}
    updated = {"$set": set}
    cache.update_one(filter, updated)

def create_cached(id, type, user, start_set, ids=None):
    found = cache.find_one({"id": id, "type": type})
    if found:
        found["content"] = start_set
        found["ids"] = ids
        return 0
    cache.insert_one({"id": id, "type": type, "user": user, "content": start_set, "ids": ids})

def get_cached(id, type, to_get):
    return cache.find_one({"id": id, "type": type})[to_get]

def locate_user(orig_id):
    return users.find_one({"orig": orig_id})

def locate_chat(name_id):
    return userchats.find_one({"name": name_id})

def delete_key(collection, filter):
    return collection.delete_one(filter)

def append_key(collection, location, to_set):
    keys = list(to_set.keys())
    output = key(collection, location, keys[0])
    output.append(to_set[keys[0]])
    set_key(collection, location, {keys[0] : output})
    return output
