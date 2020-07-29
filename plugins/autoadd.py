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


def asmadd(newdata):
    database = DB(os.environ['TODO_DB'])
    olddata = database.dict_list()
    for data in newdata:
        # 過去に追加しているかみる
        for old in olddata:
            # 過去verとの関係を保つためにorで二種類用意
            if data["subject"]+" "+data["title"] == old["title"] or(data["title"] == old["title"] and data["subject"] == old["subject"]):
                if old["status"] == "済":
                    # 過去に既に存在していて、済んでいる->"済"を引き継いだまま更新する
                    data["status"] = "済"
                # 旧情報を消す。
                database.delete_id(old["id"])
        database.add_dict(data)


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
            {"title": assignment["title"], "status": status, "limit_at": dueDate, "subject": assignment["subject"]})
    return newarr


def main():
    try:
        import pickle
        with open("data.dump", "rb") as f:
            newdata = pickle.load(f)
    except:
        # ログインをする。そのときのセッションを保存する
        session = login.login()
        # 続いて自分のページに移動し、教科ごとのURLを得る
        urls = login.tomypage(session)
        assignment = []
        # 各教科URLから課題を抽出
        for url in urls:
            data = gg.getassignment(session, url["url"], 0)
            # 課題リストにはsubject情報も加える
            for item in data:
                assignment.append(
                    {"title": item["title"], "status": item["status"], "dueDate": item["dueDate"], "subject": url["subject"]})
            print("課題 " + url["subject"]+" finished")

        # 各教科URLからテスト・クイズも抽出
        for url in urls:
            data = gg.getassignment(session, url["url"], 1)
            # リストにはsubject情報も加える
            for item in data:
                assignment.append(
                    {"title": item["title"], "status": item["status"], "dueDate": item["dueDate"], "subject": url["subject"]})
            print("テスト " + url["subject"]+" finished")
        # 得られた課題リストをDBに格納するために整える
        newdata = strarrange(assignment)

    # 追加
    asmadd(newdata)
    # id整頓
    tools.todo_clean('TODO_DB')

    print("finish")


@respond_to(r'todo\s+update$')
def todo_update(message):
    message.reply("少々時間がかかります。しばらくお待ちください。")
    main()
    msg = "todoリストを更新しました。"
    message.reply(msg)

@listen_to(r'^!update$')
def com_todo_update(message):
    todo_update(message)
