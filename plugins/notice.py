import os
import datetime as dt
import time
from tododb import DB
from . import tools
import pprint


class Notice():

    def __init__(self):
        self.__notice_post(self.__notice_notdone())

    def notice(self):
        self.__notice_notdone()

    def __notice_post(self, notice_tasks:list):
        for task in notice_tasks:
            tools.postMessage(task["text"], task["attachments"], channel=task["channel"], as_user=True, icon_emoji=':panda_face:')


    def __notice_notdone(self) -> list:
        self.now = dt.datetime.now()
        db = DB(os.environ['TODO_DB'])
        self.dict_list = db.dict_list()
        self.channel = os.environ['SLACK_CHANNEL']
        self.notice_tasks = []
        for dict in self.dict_list:
            # 前バージョンとの互換性を保つ
            if not "noticetime" in dict.keys():
                continue
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
            post_dm = False
            post_announce = False
            attachments = []
            # 全体アナウンス
            if dict['user'] == 'all':
                if self.__limit_at < self.now + dt.timedelta(hours=1) and noticetime == 1:
                    text = '３日後の予定をお知らせします。'
                    noticetime = 0
                    color = 'ff4500'
                    post_announce = True
                elif self.__limit_at < self.now + dt.timedelta(days=1) and noticetime == 2:
                    text = '１日後の予定をお知らせします。'
                    noticetime = 1
                    color = 'ffff00'
                    post_announce = True
                elif self.__limit_at < self.now + dt.timedelta(days=3) and noticetime == 3:
                    text = '１時間後の予定をお知らせします。'
                    noticetime = 2
                    color = '7cfc00'
                    post_announce = True
            else:
                if dict["status"] == '未':                
                    if self.__limit_at < self.now + dt.timedelta(hours=1) and noticetime == 1:
                        text = "期限まであと１時間。ひょっとして提出し忘れてるんじゃ？:face_with_rolling_eyes::face_with_rolling_eyes:"
                        noticetime = 0
                        color = 'ff4500'
                        post_dm = True
                    elif self.__limit_at < self.now + dt.timedelta(days=1) and noticetime == 2:
                        text = "期限まであと１日もありません！！のんびりしてる暇なんてありませんね:sweat_drops:"
                        noticetime = 1
                        color = 'ffff00'
                        post_dm = True
                    elif self.__limit_at < self.now + dt.timedelta(days=3) and noticetime == 3:
                        text = "期限まであと３日。そろそろとりかかろう...:sunglasses:"
                        noticetime = 2
                        color = '7cfc00'
                        post_dm = True
            if post_dm == True:
                dict["limit_at"] = dict["limit_at"][5:]
                if dict["subject"] != 'None' and dict["note"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {"type": "mrkdwn",
                                            "text": ' *'+ dict["title"] + '* \n教科：'+ dict["subject"]+ '\n期限：'+ dict["limit_at"]+ '\n id ： `'+ str(dict["id"])+ '`'
                                    }
                                },  
                                {
                                    "type": "context",
                                    "elements": [
                                        {
                                            "type": "plain_text",
                                            "text": "※備考\n"+ dict["note"]
                                        }
                                    ]
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
                        }
                    ]
                elif dict["subject"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {"type": "mrkdwn",
                                            "text": ' *'+ dict["title"] + '* \n教科：'+ dict["subject"]+ '\n期限：'+ dict["limit_at"]+ '\n id ： `'+ str(dict["id"])+ '` '
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
                        }
                    ]                   
                elif dict["note"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {"type": "mrkdwn",
                                            "text": ' *'+ dict["title"] + '* \n期限：'+ dict["limit_at"]+ '\n id ： `'+ str(dict["id"])+ '` '
                                    }
                                },
                                {
                                    "type": "context",
                                    "elements": [
                                        {
                                            "type": "plain_text",
                                            "text": "※備考\n"+ dict["note"]
                                        }
                                    ]
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
                        }
                    ]
                else:
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn",
                                            "text": ' *'+ dict["title"] + '* \n期限：'+ dict["limit_at"]+ '\n id ： `'+ str(dict["id"])+ '` '
                                    }
                                }
                            ]
                        }
                    ]

            if post_announce == True:
                dict["user"] = self.channel
                dict["limit_at"] = dict["limit_at"][5:]
                if dict["subject"] != 'None' and dict["note"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {
                                        "type":"mrkdwn",
                                        "text": '*'+ dict["title"] + '* の情報です。\n教科：'+ dict["subject"]+ '\n日付：'+ dict["limit_at"]
                                    }
                                },
                                {
                                    "type": "context",
                                    "elements": [
                                        {
                                            "type": "plain_text",
                                            "text": "※備考\n"+ dict["note"]
                                        }
                                    ]
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
                        }
                    ]
                elif dict["subject"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {
                                        "type":"mrkdwn",
                                        "text": '*'+ dict["title"] + '* の情報です。\n教科：'+ dict["subject"]+ '\n日付：'+ dict["limit_at"]
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
                        }
                    ]                   
                elif dict["note"] != 'None':
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {
                                        "type":"mrkdwn",
                                        "text": '*'+ dict["title"] + '* の情報です\n日付：'+ dict["limit_at"]
                                    }
                                },
                                {
                                    "type": "context",
                                    "elements": [
                                        {
                                            "type": "plain_text",
                                            "text": "※備考\n"+ dict["note"]
                                        }
                                    ]
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
                        }
                    ]
                else:
                    attachments = [
                        {
                            "color": color,
                            "blocks": [
                                {
                                    "type": "section",
                                    "block_id": "status",
                                    "text": {
                                        "type":"mrkdwn",
                                        "text": '*'+ dict["title"] + '* の情報です\n日付：'+ dict["limit_at"]
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
                        }
                    ]                   

            if post_announce or post_dm:
                # tools.postMessage(text, attachments, channel=dict['user'], icon_emoji=":panda_face:")
                db.change_id(dict['id'], 'noticetime', noticetime)
                self.notice_tasks.append({"text": text, "attachments": attachments, "channel": dict["user"]})

        return self.notice_tasks


