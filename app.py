import flask
from flask import request, Response, jsonify, make_response, Flask
import os
import json
import urllib.parse
import ast
import pprint, sys
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from slack.web.classes.interactions import SlashCommandInteractiveEvent
from slack.web.classes import views
from slack.web.classes.blocks import InputBlock
from slack.web.classes.elements import PlainTextInputElement, PlainTextObject, ConversationMultiSelectElement, ConversationSelectElement
from slack.web.classes.objects import PlainTextObject
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier
from slack.web.classes.views import View
from userdb import UserDB
from plugins import todo, autoadd
import re, threading, time, datetime
from tododb import DB
from plugins.notice import Notice
from plugins import shorturl
from plugins import tools
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

user_dbname = 'user.db'
user_need_init = not os.path.exists(user_dbname)
user_database = UserDB(user_dbname)
if user_need_init:
    user_database.init()

dbname = os.environ['TODO_DB']
need_init = not os.path.exists(dbname)
database = DB(dbname)
if need_init:
    database.init()
database.clean()

def noticeThread():
    nt = Notice()
    del nt

panda_database_names = {}

sched = BackgroundScheduler(daemon=True)
panda_sched = BackgroundScheduler(deamon=True)
sched.add_job(func=noticeThread, trigger='interval', seconds=180)
sched.start()
panda_sched.start()

atexit.register(lambda: sched.shutdown(wait=False))
atexit.register(lambda: panda_sched.shutdown(wait=False))

app = flask.Flask(__name__)
# app.config['JSON_AS_ASCII'] = False

slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)
signature_verifier = SignatureVerifier(os.environ['SLACK_SIGNING_SECRET'])
slack_user_token = os.environ["SLACK_USER_TOKEN"]

slack_bot_client = WebClient(slack_bot_token)
# slack_user_client = WebClient(slack_user_token)


@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route("/slack/interactions", methods=["POST"])
def slack_app():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)

    if "payload" in request.form:
        payload = json.loads(request.form["payload"])
        user_id = payload["user"]["id"]

        if payload["type"] == "view_submission" \
            and payload["view"]["callback_id"] == "login":
            # Handle a data submission request from the modal
            submitted_data = payload["view"]["state"]["values"]            
            # {'block-id': {'action_id': {'type': 'plain_text_input', 'value': 'your input'}}}
            esc_id = submitted_data['esc_id']['esc_id']['value']
            password = submitted_data['password']['password']['value']
            status_code = user_database.change_id(user_id, esc_id, password)
            if status_code == 300:
                status_code = user_database.add(user_id, esc_id, password)
            if status_code == 400:
                slack_bot_client.chat_postMessage(text='登録に失敗しました。', channel=user_id, as_user=True)
                print('failed')
                return make_response("", 400)

            # if status_code == 200 or status_code == 300:
            #     chat = slack_bot_client.chat_postMessage(channel=user_id, text='更新中...しばらくお待ちください', as_user=True)
            #     login_data = user_database.select_id(user_id)

            #     # def pandaThread():
            #     #     login_data = user_database.select_id(user_id)
            #     #     panda_database_names[user_id]  = DB(os.environ["TODO_DB"])
            #     #     status_code = autoadd.main(user=login_data["id"], username=login_data["esc_id"], password=login_data["password"], database=panda_database_names[user_id])
            #     #     if status_code == 400:
            #     #         slack_bot_client.chat_update(channel=chat["channel"], text='esc-idとパスワードが間違っています。\n/pandaコマンドを入力して再登録してください', ts=chat["ts"], as_user=True)
            #     #     elif status_code == 200:
            #     #         print('pandaThread終了')
            #     #         if chat != None:
            #     #             slack_bot_client.chat_update(channel=chat["channel"], text='更新が終了しました', ts=chat["ts"], as_user=True)
            #     #             msg = todo.todo_list(user_id) 
            #     #             slack_bot_client.chat_postMessage(channel=chat["channel"], text=msg, as_user=True)      

            #     if panda_sched.get_job(user_id) != None:
            #         panda_sched.remove_job(user_id)
            #     panda_sched.add_job(func=pandaThread, trigger='interval', minutes=30, id=login_data["id"], next_run_time=datetime.datetime.now())
            

            return make_response("", 200)

        elif payload["type"] == "block_actions":
            task_user = payload["actions"][0]["block_id"]
            text = ''                
            channel = payload["channel"]["id"]
            if payload["actions"][0]["value"] == 'finished':
                task_id = payload["actions"][0]["action_id"]
                if task_user == user_id:
                    database = DB(os.environ["TODO_DB"])
                    database.change_id(task_id, 'status', '済')
                    text = 'id:' + task_id + 'を完了しました'
            elif payload["actions"][0]["value"] == 'unfinished':
                task_id = payload["actions"][0]["action_id"][1:]
                if task_user == user_id:
                    database = DB(os.environ["TODO_DB"])
                    database.change_id(task_id, 'status', '未')
                    text = 'id:' + task_id + 'を未完了に変更しました'
            slack_bot_client.chat_postMessage(channel=channel, text=text)
            return make_response("", 200)

    return make_response("", 404)


@app.route("/slack/commands/panda", methods=["POST"])
def modal_post():
    command = SlashCommandInteractiveEvent(request.form)
    open_modal(command)
    return make_response("", 200)


