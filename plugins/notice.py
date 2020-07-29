import os
import datetime as dt
import time
from tododb import DB
from . import tools
from slack import WebClient
import pprint


class Notice():

    def __init__(self):
        self.__notice_notdone()

    def notice(self):
        self.__notice_notdone()

    def __notice_notdone(self) -> list:
        slack_client_n = WebClient(os.environ['SLACK_BOT_TOKEN'])
        self.now = dt.datetime.now()
        db = DB(os.environ['TODO_DB'])
        self.dict_list = db.dict_list()
        for dict in self.dict_list:
            noticetime = int(dict['noticetime'])
            try:
                self.__limit_at = dt.datetime.strptime(dict["limit_at"], '%Y/%m/%d %H:%M')
                # statusの更新
                if self.now > self.__limit_at and dict['status'] == '未':
                    db.change_id(dict['id'], 'status', '期限切れ')
            except:
                break
            color = ''
            text = ''
            post = False
            if dict["status"] == '未':                
                if self.__limit_at < self.now + dt.timedelta(hours=1) and noticetime == 1:
                    text = "期限まであと１時間。ひょっとして提出し忘れてるんじゃ？:face_with_rolling_eyes::face_with_rolling_eyes:"
                    noticetime = 0
                    color = 'ff4500'
                    post = True
                elif self.__limit_at < self.now + dt.timedelta(days=1) and noticetime == 2:
                    text = "期限まであと１日もありません！！のんびりしてる暇なんてありませんね:sweat_drops:"
                    noticetime = 1
                    color = 'ffff00'
                    post = True
                elif self.__limit_at < self.now + dt.timedelta(days=3) and noticetime == 3:
                    text = "期限まであと３日。そろそろとりかかろう...:sunglasses:"
                    noticetime = 2
                    color = '7cfc00'
                    post = True
            if post == True:
                attachments = [
                    {
                        "color":color,
                        "blocks": [
                            {
                                "type":"section",
                                "text":{
                                    "type":"mrkdwn",
                                    "text": '*'+ dict["title"] + '*\n' + '期限：' + dict["limit_at"] + '\nid：' + str(dict["id"])
                                }
                            },
                            {
                                "type": "acitons",
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
                                        "value": 'unfinished'
                                    }
                                ]
                            }
                        ]
                    }
                ]
                blocks = [  
                            {
                                "type": "section",
                                "text": {
                                    "type": "plain_text",
                                    "text": text,
                                    "emoji": True
                                }
                            },                 
                            {
                                "type": "section",
                                "block_id": "status",
                                "text":{
                                    "type":"mrkdwn",
                                    "text": '*'+ dict["title"] + '*\n' + '期限：' + dict["limit_at"] + '\nid：' + str(dict["id"])
                                }
                            },
                            {
                                "type": "actions",
                                "block_id": dict["user"],
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "完了！"
                                        },
                                        "style": "primary",
                                        "value": "finished",
                                        "action_id": str(dict["id"])
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "未完了:thinking_face:",
                                            "emoji": True
                                        },
                                        "value": "unfinished",
                                        "action_id": 'u'+ str(dict["id"])
                                    }
                                ]
                            }
                          ]
                db.change_id(dict['id'], 'noticetime', noticetime)
                slack_client_n.chat_postMessage(channel=dict["user"], blocks=blocks, as_user=True)
                # pprint.pprint(tools.postMessage(text, attachments, channel=os.environ['SLACK_CHANNEL']))
