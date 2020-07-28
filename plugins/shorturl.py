import requests, json, os
from slackbot.bot import respond_to

bitly_token = os.environ['Bitly_Token']

def get_shortUrl(longUrl):
    url = 'https://api-ssl.bitly.com/v4/shorten'
    headers = {
        'Authorization':'Bearer ' + bitly_token,
        'Content-Type':'application/json',
        'Host':'api-ssl.bitly.com',
        'Accept':'application/json'
    }
    group_guid = get_group_guid()
    query = {
        'group_guid': group_guid['groups'][0]['guid'],
        'domain':'bit.ly',
        'long_url': longUrl
    }
    response = requests.post(url, json=query, headers=headers)
    return response.json()


def get_group_guid() -> dict:
    url = 'https://api-ssl.bitly.com/v4/groups'
    headers = {
        'Authorization':'Bearer '+ bitly_token,
        'Accept':'application/json'
    }
    group_guid = requests.get(url, headers=headers)
    if group_guid.status_code == 200:
        return group_guid.json()
    else:
        return None

def short_url(longUrl):
    longUrl = longUrl.replace('<','')
    longUrl = longUrl.replace('>','')
    response = get_shortUrl(longUrl)
    return response['link']