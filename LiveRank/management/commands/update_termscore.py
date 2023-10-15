
from django.core.management.base import BaseCommand

from django.db.models import Max, Q
from LiveRank.models import Master,Tags,Main,Main_Last1month,Main_Tops

from datetime import date, timedelta, datetime
import math

from apiclient.discovery import build


class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Update_termscore()


def Update_termscore():
    today = date.today()
    livers = Main.objects.all()
    ended = 0
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
        # 更新しないライバーを除外
        if not(update_list[i]["userid"] in notupdate_list):
            # もし更新データの中に同一useridがいたら更新
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
    print("各ライバーの登録者数などを更新しました")

    for liver in livers:
        print("進捗："+str(ended)+"/"+str(livers.count()))
        # スパチャ更新

        countable = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
        superchat_monthly = 0
        superchat_weekly = 0
        for month in countable:
            superchat_monthly += month.superchat_daily
        
        if countable.count() >= 7:
            months_7 = countable[:7]
            for i in months_7:
                superchat_weekly += i.superchat_daily
            if (countable[0].subscriber_lastupdate != date(2020,1,1)): # スパチャは更新されなければ2020,1,1のままなのでsubscで判定
                superchat_daily = countable[0].superchat_daily
            else:
                superchat_daily = countable[1].superchat_daily
        
        elif countable.count() >= 1:
            superchat_weekly = superchat_monthly
            if countable[0].subscriber_lastupdate != date(2020,1,1): # スパチャは更新されなければ2020,1,1のままなのでsubscで判定
                superchat_daily = countable[0].superchat_daily
            else:
                superchat_daily = countable[1].superchat_daily
        
        elif countable.count() == 0:
            superchat_weekly = 0
            superchat_daily = 0

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
        print(liver.name+"の期間系登録者数が更新されました")
        print(liver.name+"の期間系スパチャが更新されました")

        ended += 1
    print("ライバーの期間系記録が更新されました")

def test():
    today = date.today()
    liver = Main.objects.get(userid = "UC0yQ2h4gQXmVUFWZSqlMVOA")
    countable = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
    print(countable[0].subscriber_lastupdate)