from bs4 import BeautifulSoup
import requests
import time
import os


def login():
    # PandAのログインページ
    login_url = "https://cas.ecs.kyoto-u.ac.jp/cas/login"
    session = requests.session()
    time.sleep(1)
    html = session.get(login_url)
    soup = BeautifulSoup(html.text, "html.parser")
    # inputを全て取得
    inputs = soup.find_all("input")
    data = {}
    for tag in inputs:
        data[tag["name"]] = tag["value"]

    data["username"] = os.environ["PandA_username"]
    data["password"] = os.environ["PandA_password"]
    # 一応いらなさそうなものは消去
    del data["warn"]
    del data["reset"]
    session.post(login_url, data=data)
    return session


def tomypage(session):
    # ログインページに移動すると、sessionを保持しているのでマイページに移動
    url = "https://panda.ecs.kyoto-u.ac.jp/portal/login/"
    html = session.get(url)
    time.sleep(1)
    soup = BeautifulSoup(html.text, "html.parser")
    # 上の帯状の項目の各urlを取得
    lis = soup.find_all("li")
    subjects = []
    for data in lis:
        try:
            if data["class"] == ['nav-menu']:
                subjects.append(data.text.strip())
        except:
            continue

    datas = soup.find_all(lambda tag: tag.name == "a")
    urls = []
    for data in datas:
        try:
            if data["aria-haspopup"] == "true":
                urls.append(data["href"])
        except:
            continue
    response = []
    for i in range(len(subjects)):
        response.append({"url": urls[i+1], "subject": subjects[i]})

    #上の帯状の項目にない項目の各urlを取得
    setuppage_url = ""
    pages=soup.find_all('a', class_='toolMenuLink', href=True)
    for page in pages:
        if page["title"] == "サイトを修正したり新しいサイトを作成したりするためのツールです．" :
            setuppage_url = page["href"]

    html_setup = session.get(setuppage_url)
    time.sleep(1)
    soup=BeautifulSoup(html_setup.text, "html.parser")
    page_urls = []
    page_titles = []
    for ul in soup.find_all('ul', id = 'otherSiteList'):
        for i in ul.find_all('a', href = True, class_ = 'moreSitesLink'):
            page_urls.append(i["href"])
            page_titles.append(i["title"])

    for i in range(len(page_urls)):
        response.append({"url":page_urls[i], "subject":page_titles[i]})

    return response
