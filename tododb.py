import sqlite3
import datetime
import re
import time
from plugins import tools

DEFAULT = {"title": "Noname", "limit_at": "2999/12/31 23:59",
           "update_at": "2000/01/01 0:00", "status": "未", "noticetime": 3, "user": None}
DEFAULT_TYPE = {"title": "text NOT NULL", "limit_at": "text",
                "update_at": "text NOT NULL", "status": "text", "noticetime": "integer NOT NULL", "user": "text"}


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
        
        idの値がとびとびになってしまった際や列を追加した際にアップデートとして用いられる
        """
        dict_list = self.dict_list()
        self.__drop_table()
        self.__create_table()
        for i in range(len(dict_list)):
            # 本来ないはずだが不正なデータは追加しない
            if dict_list[i]["title"] == None or dict_list[i]["title"] == "None":
                continue
            if dict_list[i]["update_at"] == None or dict_list[i]["update_at"] == "None":
                continue
            self.add_dict(dict_list[i])


    
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


    def add_dict(self, data:dict)-> dict:
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
        if not re.match(r'^\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}$', newdata["limit_at"]):
            newdata["limit_at"] = DEFAULT["limit_at"]
        # 現在時刻取得
        update_at = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')
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
        datalist.append(update_at)
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
        now_f = str(now)[0:19]
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

    def dict_list(self) ->list:
        """ToDo DB の各データをそれぞれdictにして、dictのリストを返す

        戻り値の形
        [{データ1 dict},{データ2 dict},{データ3 dict}]
        """
        dict_list = []
        columns = self.__conn.execute("select * from todo").description
        for i in range(20):
            fromnum = i*50+1
            tonum = (i+1)*50
            for r in self.__c.execute(f"select * from todo WHERE id BETWEEN {fromnum} and {tonum}"):
                item = list(map(str, r))
                data = {}
                for i in range(len(columns)):
                    data[columns[i][0]] = item[i]
                    i += 1
                dict_list.append(data)
        return dict_list


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


