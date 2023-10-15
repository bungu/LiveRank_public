
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

from socket import gethostname

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Make()

def Make():
    main_userids = Main.objects.all().values_list("userid",flat=True)
    userid = input("useridを入力:")

    # 新規登録の時のみ実行
    if not userid in main_userids:
        superchat_total = input("累計スパチャを入力:")
        # YouTubeから登録者,概要,サムネURLを更新
            # herokuにはアップロードされているがGithubには非公開
        youtube = build("youtube","v3",developerKey="")
        data = youtube.channels().list(
                part = "statistics,snippet",
                id = userid
                    ).execute()
        name = data['items'][0]['snippet']["title"]
        if (data['items'][0]['statistics']['hiddenSubscriberCount'] == True):
            subscriber = 0
        else:
            subscriber = data['items'][0]['statistics']['subscriberCount']
        try:
            discription = data['items'][0]['snippet']['description']
        except:
            pass
        img = data['items'][0]['snippet']["thumbnails"]['medium']["url"]
        Main(
            userid = userid,
            img = img,
            name = name,
            discription = discription,
            subscriber_total = subscriber,
            superchat_total = superchat_total,
            superchat_past = superchat_total,
            LastUpdate_SuperchatPast = date.today(),
            tagcheck = False,
            # 期間系6個欠け9個
        ).save()
        print("ライバー "+ name + " が登録できました")

        # last1monthを今日から一ヶ月後まで作成
        for i in range(31):
            Main_Last1month(
                userid = userid,
                name = name,
                # 今日から31日後まで
                day = date.today() + timedelta(days = i),
                # ↑が本番環境で↓がupdateテスト用(テストのために昨日分からlast1monthを作る)
                # day = date.today() + timedelta(days = i-1),
                # lastupdate2つはデフォルト
                # superchat_dailyはデフォルト
                # subscriber_totalはデフォルト
                # 意図したデフォルト込みid抜き合計7個
            ).save()
        print(name + "のlast1monthを31個作成しました")
        
        # 次にtopsを作成    
        Main_Tops(
            name = name,
            userid = userid,
            order = 1,
            superchat_tops = 0,
            subscriber_tops = 0,
        ).save()
        print(name + "のtopsを1つ作成しました")
    else:
        print("登録済みのユーザーです")