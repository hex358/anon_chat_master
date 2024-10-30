import time
import json
import inspect
import asyncio
import traceback
from datetime import datetime

import aiogram.types

import funcs
import randomizer

last_usage = time.time()
new_usage = last_usage
report_types = json.load(open('base/console_texts.json', 'r'))
texts = json.load(open('base/messages.json', 'r', encoding='utf-8'))

def time_refresh():
    last_usage = time.time()

def _report(type, text, user=False, timed=False, process_id=""):
    global last_usage
    new_usage = time.time()
    run_time = new_usage - last_usage
    last_usage = new_usage
    output = f"{report_types[type]} *{process_id}* {str(user)+': ' if user else ""}{text} ({round(run_time,3) if timed else ""})"
    with open("logs.log", "a", encoding="utf-8") as logs:
        logs.write(f"{datetime.fromtimestamp(int(time.time()))} {output}\n")
    print(output)

def _big_report(text):
    c = int(20-(len(text)/2))
    output = f"{c*"="} {text} {c*"="}"
    with open("logs.log", "a", encoding="utf-8") as logs:
        logs.write(output+"\n")
    print(output)

def log(callable):
    async def wrapper(*argv):
        user = None
        id = ""
        func_type = type(argv[0])
        types = [aiogram.types.callback_query.CallbackQuery,
                             aiogram.types.message.Message]
        if func_type in types:
            user = argv[0].from_user.id
            id = randomizer.id_gen(25)

        time_refresh()
        _report("load", f"Executing command [[ {callable.__name__} ]] [[ {argv} ]]", user=user, process_id=id)
        try:
            await callable(*argv)
            _report("succ", f"Done", process_id=id, timed=True)
        except:
            if func_type == types[0]: await funcs.msg_with_hide(texts["error_code"].format(code=id), argv[0].message)
            elif func_type == types[1]: await argv[0].answer(texts["error_code"].format(code=id))
            _report("err", f"An error occured\n{traceback.format_exc()}", process_id=id)
    return wrapper