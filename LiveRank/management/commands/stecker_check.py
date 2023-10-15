

from django.core.management.base import BaseCommand

from django.http import HttpResponse
from django.shortcuts import redirect
from django.db.models import Max, Q
from django.core.paginator import Paginator

from LiveRank.models import Master,Tags,Main,Main_Last1month,Main_Tops
from LiveRank.forms import OrderForm,FindForm

from time import sleep
from datetime import date, timedelta, datetime
import random
import math

from apiclient.discovery import build

import pytchat
from pytchat import SuperchatCalculator,LiveChat
import requests, json

import pprint


class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Check()

def Check():

    videoid = "UX6IDuP1Hdw"

    # 通貨の配列を作っておく
    url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
    text = url.text
    json_currency = json.loads(text)

    # youtubeapiを起動
     # herokuにはアップロードされているがGithubには非公開
    youtube = build("youtube","v3",developerKey="")
    
    response = youtube.videos().list(
        part = 'snippet',
        id= '{},'.format(videoid),
    ).execute()

    # 辞書を整形して出力
    pprint.pprint(response)

    print("title: " + response["items"][0]["snippet"]["title"])
    print('publishTime:' + response["items"][0]["snippet"]["publishedAt"])

    # Pychatにかける
    total = 0
    videoid_ = videoid
    global livechat
    livechat = pytchat.create(video_id = videoid_, interruptable=False)
    while livechat.is_alive():
        # チャットデータの取得
        chatdata = livechat.get()
        for c in chatdata.items:
            if c.type != "textMessage":
                print(c.type)
            if c.type == "superChat" or c.type == "superSticker":
                value = c.amountValue
                # print("username: "+ c.author.name)
                # print("message: " + c.message)
                if  c.currency == "¥":
                    total += value
                    # print(str(value)+"円分のJPYを加算")
                else:
                    if c.currency == "MYR ":
                        rate = float(json_currency["MYR"])
                    elif c.currency == "DKK ":
                        rate = float(json_currency["DKK"])
                    elif c.currency == "SAR ":
                        rate = float(json_currency["SAR"])
                    elif c.currency == "CZK ":
                        rate = float(json_currency["CZK"])
                    elif c.currency == "₱":
                        rate = float(json_currency["PHP"])
                    else:
                        try:
                            rate = float(json_currency[c.currency])
                        except:
                            print(c.currency+"の換算に失敗")
                            continue
                    addition = round(value / rate,6)
                    total += addition
                    print(str(addition)+"円分の"+c.currency+"を加算 ※換算前は"+str(value)+c.currency)
                    print("total: " + str(total))
                # print("現在：" + str(total) + "円")
            else:
                pass
        
    total = int(total)
    print("スパチャ合計：" + str(total) + "円" + "\n")

    print("完了")