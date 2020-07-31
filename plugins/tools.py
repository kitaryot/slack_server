import os
import datetime
import requests
import json
import re
from dateutil.relativedelta import relativedelta


# 今後誰かが取得したくなった時の参考にchannel名、相手の名前等を取得する方法を載せておく
def getmsginfo(message)-> dict:
    """ユーザー情報をdict形式で返す
    現在得られるのは
    
    channel:チャンネル名(DMの場合はNone)
    
    channel_id:チャンネル固有のid

    user_id:ユーザー固有のid

    user_name:ユーザー名
    """
    info_dict={}
    try:
        info_dict["channel"] = message.channel._body["name"]
    except KeyError:
        info_dict["channel"] = None
    info_dict["channel_id"] = message.channel._body["id"]
    info_dict["user_id"] = message.user["id"]
    info_dict["user_name"] = message.user["real_name"]
    return info_dict


#userが入力した文字列(limit_at)を既定の形式に変換する
def datetrans(limit_at, now, mode=0):
    #　例で2020年8月16日19時18分のコマンドを記述しておく
    limit_at_str = ''
    date_format = "%Y%m%d%H%M"
    limit_at = limit_at.replace("/","")
    limit_at = limit_at.replace(":","")
    limit_at = limit_at.replace(" ","")
    length = len(limit_at)
    year_judge = False  # 年度判定が必要か否か
    if length == 12:
        # 年度＋月日＋時間      ex)202008161918
        limit_at_str = limit_at
    elif length == 8:
        if limit_at[0] == '2':
            # 初めが2なら年度＋月日  ex)20200816
            limit_at_str = limit_at + '2359'
        else:
            # 月日＋時間       ex)08161918
            limit_at_str = '2020' + limit_at
            year_judge = True
    elif length == 7:
        # 年度＋月日(1-9月)   ex)2020816　
        if limit_at[0] == '2' and limit_at[1] == '0':
            limit_at_str = limit_at[0:4] + '0' + limit_at[4:] + '2359'
        else:
            # 月日＋時間（1-9月）  ex)8161918
            limit_at_str = '20200' + limit_at
            year_judge = True
    elif length == 4:
        # 月日
        limit_at_str = '2020' + limit_at + '2359'
        year_judge = True
    elif length == 3:
        limit_at_str = '20200' + limit_at + '2359'
        year_judge = True
    elif length <= 2:
        try:
            # 2文字以下ならlimit_at日後
            l = now + datetime.timedelta(days=int(limit_at))
            limit_at_str = l.strftime(date_format)
            limit_at_str = limit_at_str[:-4] + '2359'
        except:
            return None

    if mode == 1:
        year_judge = False

    if len(limit_at_str) == 12:
        try:
            limit_at_format = datetime.datetime.strptime(
                limit_at_str, date_format)
            while limit_at_format < now and year_judge == True:
                # 2月29日->2月28日になる
                limit_at_format += relativedelta(years=1)
            limit_at_fin = limit_at_format.strftime('%Y/%m/%d %H:%M')
            return limit_at_fin
        except:
            # 日付が不正な場合はユーザーが入力した文字列を保存したいのでその処理は
            # add時に任せてNoneを返す
            return None
    else:
        return None


# datetime型でlimit_atを返す
def limit_datetime(assignment, mode=0):
    if mode == 0:
        duedate = assignment["dueDate"]
    elif mode == 1:
        duedate = assignment["limit_at"]  
    date_format = '%Y/%m/%d %H:%M'
    duedate_datetime = datetime.datetime.strptime(duedate, date_format)
    return duedate_datetime


def autostatus(assignment, now, mode=0):
    duedate = limit_datetime(assignment, mode)
    if now > duedate:
        status = "期限切れ"
    else:
        status = "未"
    return status

# messageをpost
def postMessage(text, attachments:list, channel="bot-test", username="お知らせ", icon_emoji=":snake:", as_user=False):
    headers = {
        'Authorization': 'Bearer '+os.environ['SLACK_BOT_TOKEN'],
        'Content-Type': 'application/json; charset=utf-8'
    }
    data = {
        "channel":channel,
        "username":username,
        "text":text,
        "attachments":attachments,
        "icon_emoji":icon_emoji,
        "as_user": as_user
    }
    url = 'https://slack.com/api/chat.postMessage'
    r_post = requests.post(url, headers=headers, json=data)
    return json.loads(r_post.text)

# messageを編集
# channelはユニークなchannel_idで指定する必要がある(postMessageはチャンネル名でpostできる)
def updateMessage(text, attachments:list, ts, channel, username="お知らせ", icon_emoji=":snake:"):
    headers = {
        'Authorization': 'Bearer '+os.environ['SLACK_BOT_TOKEN'],
        'Content-Type': 'application/json; charset=utf-8'
    }
    data = {
        "channel":channel,
        "username":username,
        "text":text,
        "attachments":attachments,
        "icon_emoji":icon_emoji,
        "ts":ts
    }
    url = 'https://slack.com/api/chat.update'
    r_post = requests.post(url, headers=headers, json=data)
    return json.loads(r_post.text)


def noticetimeSet(limit_at:datetime, now):
    diff = limit_at - now
    noticetime = 3
    if diff < datetime.timedelta(hours=1):
        noticetime = 0
    elif diff < datetime.timedelta(days=1):
        noticetime = 1
    elif diff < datetime.timedelta(days=3):
        noticetime = 2
    return noticetime