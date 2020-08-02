import sqlite3
import datetime
import re
import time
from plugins import tools

DEFAULT = {"title": "Noname", "limit_at": "2999/12/31 23:59",
           "update_at": "2000/01/01 0:00", "status": "未", "noticetime": 3, "user": None, "deleted": 0, "subject": None,"note": None,"importance": "中"}
DEFAULT_TYPE = {"title": "text NOT NULL", "limit_at": "text",
                "update_at": "text NOT NULL", "status": "text", "noticetime": "integer NOT NULL", "user": "text", "deleted":"bit", "subject": "text","note": "text","importance": "text NOT NULL"}


class DB(object):
    def __init__(self, name):
        self.__conn = sqlite3.connect(name)
        self.__c = self.__conn.cursor()

    def __create_table(self):
        keys = DEFAULT.keys()
        msg = "(id integer NOT NULL PRIMARY KEY AUTOINCREMENT"
        for key in keys:
            if key == "id":
                continue
            msg += f",{key} {DEFAULT_TYPE[key]}"
        msg += ")"
        self.__c.execute(f"create table todo {msg}")

    def __drop_table(self):
        """テーブルを削除する

        todo.dbというファイル自体は残る
        """
        self.__c.execute("drop table todo")

    def init(self):
        "todo.db作成時に最初に行う関数"
        self.__create_table()

    def reset(self):
        """一度テーブルを削除して再生成する

        このとき、テーブル内のデータはなくなる
        """
        self.__drop_table()
        self.__create_table()


    def clean(self):
        """一度テーブルを削除して再生成する

        このとき、テーブル内のデータは保たれる

        列を追加した際にアップデートとして用いられる
        """
        dict_list = self.dict_list(mode=1)
        self.__drop_table()
        self.__create_table()
        for i in range(len(dict_list)):
            # 本来ないはずだが不正なデータは削除データとして追加
            if dict_list[i]["title"] == None or dict_list[i]["title"] == "None":
                dict_list[i]["deleted"]=1
                dict_list[i]["limit_at"]=DEFAULT["limit_at"]
            self.add_dict(dict_list[i], update_update_at = 0)

    def delete_id(self, id: str, userid: str, secret = False) -> int:
        """指定したidのデータを削除する

        ユーザーに権限がない場合は-1を返す

        オプションで内容も初期化することが出来る。
        """
        if self.select_id(id)["user"]==userid:
            result = self.change_id(id, "deleted", 1)
            if result == 200 and secret:
                for key, value in DEFAULT.items():
                    if key=="deleted" or key=="id" or key=="update_at" or key=="user":
                        continue
                    result = self.change_id(id, key, value)
                    if result != 200:
                        break
        else:
            result = -1
        return result


    def select_id(self, id: str) -> dict:
        """idでデータを取得してdict形式で返す

        idが存在しない値であるときは全要素Noneで返すので注意
        """
        dict_list = []
        columns = self.__conn.execute("select * from todo").description
        for r in self.__c.execute(f"select * from todo where id=={id}"):
            item = list(map(str, r))
            data = {}
            for i in range(len(columns)):
                data[columns[i][0]] = item[i]
                i += 1
            dict_list.append(data)
        if len(dict_list) == 0:
            data = {}
            for i in range(len(columns)):
                data[columns[i][0]] = None
                i += 1
            dict_list.append(data)
        return dict_list[0]


    def add_dict(self, data:dict, update_update_at=1)-> dict:
        """追加するデータをdictionaryで受け取る

        引数 (self,追加したいデータ:dict)

        return 追加したデータ

        dictの要素の過不足はDEFAULTが補正してくれる
        """
        # 基本としてデフォルトを読み込む
        newdata = {}
        for key in DEFAULT.keys():
            newdata[key] = DEFAULT[key]
        dict_items = data.items()
        # dictの中身をnewdataに上書き
        for item in dict_items:
            if item[0] in newdata.keys():
                newdata[item[0]] = item[1]
        # ここで、limit_atがちゃんとフォーマットにあっているか見る
        if newdata["limit_at"]==None:
            newdata["limit_at"] = DEFAULT["limit_at"]
        if not re.match(r'^\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}$', newdata["limit_at"]):
            newdata["limit_at"] = DEFAULT["limit_at"]
        # 現在時刻取得
        update_at = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        # update_update_atによってupdate_atを更新するか決める
        if update_update_at == 1:
            newdata["update_at"] = update_at
        # sql文を作文
        msg1 = "insert into todo ("
        msg2 = "values("
        datalist = []
        for tag in newdata.keys():
            if tag == "update_at":
                continue
            msg1 += f"{tag},"
            msg2 += "?,"
            datalist.append(newdata[tag])
        msg1 += "update_at)"
        msg2 += "?)"
        datalist.append(newdata["update_at"])
        sql = msg1+msg2
        self.__c.execute(sql, datalist)
        self.__conn.commit()
        return newdata


    def change_id(self, id, column, value) -> int:
        """idを指定してcolumnの値をvalueに変更

        columnが不正の時 400, idが不正の時 401, 
        sql文が正常に実行できなかった時 402, columnがlimit_atで不正な値の時 403, columnにidまたはupdate_atを指定した時 404, 
        正常に処理が完了した時 200 を返す
        ただしcolumnが不正な場合, idについては調べないので両方が不正な場合は400を返す 
        """
        status_code = 400
        keys = DEFAULT.keys()
        now = datetime.datetime.now()
        now_f = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        if column == 'id' or column == 'update_at':
            status_code = 404
            return status_code
        if column == 'limit_at':
            status = '未'
            limit_at_fin = tools.datetrans(value, now)
            if limit_at_fin == None:
                status_code = 403
                return status_code
            else:
                limit_at_format = datetime.datetime.strptime(limit_at_fin, '%Y/%m/%d %H:%M')
                if now > limit_at_format:
                    status = '期限切れ'
                noticetime = tools.noticetimeSet(limit_at_format, now)
                try:
                    sql = f'UPDATE todo SET {column} = "{limit_at_fin}", \
                        status = "{status}", noticetime = "{noticetime}", \
                            update_at = "{now_f}" WHERE id = {id}'
                    self.__c.execute(sql)
                    self.__conn.commit()
                    status_code = 200
                except sqlite3.Error:
                    status_code = 402
                return status_code
        for key in keys:
            if key == column:
                status_code = 401
                for db_id in self.__c.execute('select id from todo'):
                    try:
                        if db_id[0] == int(id):
                            status_code = 200
                            break
                    except:
                        status_code = 401
        if status_code == 200:
            try:
                sql = f'UPDATE todo SET {column} = "{value}", \
                    update_at = "{now_f}" WHERE id = {id}'
                self.__c.execute(sql)
                self.__conn.commit()
            except sqlite3.Error:
                status_code = 402

        return status_code

    def add(self, title: str, limit_at: str):
        """title と limit_at (有効期限) を登録

        これは既存のシステムを保つためにあるものなので、add_dict()を使ってほしい
        """
        update_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.add_dict({"title":title,"limit_at":limit_at,"update_at":update_at})


    def list(self) -> str:
        """ToDo DB のデータを一覧した文字列を返す

        先頭には"TODO list:"がつくというおまけつき
        """
        str_list = "TODO list:\n"
        for r in self.__c.execute("select * from todo"):
            str_list += ', '.join(map(str, r))
            str_list += '\n'
        return str_list

    def dict_list(self, mode=0, show_over_deadline=1, user_id=None) -> list:
        """ToDo DB の各データをそれぞれdictにして、dictのリストを返す

        引数でmode=1とすると、削除されたデータを含めて取得

        引数でshow_over_deadline=0 とすると、期限切れのものを含めて取得、 2 とすると、期限切れと未のものを取得、
        3 とすると、未のものだけ取得

        引数でuser_id= ユーザーのid とすると、特定ユーザーのデータのみ取得

        戻り値の形
        [{データ1 dict},{データ2 dict},{データ3 dict}]
        """
        now = datetime.datetime.now()
        dict_list = []
        columns = self.__conn.execute("select * from todo").description
        for r in self.__c.execute(f"select * from todo"):
            item = list(map(str, r))
            data = {}
            for i in range(len(columns)):
                data[columns[i][0]] = item[i]
                i += 1
            # 削除済みのものはここで排除する。またint型に直すものを直す
            data["id"]=int(data["id"])
            data["noticetime"]=int(data["noticetime"])
            if "deleted" in data.keys():
                data["deleted"]=int(data["deleted"])
                if mode == 0 and data["deleted"] == 1:
                    continue
            # 期限切れのものを排除する
            if show_over_deadline == 0:
                if datetime.datetime.strptime(data["limit_at"], '%Y/%m/%d %H:%M')-now < datetime.timedelta(hours=0):
                    continue
            # 済のものを排除する
            if show_over_deadline == 2:
                if data["status"] == '済':
                    continue
            # 済、期限切れのものを排除する
            if show_over_deadline == 3:
                if data["status"] == '済' or data["status"] == '期限切れ':
                    continue
            # 他のユーザーのものを排除する
            if user_id != None:
                if data["user"] != user_id and data["user"] !="all":
                    continue
            dict_list.append(data)
        return dict_list

    def dict_list_sorted(self, keycolumn="limit_at", show_over_deadline=0, showdeleted=0, user_id=None) -> list:
        """ToDo DB の各データをそれぞれdictにして、dictのリストを返す

        全データ期限の早い順に並び変えられている。

        引数でkeycolumn= 列の名前 とすると、指定した列でソート（基本はlimit_at用なので、それ以外は対応していない可能性あり）

        引数でshowdeleted=1 とすると、削除されたデータを含めて取得

        引数でshow_over_deadline=0 とすると、期限切れのものを含めて取得

        引数でuser_id= ユーザーのid とすると、特定ユーザーのデータのみ取得

        戻り値の形
        [{データ1 dict},{データ2 dict},{データ3 dict}]
        """

        dict_list=self.dict_list(mode=showdeleted, show_over_deadline=show_over_deadline, user_id=user_id)
        data_sorted = sorted(dict_list, key=lambda x: tools.order(x[keycolumn],keycolumn))

        return data_sorted


    def search(self, column, text, mode=0) ->list:
        """columnの値にtextが含まれる場合そのデータをlist形式(要素はdict形式)で返す

        マッチするものがない場合、空のリストで返す
        mode=0の時, 検索モード, mode=1の時, 完全一致モード
        """
        matched = []
        dict_list = self.dict_list()
        text_compile = re.compile(text)
        for dict in dict_list:
            value = dict[column]
            if mode == 0:
                if text_compile.search(value):
                    matched.append(dict)
            elif mode == 1:
                if value == text:
                    matched.append(dict)
        return matched



