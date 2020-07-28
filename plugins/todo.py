from slackbot.bot import respond_to
from tododb import DB
from . import tools
import os
import datetime

def todo_add(user, title, limit_at):
    # ユーザー情報取得
    data= {"title": title, "limit_at": limit_at,"user": user}
    database = DB(os.environ['TODO_DB'])
    now = datetime.datetime.now()
    limit_at_fin = tools.datetrans(limit_at, now)
    msg="以下の内容で"
    if limit_at_fin != None:
        limit_at_format = datetime.datetime.strptime(limit_at_fin, '%Y/%m/%d %H:%M')
        if now > limit_at_format:
            data["status"] = '期限切れ'
        noticetime = tools.noticetimeSet(limit_at_format, now)
        data["noticetime"]=noticetime
        data["limit_at"]=limit_at_fin
        msg += "、期限を正しく設定して"
    data = database.add_dict(data)
    msg += "追加しました。"
    for item in data.items():
        if item[0]=="user":
            continue
        msg+=f"\n{item[0]}: {item[1]}"
    return msg

def todo_add_unlimit(title):
    database = DB(os.environ['TODO_DB'])
    database.add(title, None)

def todo_list(user):
    database = DB(os.environ['TODO_DB'])
    data = database.search('user', user, mode=1)
    str_list = 'TODO list:\n'
    for r in data:
        str_list += ', '.join(map(str, r.values()))
        str_list += '\n'
    return str_list

def todo_list_all():
    database = DB(os.environ['TODO_DB'])
    return database.list()

def todo_reset():
    database = DB(os.environ['TODO_DB'])
    database.reset()
    return 'データベースを初期化しました'

def todo_search(text):
    msg = ''
    num = 0
    database = DB(os.environ['TODO_DB'])
    matched = database.search('title', text)
    if matched == []:
        msg = '一致するassigmentは存在しません'
    else:
        for data in matched:
            num += 1
            msg += f'\n{data["title"]}, 期限:{data["limit_at"]}, status:{data["status"]}, id:{data["id"]}'
        msg = f'一致するassignmentは以下の{num}件です。' + msg
    return msg

def todo_change_id(id, column, value):
    database = DB(os.environ['TODO_DB'])
    status_code = database.change_id(id, column, value)
    msg = ''
    if status_code == 400:
        msg = 'カラムが不正です'
    elif status_code == 401:
        msg = 'idが不正です'
    elif status_code == 402:
        msg = 'sqlite文が実行できません'
    elif status_code == 403:
        msg = 'limit_atを正しく入力してください'
    elif status_code == 404:
        msg = 'idまたはupdate_atを変更することはできません'
    elif status_code == 200:
        msg = '値を変更しました'
    return msg