def open_modal(command: SlashCommandInteractiveEvent):
    title = PlainTextObject(text="ID, password 入力フォーム")
    color_input_blocks = [InputBlock(label=PlainTextObject(text="esc-id"),
                                     element=PlainTextInputElement(placeholder="a020....", action_id='esc_id'), block_id='esc_id'),
                          InputBlock(label=PlainTextObject(text="Password"),
                                     element=PlainTextInputElement(placeholder="password", action_id='password'),
                                     block_id='password')]
    modal = views.View(type="modal", title=title, blocks=color_input_blocks, submit="Submit", callback_id='login')
    slack_bot_client.views_open(trigger_id=command.trigger_id, view=modal.to_dict())


@slack_events_adapter.on("reaction_added")
def emoji_added(event_data):
    """userのリアクションに対するresponse
    """
    event = event_data["event"]
    emoji = event['reaction']
    channel = event['item']['channel']
    ts = event['item']['ts']
    user_id = event['user']
    text = ":%s:" % emoji
    slack_bot_client.chat_postMessage(channel=channel, text=text)

@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message.get("subtype") == None:
        text = message['text']
        channel = message['channel']
        user = message['user']
        ts = message['ts']
        if text[0] == '!':
            msg = ''
            text_body = text[1:]

            todo_add = re.search(r'^add\s+(\S+)\s+(\S+)$', text_body)
            todo_list = re.search(r'^list', text_body)
            todo_list_all = re.search(r'^list\s+all$', text_body)
            todo_list_all_users = re.search(r'^list\s+all\s+users$', text_body)
            todo_reset = re.search(r'^reset$', text_body)
            todo_search = re.search(r'^search\s+(\S+)$', text_body)
            todo_change_id = re.search(r'^change\s+(\S+)\s+(\S+)\s+(\S+)$', text_body)
            todo_delete = re.search(r'^delete\s+(\S+)', text_body)
            todo_delete_secret = re.search(r'^delete_secret\s+(\d+)$', text_body)
            todo_short = re.search(r'^short\s+(\S+)$', text_body)
            todo_update = re.search(r'^update$', text_body)
            todo_cancel_announcement = re.search(r'^cancel\s+announcement\s+(\d+)$', text_body)
            todo_finish = re.search(r'^finish\s+(.*)', text_body)

            if todo_add:
                msg = todo.todo_add(user, todo_add.group(1), todo_add.group(2))
            elif todo_list:
                msg = todo.todo_list(user)
            elif todo_list_all:
                msg = todo.todo_list(user)
            elif todo_list_all_users:
                msg = todo.todo_list_all()
            elif todo_reset:
                msg = todo.todo_reset()
            elif todo_search:
                msg = todo.todo_search(todo_search.group(1))
            elif todo_change_id: 
                msg = todo.todo_change_id(todo_change_id.group(1), \
                    todo_change_id.group(2), todo_change_id.group(3))
            elif todo_delete_secret:
                msg = todo.todo_delete_secret(user, todo_delete_secret.group(1))
            elif todo_short:
                msg = shorturl.short_url(todo_short.group(1))
            elif todo_delete:
                msg = todo.todo_delete(user, todo_delete.group(1))
            elif todo_cancel_announcement:
                msg = todo.todo_cancel_announcement(todo_cancel_announcement.group(1))
            elif todo_finish:
                msg = todo.todo_finish(user, todo_finish.group(1))

            # elif todo_complete_delete_id:
            #     result = database.complete_delete_id(todo_complete_delete_id.group(1), user)
            #     if result == -1:
            #         msg = 'データの完全消去に失敗しました'
            #     else:
            #         msg = 'データを完全に消去しました'
            elif todo_update: 
                login_data = user_database.select_id(user)
                if login_data["id"] == None:
                    slack_bot_client.chat_postMessage(channel=channel, text='esc-idとパスワードが未登録です。\n/pandaコマンドを入力して登録してください')
                else:
                    chat = slack_bot_client.chat_postMessage(channel=channel, text='更新中...２分ほど要します。しばらくお待ちください。')  

                    if panda_sched.get_job(user) != None:
                        panda_sched.remove_job(user)
                    panda_sched.add_job(func=pandaThread, trigger='interval', \
                        args=[login_data["id"], login_data["esc_id"], login_data["password"], channel, chat["ts"]], \
                            minutes=15, id=login_data["id"], next_run_time=datetime.datetime.now())


                # chat = slack_bot_client.chat_postMessage(channel=channel, text='更新中です...')
                # autoadd.main(user=login_data["id"], username=login_data["esc_id"], password=login_data["password"], database=database)
                # autoadd.main(user=login_data["id"], username=login_data["esc_id"], password=login_data["password"], database=database, mode=1)
            else:
                msg = 'このコマンドは無効です'
            
            if msg != '':
                chat = slack_bot_client.chat_postMessage(channel=channel, text=msg, unfurl_links=False)

def pandaThread(user, esc_id, password, channel, ts):
    panda_database_names[user]  = DB(os.environ["TODO_DB"])
    status_code = autoadd.main(user=user, username=esc_id, password=password, database=panda_database_names[user])
    if status_code == 400:
        slack_bot_client.chat_update(channel=channel, text='esc-idまたはパスワードが間違っています。\n/pandaコマンドを入力して再登録してください', ts=ts)
    elif status_code == 200:
        print('pandaThread終了')
        try:
            slack_bot_client.chat_update(channel=channel, text='更新が終了しました', ts=ts)      
            msg = todo.todo_list(user)
            slack_bot_client.chat_update(channel=channel, text=msg, ts=ts)
        except:
            print('failed')
    del panda_database_names[user]


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)