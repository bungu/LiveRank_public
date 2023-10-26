
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
        # ここに書いたものが実行される
        Update()

errorcount = 0 # グローバル変数
updated = [] # ダブり回避用の、再帰後も引き継がれるグローバル配列 カウントしたライバーを入れていく

def Update():
    hostname = gethostname()
    global errorcount,updated
    try:
        print("時刻："+ str(datetime.now()))
        hour = datetime.now().hour
        if (hour <= 8) and ("MacBook-Pro" in hostname):
            today = date.today() - timedelta(days = 1)
            print("0-9時かつMacでの更新であるため昨日をtodayとして進行")
        else:
            today = date.today()
            print("9-24時であるかherokuでの更新であるためtodayを通常通り設定して進行")

        print("today:"+str(today))

        update_list = []
        notupdate_list = []
        main_userids =  Main.objects.all().values_list("userid",flat=True)

        for userid_ in main_userids:
            userid = userid_
            prof = {
                'userid' : userid,
            }
            update_list.append(prof)

        # チャンネル名と登録者情報と画像urlをYouTubeからAPIを用いて取得
        # herokuにはアップロードされているがGithubには非公開
        youtube = build("youtube","v3",developerKey="")

        # Youtubeからuseridを参照してupdate_listにそれぞれ登録者情報を代入
        for i,update in enumerate(update_list): #enumerateを使うとインデックス番号も回すことができる
            # 取得
            response = youtube.channels().list(
                part = "statistics,snippet",
                id = update_list[i]["userid"]
            ).execute()
            try: 
                name = response['items'][0]['snippet']["title"]
                if (response['items'][0]['statistics']['hiddenSubscriberCount'] == True):
                    subscriber = 0
                else:
                    subscriber = response['items'][0]['statistics']['subscriberCount']
                try:
                    discription = response['items'][0]['snippet']['description']
                    img = response['items'][0]['snippet']["thumbnails"]['medium']["url"]
                except:
                    discription = ""
                    img = ""
                    print(update_list[i]["userid"]+"の画像又は概要欄の取得に失敗")
                # updatelistに入れ込む
                update_list[i]["name"] = name
                update_list[i]["subscriber_total"] = subscriber
                update_list[i]["discription"] = discription
                update_list[i]["img"] = img
            except:
                import traceback
                traceback.print_exc()
                print("userid:"+update_list[i]["userid"]+"のライバーはなんらかのエラーで非更新対象")
                notupdate_list.append(update_list[i]["userid"])

        # Mainにいれば上書き

        # mainモデルのuseridを配列で出す
        main_userids = Main.objects.all().values_list("userid",flat=True)

        for i in range(len(update_list)):
            # 更新できないライバーを除外
            if not(update_list[i]["userid"] in notupdate_list):
                # もし更新データの中に同一useridがいたら更新,いなかったら新規作成
                if(update_list[i]["userid"] in main_userids):
                    # Mainモデルの中から同一useridのレコードを抽出
                    liver = Main.objects.get(userid = update_list[i]["userid"])
                    # model固有idはそのまま、それ以外のデータをupdate_listから更新
                    if (liver.tags.all()):
                        # タグチェック分岐
                        Main(
                            id = liver.id,
                            userid = update_list[i]["userid"],
                            img = update_list[i]["img"],
                            name = update_list[i]["name"],
                            discription = update_list[i]["discription"],
                            subscriber_total = update_list[i]["subscriber_total"],
                            superchat_past = liver.superchat_past,
                            LastUpdate_SuperchatPast = liver.LastUpdate_SuperchatPast,
                            superchat_total = liver.superchat_total,
                            tagcheck = True,

                            superchat_monthly = liver.superchat_monthly,
                            superchat_weekly = liver.superchat_weekly,
                            superchat_daily = liver.superchat_daily,

                            subscriber_monthly = liver.subscriber_monthly,
                            subscriber_weekly = liver.subscriber_weekly,
                            subscriber_daily = liver.subscriber_daily,
                            # id込み16個 (0個欠け)
                            # 取得し他情報以外全てデフォルト
                        ).save()
                    else:
                        Main(
                            id = liver.id,
                            userid = update_list[i]["userid"],
                            img = update_list[i]["img"],
                            name = update_list[i]["name"],
                            discription = update_list[i]["discription"],
                            subscriber_total = update_list[i]["subscriber_total"],
                            superchat_past = liver.superchat_past,
                            LastUpdate_SuperchatPast = liver.LastUpdate_SuperchatPast,
                            superchat_total = liver.superchat_total,
                            tagcheck = False,

                            superchat_monthly = liver.superchat_monthly,
                            superchat_weekly = liver.superchat_weekly,
                            superchat_daily = liver.superchat_daily,

                            subscriber_monthly = liver.subscriber_monthly,
                            subscriber_weekly = liver.subscriber_weekly,
                            subscriber_daily = liver.subscriber_daily,
                            # id込み16個 (0個欠け)
                        ).save()

                # 同じuseridがなかった場合通知
                else:
                    print(update_list[i]["userid"]+"のメインモデルがありません")

        # 重そうなので一旦空にする
        update_list = []
        # 昨日までのlast1monthを作成, superchat_pastを更新
        main_livers = Main.objects.all()

        # 通貨の配列を作っておく
        url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
        text = url.text
        json_currency = json.loads(text)

        ended = 0
        for liver_for in main_livers:
            liver = liver_for
            print("進捗："+str(ended)+"/"+str(main_livers.count()))
            userid = liver.userid
            months = Main_Last1month.objects.filter(userid=userid)
            months_days = Main_Last1month.objects.filter(userid=userid).values_list("day",flat=True)

            if (max(months_days) < today - timedelta(days = 31)) or (liver.name in updated) :
                if max(months_days) < today - timedelta(days = 31):
                    print(liver.name + "が一ヶ月以上更新されていないようです 最終更新日:"+str(max(months_days)))
                elif liver.name in updated:
                    print(liver.name + "は今回の実行で既に更新済み")
            
            # 31日以内に更新があった場合本処理
            elif max(months_days) >= today - timedelta(days = 31):
                # monthsの中で最大の日付が今日より前だったら(≒未来にmonthsがなかったら)、昨日までの範囲で「ない日」のlast1monthを作る
                if max(months_days) <= today - timedelta(days = 1) :
                    for i in range(1,32):
                        day = today - timedelta(days = i)
                        if not(day in months_days): # 被り作成防止
                            Main_Last1month(
                                userid = userid,
                                name = liver.name,
                                day = day,
                                # superchat_daily :デフォルト
                                # subscriber_total :デフォルト
                                # lastupdate2つ :デフォルト
                                # 意図したデフォルト込みid抜き合計7個
                            ).save()
                            print(liver.name + "の" + str(day) + "のlast1monthを新規作成")
                
                # 欠けてる日の登録者数を更新(欠けてる日を埋める方法はないので、全部同じ値で埋める)

                # 辞書の配列を作成, 昨日の分だけ確定　
                # BUG:ここはsubscriber_totalに最新の値が入ってないとバグるが、上で更新してるから多分おおよそ問題ないンゴね~
                # ↓ここで現在の登録者数を記録
                subscriber_records = [
                    {
                        "day": today - timedelta(days = 1),
                        "subscriber": liver.subscriber_total
                    }
                ]
                yet_videos = [] # エラー防止で先に定義しておく

                #updateがデフォじゃない日で日付が最大(≒最も現在に近い)の日(≒最終更新日)」を出す
                not_defaults = Main_Last1month.objects.filter(userid = userid).filter(subscriber_lastupdate__gt = date(2020,1,1))

                #ここから登録者の更新
                try:
                    max_day = max(not_defaults.values_list("day",flat=True))
                except: # updatedなレコードが存在しないライバーの場合, last1monthの中で最大を検索 恐らく今日になるので、下の処理が対象なしになる
                    max_day = max(Main_Last1month.objects.filter(userid = userid).values_list("day",flat=True))
                print("max_day:"+str(max_day))
                max_day_record = Main_Last1month.objects.filter(userid = userid).get(day= max_day)
                days = []
                # 最終更新日+1~昨日までの日を登録者格納用の配列に格納
                i = 1
                while(max_day + timedelta(days = i) < today - timedelta(days = 1)):
                    days.append(max_day + timedelta(days = i))
                    i += 1
                # 上で作った配列に登録者と一緒にdaysを代入
                for day in days:
                    a = {
                        "day": day,
                        "subscriber": max_day_record.subscriber_total
                    }
                    subscriber_records.append(a)
            
                # last1monthの登録者を更新
                print(liver.userid)
                for subsc in subscriber_records:
                    print(subsc)
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
                    print(str(month.day))
                        

                # Pychatで欠けてる日のスパチャ額を取得
                superchat_yet_months = []
                yet_videos = []
                months = Main_Last1month.objects.filter(userid=userid) # 更新

                # スパチャが欠けてる日の最小値を取得(アップデートがデフォルト)
                for month in months:
                    if month.superchat_lastupdate == date(2020,1,1) and month.day < today:
                        superchat_yet_months.append(month.day)

                # youtubeapiを起動
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
                    print(liver.name+"のスパチャの更新は"+str(minday)+"から昨日までが対象\n")
                
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
                            # これ時差直したい
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
                            if c.type == "superChat" or c.type == "superSticker":
                                value = c.amountValue
                                # 日本円
                                if  c.currency == "¥":
                                    total += value
                                    print(str(value)+"円分のJPYを加算")
                                # それ以外
                                else:
                                    try:
                                        if len(c.currency) == 4:
                                            rate = float(json_currency[c.currency[:3]])
                                        elif c.currency == "₱":
                                            rate = float(json_currency["PHP"])
                                        elif c.currency == "₪":
                                            rate = float(json_currency["ILS"])
                                        elif c.currency == "₫":
                                            rate = float(json_currency["VND"])
                                        else:
                                            rate = float(json_currency[c.currency])
                                        addition = round(value / rate,6)
                                        total += addition
                                        print(str(addition)+"円分の"+c.currency+"を加算 ※換算前は"+str(value)+c.currency)
                                    except:
                                        print(c.currency+"の換算に失敗")
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
                        print("統合前のsuperchatpastは"+str(liver.superchat_past))
                        print(str(month.day) + "のスパチャ記録は" + str(month.superchat_daily))
                        userid_hikitugi = liver.userid
                        Main(
                            id = liver.id,
                            userid = liver.userid,
                            img = liver.img,
                            name = liver.name,
                            
                            superchat_past = liver.superchat_past + month.superchat_daily,
                            LastUpdate_SuperchatPast = today,
                            subscriber_total = liver.subscriber_total,
                            #仮
                            superchat_total = liver.superchat_total,
                            discription = liver.discription,
                            tagcheck = liver.tagcheck,

                            superchat_monthly = liver.superchat_monthly,
                            superchat_weekly = liver.superchat_weekly,
                            superchat_daily = liver.superchat_daily,

                            subscriber_monthly = liver.subscriber_monthly,
                            subscriber_weekly = liver.subscriber_weekly,
                            subscriber_daily = liver.subscriber_daily,
                            # id込み16個
                        ).save()
                        print(liver.name +"の" + str(month.day) + "のレコードがsuperchat_pastに統合されました")
                        # なんか一応更新しとく
                        liver = Main.objects.get(userid = userid_hikitugi)
                        print("統合後のsuperchat_pastは"+str(liver.superchat_past))
                        month.delete()
                
                # 期間系の統計と記録
                # スパチャは今日以前のlast1monthの個数に応じて処理を変更
                countable = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
                superchat_monthly = 0
                superchat_weekly = 0
                for month in countable:
                    superchat_monthly += month.superchat_daily
                
                if countable.count() >= 7:
                    months_7 = countable[:7]
                    for i in months_7:
                        superchat_weekly += i.superchat_daily
                    if countable[0].subscriber_lastupdate != date(2020,1,1): # スパチャは更新されなければ2020,1,1のままなのでsubscで判定
                        superchat_daily = countable[0].superchat_daily
                    else:
                        superchat_daily = countable[1].superchat_daily
                
                elif countable.count() >= 1:
                    superchat_weekly = superchat_monthly
                    if countable[0].subscriber_lastupdate != date(2020,1,1): # スパチャは更新されなければ2020,1,1のままなのでsubscで判定
                        superchat_daily = countable[0].superchat_daily
                    else:
                        superchat_daily = 0
                
                elif countable.count() == 0:
                    superchat_weekly == 0
                    superchat_daily == 0
                

                countable_subscriber = Main_Last1month.objects.filter(userid=liver.userid).filter(subscriber_total__gt=0).order_by("day").reverse()

                # 0が今日になる感じで日付順で並べているため、最後の要素を取ると「登録者記録が0ではない最も前の記録」を出すことができる
                # BUG:[可能性]これは存在する全てのlast1monthに値が入っていることを前提にやられているが、そうじゃない場合オワ
                # エラー報告モデル作るか
                if countable_subscriber.count() != 0:
                    oldest_day = countable_subscriber.last().day
                    newest_day = countable_subscriber[0].day
                    oldest_subscriber = countable_subscriber.last().subscriber_total
                    newest_subscriber = countable_subscriber[0].subscriber_total

                    subscriber_monthly =  newest_subscriber - oldest_subscriber

                    if (newest_day - oldest_day).days > 7:
                        subscriber_weekly = newest_subscriber - countable_subscriber[6].subscriber_total
                    else:
                        subscriber_weekly = subscriber_monthly
                    try:
                        subscriber_daily = newest_subscriber - countable_subscriber[1].subscriber_total
                    except:
                        subscriber_daily = 0

                elif countable_subscriber.count() == 0:
                    subscriber_monthly = 0
                    subscriber_weekly = 0
                    subscriber_daily = 0
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

                    subscriber_monthly = subscriber_monthly,
                    subscriber_weekly = subscriber_weekly,
                    subscriber_daily = subscriber_daily,

                    # id込み16個 (0個欠け)
                ).save()
                print(liver.name+"の期間系スパチャが更新されました")
                print(liver.name+"の期間系登録者数が更新されました")

                    
                # last1monthの個数検証
                months = Main_Last1month.objects.filter(userid=userid)
                if len(months) != 31:
                    print(liver.name + "のlast1monthが"+str(len(months))+"個あります")
            
            ended += 1
            updated.append(liver.name)

            print("エラーカウント:"+str(errorcount)) # errorcountはグローバル変数

            print("") # 改行

        # ここから登録者とスパチャ額について、一月分の記録とtop10の更新

        # main_livers = Main.objects.all().values("name","userid","superchat_total","subscriber_total")

        # 最後にマスターを更新
        master = Master.objects.all()[0]

        Master(
            id=1,
            last_update = today - timedelta(days = 1),
            pv_count = master.pv_count
        ).save()

        print("完了")

    except:
        # エラーがあった場合再帰 ループし続けたらやばいので回数を定義
        
        errorcount += 1 # errorcountはグローバル変数
        print("エラーカウント加算:"+str(errorcount))
        import traceback
        traceback.print_exc()
        if errorcount <= 50:
            Update()
