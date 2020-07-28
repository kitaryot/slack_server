import sqlite3

class UserDB(object):
    def __init__(self, name):
        self.__conn = sqlite3.connect(name)
        self.__c = self.__conn.cursor()

    def __create_table(self):
        sql = 'CREATE TABLE user(\
            id TEXT PRIMARY KEY,\
                 esc_id TEXT NOT NULL,\
                 password TEXT NOT NULL)'
        self.__c.execute(sql)

    def __drop_table(self):
        """テーブルを削除する

        user.dbというファイル自体は残る
        """
        self.__c.execute("drop table user")

    def init(self):
        "user.db作成時に最初に行う関数"
        self.__create_table()

    def reset(self):
        """一度テーブルを削除して再生成する

        このとき、テーブル内のデータはなくなる
        """
        self.__drop_table()
        self.__create_table()

    
    def select_id(self, id: str) -> dict:
        """idでデータを取得してdict形式で返す

        idが存在しない値であるときは全要素Noneで返す
        """
        # try:
        dict_list =[]
        columns = self.__conn.execute(f'select * from user').description
        for r in self.__conn.execute(f'select * from user where id=="{id}"'):
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
        # except:
        #      return None


    def add(self, id, esc_id, password) -> int:
        try:
            sql = f'INSERT INTO user(id, esc_id, password) \
                VALUES("{id}", "{esc_id}", "{password}")'
            self.__c.execute(sql)
            self.__conn.commit()
            return 200
        except sqlite3.Error:
            return 400


    def change_id(self, id: str, esc_id, password) -> int:
        """idを指定してesc_id, passwordを変更
           idが存在する場合200, しない場合300を返す
        """
        status_code = 300
        for db_id in self.__c.execute('select id from user'):
            if db_id[0] == id:
                try:
                    self.__c.execute(f'UPDATE user SET esc_id = "{esc_id}",\
                            password = "{password}" WHERE id = "{id}"')
                    self.__conn.commit()
                    status_code = 200
                    return status_code
                except sqlite3.Error:
                    status_code = 400
                    return status_code
        if status_code == 300:
            return status_code


    def dict_list(self) ->list:
        """user DB の各データをそれぞれdictにして、dictのリストを返す

        戻り値の形
        [{データ1 dict},{データ2 dict},{データ3 dict}]
        """
        dict_list = []
        columns = self.__conn.execute("select * from user").description
        for i in range(20):
            fromnum = i*50+1
            tonum = (i+1)*50
            for r in self.__c.execute(f"select * from user WHERE id BETWEEN {fromnum} and {tonum}"):
                item = list(map(str, r))
                data = {}
                for i in range(len(columns)):
                    data[columns[i][0]] = item[i]
                    i += 1
                dict_list.append(data)
        return dict_list

    def list_all(self) -> str:
        str_list ="userList:\n"
        for r in self.__c.execute("select * from user"):
            str_list += ', '.join(map(str, r))
            str_list += '\n'
        return str_list