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
from plugins import todo
import re, threading, time
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

def noticeThread():
    nt = Notice()
    del nt
    

sched = BackgroundScheduler(daemon=True)
sched.add_job(func=noticeThread, trigger='interval', seconds=30)
sched.start()

atexit.register(lambda: sched.shutdown(wait=False))

app = flask.Flask(__name__)
# app.config['JSON_AS_ASCII'] = False

slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)
signature_verifier = SignatureVerifier(os.environ['SLACK_SIGNING_SECRET'])

slack_client = WebClient(slack_bot_token)


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
                # slack_client.chat_postMessage(text='登録に失敗しました。')
                print('failed')
                return make_response("", 400)

            return make_response("", 200)

        elif payload["type"] == "block_actions":
            if payload["actions"][0]["value"] == 'finished':
                task_user = payload["actions"][0]["block_id"]
                task_id = payload["actions"][0]["action_id"]
                if task_user == user_id:
                    database = DB(os.environ["TODO_DB"])
                    database.change_id(task_id, 'status', '済')
                return make_response("", 200)
            elif payload["actions"][0]["value"] == 'unfinished':
                task_user = payload["actions"][0]["block_id"]
                task_id = payload["actions"][0]["action_id"][1:]
                if task_user == user_id:
                    database = DB(os.environ["TODO_DB"])
                    database.change_id(task_id, 'status', '未')
                return make_response("", 200)

    return make_response("", 404)


@app.route("/slack/commands/panda", methods=["POST"])
def modal_post():
    command = SlashCommandInteractiveEvent(request.form)
    open_modal(command)
    return make_response("", 200)


def open_modal(command: SlashCommandInteractiveEvent):
    title = PlainTextObject(text="ID, password 入力フォーム")
    color_input_blocks = [InputBlock(label=PlainTextObject(text="esc_id"),
                                     element=PlainTextInputElement(placeholder="a020....", action_id='esc_id'), block_id='esc_id'),
                          InputBlock(label=PlainTextObject(text="Password"),
                                     element=PlainTextInputElement(placeholder="password", action_id='password'),
                                     block_id='password')]
    modal = views.View(type="modal", title=title, blocks=color_input_blocks, submit="Submit", callback_id='login')
    slack_client.views_open(trigger_id=command.trigger_id, view=modal.to_dict())


@slack_events_adapter.on("reaction_added")
def emoji_added(event_data):
    """userのリアクションに対するresponse
    """
    event = event_data["event"]
    pprint.pprint(event)
    emoji = event['reaction']
    channel = event['item']['channel']
    user_id = event['user']
    text = ":%s:" % emoji
    slack_client.chat_postMessage(channel=channel, text=text)

@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message.get("subtype") == None:
        text = message['text']
        channel = message['channel']
        user = message['user']
        if text[0] == '!':
            msg = ''
            text_body = text[1:]

            todo_add = re.search(r'^add\s+(\S+)\s+(\S+)$', text_body)
            todo_list = re.search(r'^list$', text_body)
            todo_list_all = re.search(r'^list\s+all$', text_body)
            todo_reset = re.search(r'^reset$', text_body)
            todo_search = re.search(r'^search\s+(\S+)$', text_body)
            todo_change_id = re.search(r'^change\s+(\S+)\s+(\S+)\s+(\S+)$', text_body)
            todo_short = re.search(r'short\s+(\S+)$', text_body)

            if todo_add:
                msg = todo.todo_add(user, todo_add.group(1), todo_add.group(2))
            elif todo_list:
                msg = todo.todo_list(user)
            elif todo_list_all:
                msg = todo.todo_list_all()
            elif todo_reset:
                msg = todo.todo_reset()
            elif todo_search:
                msg = todo.todo_search(todo_search.group(1))
            elif todo_change_id: 
                msg = todo.todo_change_id(todo_change_id.group(1), \
                    todo_change_id.group(2), todo_change_id.group(3))
            elif todo_short:
                msg = shorturl.short_url(todo_short.group(1))
            else:
                msg = 'このコマンドは無効です'
            
            slack_client.chat_postMessage(channel=channel, text=msg)
        
        if text == 'try':
            blocks =   [  
                            {
                                "type": "section",
                                "text": {
                                    "type": "plain_text",
                                    "text": text,
                                    "emoji": True
                                }
                            },                 
                            {
                                "type":"section",
                                "text":{
                                    "type":"mrkdwn",
                                    "text": '*遅れた*'
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "完了！"
                                        },
                                        "value": "finished"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "未完了:thinking_face:",
                                            "emoji": True
                                        },
                                        "value": "unfinished"
                                    }
                                ]
                            }
                        ]
            slack_client.chat_postMessage(channel=channel, blocks=blocks)
            attachments = [
                    {
                        "color": "ff4500",
                        "blocks":[
                            {
                                "type":"section",
                                "text":{
                                    "type":"mrkdwn",
                                    "text": '*試す*'
                                }
                            }
                        ]
                    }
            ]
            tools.postMessage("text", attachments)
            

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)