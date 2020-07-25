import flask
from flask import request, Response, jsonify, make_response, Flask
import os
import json
import urllib.parse
import ast
import pprint, sys
from slack import WebClient
from slackeventsapi import SlackEventAdapter

app = flask.Flask(__name__)
app.config['JSON_AS_ASCII'] = False

slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)

slack_client = WebClient(slack_bot_token)

@app.route('/')
def hello_world():
    return 'Hello World!'

@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    text = message.get('text')
    if "hi" in text:
        channel = message["channel"]
        message = "ss"
        slack_client.chat_postMessage(channel=channel, text=message)

@app.route('/interactive', methods=['POST'])
def interactive():
    data = request.form['payload']
    data_dict = json.loads(data)
    actions = data_dict['actions'][0] #text['text'] => ボタンのテキスト    value 設定したvalue(click_me_123)  type = button
    container = data_dict['container'] #channel_id, message_ts 
    user = data_dict['user']
    print(actions, container, user)
    if actions['text']['text'] == 'Approve' and actions['value'] == 'click_me_123':
        slack_client.chat_postMessage(channel=container['channel_id'], text='Approveが押されました。')
    response = jsonify({'message': data})
    response.status_code = 200
    return response



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)