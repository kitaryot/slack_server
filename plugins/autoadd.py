from .sub_autoadd import login
from .sub_autoadd import getassignment as gg
from bs4 import BeautifulSoup
from slackbot.bot import respond_to, listen_to
import requests
from tododb import DB
import time
import datetime
import os
import sqlite3
from . import tools
import asyncio


def asmadd(newdata, database, user_id):
    olddata = database.dict_list(mode=1, user_id=user_id)
    newnewdatas = []
    for data in newdata:
        # 過去に追加しているかみる
        for old in olddata:
            if data["subject"]+data["title"] == old["subject"]+old["title"]:
                break
        else:
            newnewdatas.append(data)
    
    for newnewdata in newnewdatas:
        todo_add_sub(user_id=user_id, data=newnewdata, database=database)


def todo_add_sub(user_id, data:dict, database, announce=False) -> str:
    """データ登録の際はこのtodo_add_subにmessageとデータのディクショナリを与えてください。

    戻り値は、登録内容をお知らせする文字列となっています。
    """
    # ユーザー情報取得
    if announce:
        data["user"]="all"
    else:
        data["user"]=user_id
    database = DB(os.environ['TODO_DB'])
    now = datetime.datetime.now()
    if "limit_at" in data.keys() or not "status" in data.keys():
        if not "limit_at" in data.keys() and not "status" in data.keys():
            data["limit_at"]=None
        limit_at_fin = tools.datetrans(data["limit_at"], now)
        msg="以下の内容で"
        if limit_at_fin != None or data["limit_at"] == None:
            if data["limit_at"] != None:
                limit_at_format = datetime.datetime.strptime(limit_at_fin, '%Y/%m/%d %H:%M')
                if now > limit_at_format:
                    data["status"] = '期限切れ'
                noticetime = tools.noticetimeSet(limit_at_format, now)
                data["noticetime"]=noticetime
                data["limit_at"]=limit_at_fin
            msg += "、期限を正しく設定して"
        else:
            return "limit_atの形が不正です。以下の入力例を参考にしてください。\n202008161918: 2020年8月16日19時18分となります。\n0816: 現在以降で最も早い8月16日23時59分となります。"
        data = database.add_dict(data)
        msg += "追加しました。"
        for item in data.items():
            if item[0]=="user":
                continue
            msg+=f"\n{item[0]}: {item[1]}"
        return msg
    if "status" in data.keys():
        data["noticetime"]=3
        data = database.add_dict(data)
        msg="以下の内容で追加しました。\n"
        for item in data.items():
            if item[0]=="user":
                continue
            msg+=f"\n{item[0]}: {item[1]}"
        return msg
    return "何らかの不具合により追加できません。"


def strarrange(assignments):
    newarr = []
    now = datetime.datetime.now()
    for assignment in assignments:
        if assignment["dueDate"] == "":
            dueDate = "2999/12/31 23:59"
            assignment["dueDate"] = dueDate
        else:
            dueDate = assignment["dueDate"]
        if "提出日時" in assignment["status"] or "返却"in assignment["status"]:
            status = "済"
        else:
            # status = "未"
            status = tools.autostatus(assignment, now)
        newarr.append(
            {"title": assignment["title"], "status": status, "limit_at": dueDate, "subject": assignment["subject"], "user": assignment["user"]})
    return newarr


def main(user, username, password, database):
    # try:
    #     import pickle
    #     with open("https://slack-interactive.herokuapp.com/tmp/data.dump", "rb") as f:
    #         newdata = pickle.load(f)
    # except:
    # ログインをする。そのときのセッションを保存する
    session = login.login(username, password)
    # 続いて自分のページに移動し、教科ごとのURLを得る
    urls = login.tomypage(session)

    if urls == None:
        return 400

    assignment = []

    # 各教科URLから課題を抽出        
    for url in urls:
        data = gg.getassignment(session, url["url"], 0)
        # 課題リストにはsubject情報も加える
        for item in data:
            assignment.append(
                {"title": item["title"], "status": item["status"], "dueDate": item["dueDate"], "subject": url["subject"], "user": user})
            
        print("課題 " + url["subject"]+" finished")


    # 各教科URLからテスト・クイズも抽出
    for url in urls:
        data = gg.getassignment(session, url["url"], 1)
        # リストにはsubject情報も加える
        for item in data:
            assignment.append(
                {"title": item["title"], "status": item["status"], "dueDate": item["dueDate"], "subject": url["subject"], "user": user})
        print("テスト " + url["subject"]+" finished")
    # 得られた課題リストをDBに格納するために整える
    newdata = strarrange(assignment)

    # 追加
    asmadd(newdata, database, user_id=user)
    # id整頓
    database.clean()
    print("finish")
    return 200