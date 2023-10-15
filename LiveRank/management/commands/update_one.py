
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


class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Update()

errorcount = 0 # グローバル変数
updated = [] # ダブり回避用の、再帰後も引き継がれるグローバル配列 カウントしたライバーを入れていく

def Update():
    global errorcount,updated
    print("時刻："+ str(datetime.now()))
    hour = datetime.now().hour
    if hour <= 8:
        today = date.today() - timedelta(days = 1)
        print("0-9時であるため昨日をtodayとして進行")
    else:
        today = date.today()
        print("9-24時であるためtodayを通常通り設定して進行")

    print("today:"+str(today))

    update_list = []
    main_userids =  Main.objects.all().values_list("userid",flat=True)

    # 昨日までのlast1monthを作成, superchat_pastを更新
    main_livers = Main.objects.all()

    # 通貨の配列を作っておく
    url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
    text = url.text
    json_currency = json.loads(text)

    # ここで更新するライバーを決定
    userid_ = input("スパチャを更新するライバーのuseridを入力:")
    liver = Main.objects.get(userid = userid_)
    
    userid = liver.userid
    months = Main_Last1month.objects.filter(userid=userid)
    months_days = Main_Last1month.objects.filter(userid=userid).values_list("day",flat=True)

    # もし31日以上更新されてなかったら終了でごぜーます
    if (max(months_days) < today - timedelta(days = 31)) or (liver.name in updated) :
        if max(months_days) < today - timedelta(days = 31):
            print(liver.name + "が一ヶ月以上更新されていないようです 最終更新日:"+str(max(months_days)))
        elif liver.name in updated:
            print(liver.name + "は今回の実行で既に更新済み")

    # 31日以内に更新があった場合本処理
    elif max(months_days) >= today - timedelta(days = 31):
        # monthsの中で最大の日付が昨日より前だったら(≒未来にmonthsがなかったら)、昨日までの範囲で「ない日」のlast1monthを作る
        if max(months_days) < today - timedelta(days = 1) :
            for i in range(1,32):
                day = today - timedelta(days = i)
                # 被り作成防止
                if not(day in months_days):
                    Main_Last1month(
                        userid = userid,
                        name = liver.name,
                        day = day,
                        # superchat_daily :デフォルト
                        # subscriber_total :デフォルト
                        # lastupdate2つ :デフォルト
                        # 意図したデフォルト込みid抜き合計7個
                    ).save()
        
        # 欠けてる日の登録者数を更新(欠けてる日を埋める方法はないので、全部同じ値で埋める)
        not_defaults = Main_Last1month.objects.filter(userid = userid).filter(subscriber_lastupdate__gt = date(2020,1,1))

        # 辞書の配列を作成, 昨日の分だけ確定　
        # BUG:ここはsubscriber_totalに最新の値が入ってないとバグるが、上で更新してるから多分おおよそ問題ないンゴね~
        subscriber_records = [
            {
                "day": today - timedelta(days = 1),
                "subscriber": liver.subscriber_total
            },
        ]
        #updateがデフォじゃない日で日付が最小(最も前)の日(≒最終更新日)」を出す
        yet_videos = [] # エラー防止で先に定義しておく
        # 実行テストのためふみのたまきのみ実行 ここ含めて現在2個
        # if userid == "UCBiqkFJljoxAj10SoP2w2Cg":
        try:
            min_day = min(not_defaults.values_list("day",flat=True))
        except: # updatedなレコードが存在しないライバーの場合, last1monthの中で最小を検索
            min_day = min(Main_Last1month.objects.filter(userid = userid).values_list("day",flat=True))
        min_day_record = Main_Last1month.objects.filter(userid = userid).get(day= min_day)
        days = []
        # 最終更新日+1~一昨日までの日を登録者格納用の配列に格納
        i = 1
        while(min_day + timedelta(days = i) < today - timedelta(days = 1)):
            days.append(min_day + timedelta(days = i))
            i += 1
        # 上で作った辞書の配列に登録者と一緒にdaysを代入
        for day in days:
            a = {
                "day": day,
                "subscriber": min_day_record.subscriber_total
            }
            subscriber_records.append(a)

        # last1monthの登録者を更新
        for subsc in subscriber_records:
            month = Main_Last1month.objects.filter(userid = liver.userid).get(day = subsc["day"])
            Main_Last1month(
                    id = month.id,
                    userid = month.userid,
                    name = month.name,
                    day = month.day,
                    superchat_daily = month.superchat_daily,
                    subscriber_total = subsc["subscriber"],
                    subscriber_lastupdate = today,
                    superchat_lastupdate = month.superchat_lastupdate,
                    # id込み8項目
                ).save()

        # Pychatで欠けてる日のスパチャ額を取得
        superchat_yet_months = []
        yet_videos = []
        months = Main_Last1month.objects.filter(userid=userid) # 更新

        # スパチャが欠けてる日の最小値を取得(アップデートがデフォルト)
        for month in months:
            if month.superchat_lastupdate == date(2020,1,1) and month.day < today:
                superchat_yet_months.append(month.day)

        # youtubeapiを起動
        # herokuにはアップロードされているがGithubには非公開
        youtube = build("youtube","v3",developerKey="")

        # Youtubeapiに合う形にdate型を変換
        if len(superchat_yet_months) != 0:
            minday = min(superchat_yet_months)
        else:
            minday = today
        start = datetime.strftime(minday,'%Y-%m-%dT%H:%M:%S.%fZ')
        if minday == today:
            print(liver.name+"の昨日までのスパチャは既に更新されていると推測されます\n")
        else:
            print(liver.name+"のスパチャの更新は"+str(minday)+"から"+str(today - timedelta(days = 1))+"までが対象\n")
        
        response = youtube.search().list(
            type='video',
            part = 'snippet,id',
            channelId = liver.userid,
            regionCode = "JP",
            maxResults = 50,
            order = "date",
            publishedAfter = start,
            eventType = "completed"
        ).execute()
            
        print("以下対象動画")
        for i in range(50):
            try:
                # shortsを除外してみる：エラー消えたのでこれを保持
                if not("#shorts" in response['items'][i]['snippet']['title']):
                    publish_ = response["items"][i]["snippet"]["publishedAt"][:10]
                    publish = date.fromisoformat(publish_)
                    # superchat_yet_months(スパチャが更新されていないレコード)にある日付に出た動画なら保存
                    if publish in superchat_yet_months:
                        a = response['items'][i]['id']['videoId']
                        yet = {
                            "day" : publish,
                            "videoid" : response["items"][i]["id"]["videoId"],
                            "title":response['items'][i]['snippet']['title'],
                            "publishTime": response['items'][i]['snippet']['publishTime'].replace('T',' ').replace('Z','')[:10]
                        }
                        print("タイトル："+yet["title"])
                        print("投稿日時："+yet["publishTime"]+"\n")
                        yet_videos.append(yet)
            except:
                pass
        # Pychatにかける
        for n in range(len(yet_videos)):
            total = 0
            videoid_ = yet_videos[n]["videoid"]
            print('タイトル:' + yet_videos[n]["title"])
            print('videoid:' + videoid_)
            print('publishTime:' + yet_videos[n]["publishTime"])
            global livechat
            livechat = pytchat.create(video_id = videoid_, interruptable=False)
            while livechat.is_alive():
                # チャットデータの取得
                chatdata = livechat.get()
                for c in chatdata.items:
                    if c.type == "superChat":
                        value = c.amountValue
                        if  c.currency == "¥":
                            total += value
                            print(str(value)+"円分のJPYを加算")
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
                            addition = round(value / rate,6)
                            total += addition
                            print(str(addition)+"円分の"+c.currency+"を加算 ※換算前は"+str(value)+c.currency)
                        # print("現在：" + str(total) + "円")
                    else:
                        pass
            
            total = int(total)
            print("スパチャ合計：" + str(total) + "円" + "\n")
            yet_videos[n]["superchat"] = total
    

        # last1monthのスパチャを更新
        if len(yet_videos) > 0:
            for yet in yet_videos:
                month = Main_Last1month.objects.filter(userid = liver.userid).get(day = yet["day"])
                Main_Last1month(
                        id = month.id,
                        userid = month.userid,
                        name = month.name,
                        day = month.day,
                        superchat_daily = month.superchat_daily + yet["superchat"],
                        subscriber_total = month.subscriber_total,
                        subscriber_lastupdate = month.subscriber_lastupdate,
                        superchat_lastupdate = today,
                        # id込み8項目
                    ).save()
            print(liver.name+"のlast1monthのスパチャが更新されました")
        else:
            print("対象動画なし（last1monthスパチャ非更新）")

        # monthsの中で32日前以前があったら消してMainのsuperchat_pastを更新
        superchat_past = liver.superchat_past
        months = Main_Last1month.objects.filter(userid = liver.userid)
        for month in months:
            if month.day < today - timedelta(days = 31):
                Main(
                    id = liver.id,
                    userid = liver.userid,
                    img = liver.img,
                    name = liver.name,
                    # 期間スパチャ,登録者は直後に更新するためデフォ
                    superchat_past = liver.superchat_past + month.superchat_daily,
                    LastUpdate_SuperchatPast = today,
                    subscriber_total = liver.subscriber_total,
                    #仮
                    # superchat_total = liver.superchat_past,
                    discription = liver.discription,
                    tagcheck = liver.tagcheck,

                    superchat_monthly = liver.superchat_monthly,
                    superchat_weekly = liver.superchat_weekly,
                    superchat_daily = liver.superchat_daily,

                    subscriber_monthly = liver.subscriber_monthly,
                    subscriber_weekly = liver.subscriber_weekly,
                    subscriber_daily = liver.subscriber_daily,
                    # id込み15個 (トータル欠け)
                ).save()
                month.delete()
        
        # totalの加算してねぇ😇
        
        # 期間系の統計と記録
        countable = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
        superchat_monthly = 0
        superchat_weekly = 0
        for month in countable:
            superchat_monthly += month.superchat_daily
        
        if countable.count() >= 7:
            months_7 = countable[:7]
            for i in months_7:
                superchat_weekly += i.superchat_daily
            superchat_daily = countable[0].superchat_daily
        
        elif countable.count() >= 1:
            superchat_weekly = superchat_monthly
            superchat_daily = countable[0].superchat_daily
        
        elif countable.count() == 0:
            superchat_weekly == 0
            superchat_daily == 0

        Main(
            id = liver.id,
            userid = liver.userid,
            img = liver.img,
            name = liver.name,
            superchat_past = liver.superchat_past,
            LastUpdate_SuperchatPast = liver.LastUpdate_SuperchatPast,
            subscriber_total = liver.subscriber_total,
            superchat_total = liver.superchat_past + superchat_monthly,
            discription = liver.discription,
            tagcheck = liver.tagcheck,

            superchat_monthly = superchat_monthly,
            superchat_weekly = superchat_weekly,
            superchat_daily = superchat_daily,

            subscriber_monthly = liver.subscriber_monthly,
            subscriber_weekly = liver.subscriber_weekly,
            subscriber_daily = liver.subscriber_daily,

            # id込み16個 (0個欠け)
        ).save()
        print(liver.name+"の期間系スパチャが更新されました")

        # 期間系の記録

            
        # last1monthの個数検証
        months = Main_Last1month.objects.filter(userid=userid)
        if len(months) != 31:
            print(liver.name + "のlast1monthが"+str(len(months))+"個あります")

        # 更新部分のエラーをテストしたい
        


    # 日間,週間,月間金額を導出
    # (date-date).days でdate型の引き算で整数型にできるらしい dt1 + timedelta(days=1)で一日後にできる
    # 問題:例えばレコードが2つ以上あるけど一日飛んでたりする場合、デイリーのシステムが動かない：もし空白があった場合は前の日の値で埋める機能が必要
    # レコードが取れない日とかある？
    # for userid in userids:
    #     liver_dailys = Main_Last1month.objects.filter(userid=userid)
    #     daycount = liver_dailys.count()
    #     earlist_day = today - timedelta(days=(daycount-1))
    #     # 日間
    #     if(daycount >= 2):
    #         aday_ago = today - timedelta(days=1)
    #         superchat_daily = (liver_dailys.get(day=today).superchat_total) - (liver_dailys.get(day=aday_ago).superchat_total)
    #         subscriber_daily = (liver_dailys.get(day=today).subscriber_total) - (liver_dailys.get(day=aday_ago).subscriber_total)
    #     else:
    #         superchat_daily = 0
    #         subscriber_daily = 0
    #     # 週間
    #     if(daycount >= 8):
    #         oneweek_ago = day=today - timedelta(days=7)
    #         superchat_weekly = (liver_dailys.get(day=today).superchat_total) - (liver_dailys.get(day=oneweek_ago).superchat_total)
    #         subscriber_weekly = (liver_dailys.get(day=today).subscriber_total) - (liver_dailys.get(day=oneweek_ago).subscriber_total)
    #     else:
    #         superchat_weekly = (liver_dailys.get(day=today).superchat_total) - (liver_dailys.get(day=earlist_day).superchat_total)
    #         subscriber_weekly = (liver_dailys.get(day=today).subscriber_total) - (liver_dailys.get(day=earlist_day).subscriber_total)
    #     liver = Main.objects.get(userid=userid)
    #     # 月間
    #     superchat_monthly = (liver_dailys.get(day=today).superchat_total) - (liver_dailys.get(day=earlist_day).superchat_total)
    #     subscriber_monthly = (liver_dailys.get(day=today).subscriber_total) - (liver_dailys.get(day=earlist_day).subscriber_total)

    #     # 月間の計算　+ 日間と週間の更新
    #     Main(
    #         id = liver.id,
    #         userid = liver.userid,
    #         img = liver.img,
    #         name = liver.name,
    #         discription = liver.discription,

    #         superchat_total = liver.superchat_total,
    #         superchat_monthly = superchat_monthly,
    #         superchat_weekly = superchat_weekly,
    #         superchat_daily = superchat_daily,

    #         subscriber_total = liver.subscriber_total,
    #         subscriber_monthly = subscriber_monthly,
    #         subscriber_weekly = subscriber_weekly,
    #         subscriber_daily = subscriber_daily,
    #         ).save()

        print("完了")