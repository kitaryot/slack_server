import requests
from bs4 import BeautifulSoup
import time


def getframe(session, url):
    html = session.get(url)
    time.sleep(0.3)
    soup = BeautifulSoup(html.text, "html.parser")
    frame = soup.find("iframe")
    return frame["src"]


def getasmdata(session, url):
    html = session.get(url)
    time.sleep(0.3)
    soup = BeautifulSoup(html.text, "html.parser")
    trs = soup.find_all("tr")
    assignments = []
    for tr in trs:
        try:
            data = {}
            # headerから課題情報を取得
            for header in ["title", "dueDate", "status"]:
                data[header] = tr.find("td", headers=header).text.strip()
            assignments.append(data)
        except:
            pass
    return assignments


def gettestdata(session, url):
    html = session.get(url)
    time.sleep(0.3)
    soup = BeautifulSoup(html.text, "html.parser")
    tbodies = soup.find_all("tbody")
    assignments = []
    # 現在取り組めるテストは[0]に格納されている
    tbody = tbodies[0]
    try:
        trs = tbody.find_all("tr")

        for tr in trs:
            data = {"title": "", "dueDate": "", "status": ""}
            tds = tr.find_all("td")

            # 時間表記が課題と大幅に異なるので整える
            date = tds[2].text
            date = date.replace("-", " ")
            date = date.replace(":", " ")
            date = date.replace("-", " ")
            elements = date.split()
            if len(elements) == 1:
                data["dueDate"] = ""
            else:
                for i in [1, 2]:
                    if len(elements[i]) == 1:
                        elements[i] = "0"+elements[i]
                if elements[5] == "午後":
                    elements[3] = str(12+int(elements[3]))
                data["dueDate"] = elements[0]+"/"+elements[1] + \
                    "/"+elements[2]+" "+elements[3]+":"+elements[4]
            data["title"] = tds[0].text.strip()
            data["status"] = ("未")

            assignments.append(data)
    except:
        pass
    return assignments


def getassignment(session, url, mode):
    # mode:0->assignment 1->test
    html = session.get(url)
    time.sleep(0.3)
    soup = BeautifulSoup(html.text, "html.parser")
    # 課題をnextsに格納。特殊な場合を除き1ページに一つしかない。
    if mode == 0:
        nexts = soup.find_all(lambda tag: tag.name == "a" and (
            "課題" == tag.text.strip() or "Assignment" == tag.text.strip() or "課題/Assignment" == tag.text.strip()))
    if mode == 1:
        nexts = soup.find_all(lambda tag: tag.name == "a" and (
            "テスト・クイズ" == tag.text.strip()))

    assignments = []
    for data in nexts:
        try:
            nexturl = data["href"]
            # ページに埋め込まれた課題が表示されているframeのurlを取得
            frame = getframe(session, nexturl)
        except:
            continue
        if mode == 0:
            asmdata = getasmdata(session, frame)
        if mode == 1:
            asmdata = gettestdata(session, frame)
        assignments.extend(asmdata)
    return assignments
