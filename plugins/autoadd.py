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


def asmadd(newdata, database):
    olddata = database.dict_list()
    newnewdatas = []
    for data in newdata:
        # 過去に追加しているかみる
        for old in olddata:
            if data["subject"]+data["title"] == old["subject"]+old["title"]:
                break
        else:
            newnewdatas.append(data)
    
    for newnewdata in newnewdatas:
        database.add_dict(newnewdata)


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
            {"title": assignment["title"], "status": status, "limit_at": dueDate, "subject": assignment["subject"], "user": assignment["user"],})
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
    asmadd(newdata, database)
    # id整頓
    database.clean()
    print("finish")
    return 200