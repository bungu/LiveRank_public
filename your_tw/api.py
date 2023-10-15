import requests
import json
import os

def take_tweets(authorization_code,code_verifier): # アクセストークンをurlから取得
    # json内の情報を用いてアクセストークンをTwitterAPIにリクエスト,取得
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = f"code={authorization_code}&grant_type=authorization_code&client_id={os.environ['CLIENT_ID']}&redirect_uri={os.environ['REDIRECT_URI']}&code_verifier={code_verifier}"
    response = requests.post('https://api.twitter.com/2/oauth2/token', headers=headers, data=data, auth=(f"{os.environ['CLIENT_ID']}", f"{os.environ['CLIENT_SECRET']}"))
    
    json_response = json.loads(response.text)
    # print(json_response["access_token"])
    access_token = json_response["access_token"]

    # 取得したアクセストークンを用いてuserid(整数)をTwitterAPIにリクエスト,取得
    headers = {
        'Authorization': 'Bearer '+ access_token,
    }
    response = requests.get('https://api.twitter.com/2/users/me', headers=headers)

    json_response = json.loads(response.text)
    id_ = json_response["data"]["id"]

    # userid,アクセストークンを用いて指定したユーザーの直近ツイートをリクエスト,取得
    headers = {
        'Authorization': 'Bearer '+ access_token,
    }
    # ここのmax_resultsの値でツイート取得件数を調整
    response = requests.get('https://api.twitter.com/2/users/'+id_ + '/tweets/?max_results=100', headers=headers)
    json_response = json.loads(response.text)

    # ツイートを配列に起こす
    tweets = []
    for i in json_response["data"]:
        tweets.append(i["text"])

    print(tweets)

    return tweets