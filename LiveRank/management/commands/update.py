from django.core.management.base import BaseCommand

from LiveRank.models import Master,Main,Main_Last1month,Main_Sponsor,Error

from time import sleep
from datetime import date, timedelta, datetime
from apiclient.discovery import build

import pytchat
import requests, json

from socket import gethostname

import smtplib, ssl
from email.mime.text import MIMEText

from dotenv import load_dotenv
import os

# 環境変数を読み込む
load_dotenv(".env")

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        Update(updated = [])

# 想定していないエラーの数
error_count = 0

def Update(updated:list):
    '''
    主となる関数 ここから下の関数を呼び出して動かす
    '''
    global error_count
    # どこでエラーが起きても動くように全体をtryで囲む
    try:
        # 時刻を取得、日本時間に合わせてtodayを設定
        # tdoayを使うところがまとまってるならそこで見るべきぽいな~~
        print("時刻："+ str(datetime.now()))
        now_hour = datetime.now().hour
        if (now_hour <= 8) and ("MacBook" in gethostname()):
            today = date.today() - timedelta(days = 1)
            print("0-9時かつMacでの更新であるため昨日をtodayとして進行")
        else:
            today = date.today()
            print("9-24時であるかherokuでの更新であるためtodayを通常通り設定して進行")
        print("today:"+str(today))
        
        # YoutubeAPIを呼び出す用のオブジェクトを取得
        youtube = build("youtube","v3",developerKey = os.environ["YOUTUBE_API_KEY"])

        # 全てのライバーのMainモデルを取得
        livers =  Main.objects.all()

        # 登録ライバーの登録者数、名前、概要欄、アイコン画像をYoutubeAPIを用いて更新
        count = 0
        for liver in livers:
            if liver.userid in updated:
                continue
            update_liver_with_api(youtube, liver)
            count += 1
            print(f"進捗：{str(count)}/{str(livers.count())} {liver.name} のAPI系統の更新が完了")
        print("YoutubeAPI関連のメインモデル更新が完了")
        print()

        # スポンサーモデルの更新
        update_sponsors(youtube)
        print("YoutubeAPI関連のスポンサーモデル更新が完了")
        print()

        # 更新したのでMainモデルを再取得
        livers =  Main.objects.all()

        # 各ライバーについてスーパーチャットとlast1monthの更新
        errored_ids = [] # エラーが発生したライバーのidを格納するリスト
        progress = 0
        for liver in livers:
            progress += 1
            print("進捗："+str(progress)+"/"+str(livers.count())+" "+liver.name)
            if liver.userid in updated:
                print(liver.name + "は今回の実行で既に更新済み")
                continue
            # 欠けているlast1monthを作成
            create_lacking_last1month(today, liver)

            # last1monthの登録者数を更新
            update_last1month_subscriber(today, liver)

            # スーパーチャットの更新 エラーが起きやすい
            response = update_last1month_superchat(today, liver, youtube)
            # エラーが発生していたらidをエラーリストに追加 
            if response["errored"] == True:
                errored_ids.append(liver.userid)
                print(liver.name + "のスパチャの更新でエラーが発生しています")
            # 期間系のパラメーターを更新
            update_termscore(today, liver)
            print(liver.name+"の期間系スパチャが更新されました")
            print(liver.name+"の期間系登録者数が更新されました")
            print()

            updated.append(liver.userid)

        # マスター更新
        master = Master.objects.all().order_by("id").reverse()[0]
        master.last_update = today - timedelta(days = 1)
        master.save()

        # エラーを起こしたライバーのidが1つ以上あったらエラーとして保存
        if len(errored_ids) >= 1:
            # エラー起こしたuseridを保存
            Error(
                time=datetime.now(),
                text = "userids_with_error:"+",".join(errored_ids)
            ).save()
        if not(errored_ids): 
            errored_ids = []
        send_email(
            errored_userids = errored_ids,
            errorcount = error_count
        )

        print()
        print("完了")
    
    # 想定外のエラーが起きた場合の処理
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("全体の更新のどこかで想定外のエラーが発生しました")
        # global関数を使ってカウント
        error_count += 1
        # 想定外のエラーをエラーモデルに保存
        Error(
            error = str(e),
            date = today,
            hostname = gethostname()
        ).save()
        # 30回まで再帰する 既にアップデートが完了しているライバーの配列を渡し、更新しないようにする
        if error_count <= 30:
            Update(updated = updated)
        else:
            print("エラーが30回以上発生したため、処理を中止します")
            send_email(
                errored_userids = errored_ids,
                errorcount = error_count
            )

def update_liver_with_api(
        youtube: object,
        liver: object
    ):
    '''
    youtubeapiを用いてライバーの登録者数、名前、概要欄、アイコン画像を更新する関数
    '''
    # チャンネル名と登録者情報と画像urlをYouTubeからAPIを用いて取得
    # apiから諸情報のjsonを取得
    response = youtube.channels().list(
        part = "statistics,snippet",
        id = liver.userid
    ).execute()
    # 取得したjsonから必要な情報を抽出 
    # アカウント削除等で取得できない時のために例外処理
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
            print(liver["userid"]+"の画像又は概要欄の取得に失敗")
        # 更新する
        liver.name = name
        liver.subscriber_total = subscriber
        liver.img = img
        liver.discription = discription
        if (liver.tags.all()):
            # タグチェック分岐
            liver.tagcheck = True
        else:
            liver.tagcheck = False
        liver.save()
    except:
        import traceback
        traceback.print_exc()
        print("userid:"+liver.userid+"のライバーは上記のエラーで非更新対象")

def update_sponsors(youtube: object):
    # スポンサーモデルを更新
    # 上と異なる処理であるため別に実行
    sponsors = Main_Sponsor.objects.all()

    for sponsor in sponsors:
        response = youtube.channels().list(
            part = "statistics,snippet",
            id = sponsor.userid
        ).execute()
        try: 
            sponsor.name = response['items'][0]['snippet']["title"]
            if (response['items'][0]['statistics']['hiddenSubscriberCount'] == True):
                sponsor.subscriber_total = 0
            else:
                sponsor.subscriber_total = response['items'][0]['statistics']['subscriberCount']
            try:
                sponsor.img = response['items'][0]['snippet']["thumbnails"]['medium']["url"]
            except:
                sponsor.img = ""
                print(sponsor.userid+"の画像又は概要欄の取得に失敗")
        except:
            import traceback
            traceback.print_exc()
            print("userid:"+sponsor.userid+"のライバー(スポンサー)は上記のエラーで非更新")

def create_lacking_last1month(
        today: date,
        liver: object
    ):
    """
    ライバーの昨日までのlast1monthレコードを欠けてる分作成する関数
    last1monthレコードには過去1ヶ月分のライバーの登録者数、スーパーチャットが記録される
    """
    # ユーザーIDを取得
    userid = liver.userid

    # last1monthのレコードを取得、日付の配列を作成
    months = Main_Last1month.objects.filter(userid=userid)
    months_days = months.values_list("day",flat=True)
    
    # 存在するmonthsの中で最大の日付が昨日より前だったら(≒少なくとも今日までに1つ以上欠けているlast1monthがあったら)
    # 昨日までの範囲で「ない日」のlast1monthを作る
    if max(months_days) < today - timedelta(days = 1):
        # 今日から1日ずつ遡り、last1monthが存在しなければ作成する
        for i in range(1,32):
            months_days = Main_Last1month.objects.filter(userid=userid).values_list("day",flat=True)
            day = today - timedelta(days = i)
            if not(day in months_days):
                Main_Last1month(
                    userid = userid,
                    name = liver.name,
                    day = day,
                ).save()
                print(liver.name + "の" + str(day) + "のlast1monthを新規作成")

def update_last1month_subscriber(
        today: date,
        liver: object
    ):
    ''' 
    last1monthの登録者数を更新する関数
    '''
    # ユーザーIDを取得
    userid = liver.userid

    #updateがデフォじゃない日で日付が最大の(≒最も今日に近い)日(≒最終更新日)」を出す
    not_defaults = Main_Last1month.objects.filter(userid = userid).filter(subscriber_lastupdate__gt = date(2020,1,1))

    try:
        latest_update_day = max(not_defaults.values_list("day",flat=True))
    except: # updateされたレコードが存在しないライバーの場合, last1monthの中で最大を検索(恐らく今日になる)
        latest_update_day = max(Main_Last1month.objects.filter(userid = userid).values_list("day",flat=True))
    
    print("latest_update_day:"+str(latest_update_day))

    # 過去のバグ検証用コード 一応残しておく
    # if max_day_record_multi.count() != 1:
    #     double_months_main.append(liver.name)

    latest_update_day_record = Main_Last1month.objects.filter(userid = userid).filter(day= latest_update_day)[0]

    # 最終更新日+1~昨日までの日について登録者を更新
    i = 1
    while(latest_update_day + timedelta(days = i) <= today - timedelta(days = 1)):
        day_for_update = latest_update_day + timedelta(days = i)
        month = Main_Last1month.objects.filter(userid = liver.userid).filter(day = day_for_update)[0]
        month.subscriber_total = latest_update_day_record.subscriber_total
        month.subscriber_lastupdate = today
        month.save()
        i += 1

def update_last1month_superchat(
        today: date,
        liver:object,
        youtube: object
    ):
    '''
    スーパーチャットの情報を更新する関数
    '''
    # ライバーを全て取得
    main_livers = Main.objects.all()

    # 日本円に変換するために通貨の配列を作っておく
    url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
    text = url.text
    json_currency = json.loads(text)

    userid = liver.userid

    # エラーが起きたかどうかを記録する変数
    errored = False

    # 日本円に変換するために通貨の配列を作っておく
    url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
    text = url.text
    json_currency = json.loads(text)

    # ユーザーIDを取得
    userid = liver.userid

    # 更新されてない日の動画を取得

    # 全てのmonthsを取得
    months = Main_Last1month.objects.filter(userid=userid) # 更新

    # スパチャが欠けてる日(lastupdateがデフォルトである日)の最小値を取得

    # 欠けてる日のレコードを格納する配列
    superchat_yet_months = []

    for month in months:
        if month.superchat_lastupdate == date(2020,1,1) and month.day < today:
            superchat_yet_months.append(month.day)
    if len(superchat_yet_months) != 0:
        minday = min(superchat_yet_months)
    else:
        minday = today

    # Youtubeapiに合う形にdate型を変換
    start = datetime.strftime(minday,'%Y-%m-%dT%H:%M:%S.%fZ')
    if minday == today:
        print(liver.name+"の昨日までのスパチャは既に更新されていると推測されます\n")
    else:
        print(liver.name+"のスパチャの更新は"+str(minday)+"から昨日までが対象\n")

    
    # 取得した日付から今日までの動画を取得
    response = youtube.search().list(
        type='video',
        part = 'snippet,id',
        channelId = liver.userid,
        regionCode = "JP",
        maxResults = 50,
        order = "date",
        publishedAfter = start,
        eventType = "completed" # ライブ配信かつ完了しているものだけが取得されるようになる
    ).execute()
    
    # まだ処理していないvideoを格納する配列
    yet_videos = []

    print("以下対象動画")
    for i in range(len(response["items"])):
        # エラーが起きない動画のみ扱う # TODO: ここでのエラーの記録(エラーモデルをもっと充実させる)
        try:
            # 日付を確認
            publish = response["items"][i]["snippet"]["publishedAt"][:10]
            publish = date.fromisoformat(publish)
            # superchat_yet_months(スパチャが更新されていないレコード)にある日付に出た動画なら保存
            if publish in superchat_yet_months:
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
            errored = True
            import traceback
            traceback.print_exc()
            
    # Pychatにかけてスパチャを取得
    for n in range(len(yet_videos)):
        yet_videos[n]["superchat"] = -1 # 初期値を-1にしておく
        try:
            videoid_ = yet_videos[n]["videoid"]
            print('タイトル:' + yet_videos[n]["title"])
            print('videoid:' + videoid_)
            print('publishTime:' + yet_videos[n]["publishTime"])
            # global livechat
            livechat = pytchat.create(video_id = videoid_, interruptable=False)
            total = 0 # スパチャの合計を格納する変数
            while livechat.is_alive():
                sleep(0.1)
                # チャットデータの取得
                chatdata = livechat.get()
                for c in chatdata.items:
                    # スパチャの場合処理
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
            
            total = int(total)
            # yet_videosにスパチャの合計を格納
            # 中断された場合に辻褄が合わなくなることを回避するために一斉に保存したい
            # そのためこの時点ではDBを更新しない
            yet_videos[n]["superchat"] = total
            print("スパチャ合計：" + str(total) + "円" + "\n")
        except Exception as e:
            import traceback
            traceback.print_exc()
            # keyboardInterrupt以外が発生した場合はerroedをTrueにする
            if not isinstance(e, KeyboardInterrupt):
                errored = True

    # last1monthのスパチャを更新
    if len(yet_videos) > 0:
        for yet in yet_videos:
            if yet["superchat"] != -1: # スパチャが取得できている場合、スパチャ額を加算する
                month = Main_Last1month.objects.filter(userid = liver.userid).filter(day = yet["day"])[0]
                month.superchat_daily = month.superchat_daily + yet["superchat"]
                month.superchat_lastupdate = today
                month.save()
                month = Main_Last1month.objects.filter(userid = liver.userid).filter(day = yet["day"])[0]
                # 後からアーカイブが公開される可能性等を考慮し、記録なしかつ今日から5日以内の場合superchat_lastupdateをデフォに戻しておく
                if month.superchat_daily == 0 and timedelta(days = 1) <= today - month.day < timedelta(days = 5):
                    month.superchat_lastupdate = date(2020,1,1)
                    month.save()
        print(liver.name+"のlast1monthのスパチャが更新されました")
    else:
        print()
        print("対象動画なし（last1monthスパチャ非更新）")
    # エラーが起きているかどうかを返す
    return { "errored": errored }

def update_termscore(
        today: date,
        liver: object
    ):
    '''
    不要なlast1monthを削りつつ、mainモデルの期間系パラメーター(日間、週間、累計など)を更新する関数
    '''
    # monthsの中で32日前以前があったら消してMainのsuperchat_pastを更新
    months = Main_Last1month.objects.filter(userid = liver.userid)
    for month in months:
        if month.day < today - timedelta(days = 31):
            print("統合前のsuperchatpastは"+str(liver.superchat_past))
            print(str(month.day) + "のスパチャ記録は" + str(month.superchat_daily))
            liver.superchat_past = liver.superchat_past + month.superchat_daily
            liver.LastUpdate_SuperchatPast = today
            liver.save()
            print(liver.name +"の" + str(month.day) + "のレコードがsuperchat_pastに統合されました")
            # 一応更新しとく
            userid_hikitugi = liver.userid
            liver = Main.objects.get(userid = userid_hikitugi)
            print("統合後のsuperchat_pastは"+str(liver.superchat_past))
            month.delete()
    
    # 期間系の記録の更新

    # 期間系スパチャの更新
    # スパチャは今日以前のlast1monthの個数に応じて処理を変更
    # 今日より前の(≒未来でない)last1monthのレコードを取得
    countable = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
    superchat_monthly = 0
    superchat_weekly = 0

    # 月次記録は全てのlast1monthのスパチャを合計する
    for month in countable:
        superchat_monthly += month.superchat_daily
    
    # カウントできるlast1monthが7個以上ある時の処理
    if countable.count() >= 7:
        months_7 = countable[:7]
        # weekly記録は最新の7個のlast1monthのスパチャを合計する
        for i in months_7:
            superchat_weekly += i.superchat_daily
        # daily記録は最新のlast1monthのスパチャを取得
        try:
            int(countable[0].superchat_daily)
            superchat_daily = countable[0].superchat_daily
        except:
            superchat_daily = 0
    
    # カウントできるlast1monthが1~6個の時の処理
    elif countable.count() >= 1:
        # weekly記録は月次記録と同じになる
        superchat_weekly = superchat_monthly
        if countable[0].subscriber_lastupdate != date(2020,1,1): # スパチャは更新されなければ2020,1,1のままなのでsubscで判定
            superchat_daily = countable[0].superchat_daily
        else:
            superchat_daily = 0
    
    elif countable.count() == 0:
        superchat_weekly = 0
        superchat_daily = 0

    # 期間系登録者数の更新
    countable_subscriber = Main_Last1month.objects.filter(userid=liver.userid).filter(subscriber_total__gt=0).order_by("day").reverse()

    # countableの数が0でない場合、通常更新
    if countable_subscriber.count() != 0:

        # 月次登録者数記録の導出
        # 現在→過去日付順で並べているため、最後の要素を取ると「登録者記録が0ではない最も前の記録」を出すことができる
        oldest_day = countable_subscriber.last().day
        newest_day = countable_subscriber[0].day
        oldest_subscriber = countable_subscriber.last().subscriber_total
        newest_subscriber = countable_subscriber[0].subscriber_total

        subscriber_monthly =  newest_subscriber - oldest_subscriber

        # 週間登録者数記録の導出
        if (newest_day - oldest_day).days > 7:
            subscriber_weekly = newest_subscriber - countable_subscriber[6].subscriber_total
        else:
            subscriber_weekly = subscriber_monthly

        # 日間登録者数記録の導出
        try:
            subscriber_daily = newest_subscriber - countable_subscriber[1].subscriber_total
        except:
            subscriber_daily = 0

    # countableの数が0の場合、期間系登録者数は全て0
    elif countable_subscriber.count() == 0:
        subscriber_monthly = 0
        subscriber_weekly = 0
        subscriber_daily = 0
    
    # 更新
    liver.superchat_total = liver.superchat_past + superchat_monthly

    liver.superchat_monthly = superchat_monthly
    liver.superchat_weekly = superchat_weekly
    liver.superchat_daily = superchat_daily

    liver.subscriber_monthly = subscriber_monthly
    liver.subscriber_weekly = subscriber_weekly
    liver.subscriber_daily = subscriber_daily

    liver.save()

# 送信先のアドレス、パスキーを環境変数から取得
send_address = os.environ["ADMIN_MAIL_ADDRESS"]
pass_key = os.environ["ADMIN_MAIL_PASSKEY"]

# メインの関数
def send_email(
        errored_userids: list,
        errorcount: int
    ):
    if len(errored_userids) != 0 or errorcount != 0:
        msg = make_mime_text(
            mail_to = send_address,
            subject = "エラー発生",
            body = f"今日の更新においてエラーが発生しました スパチャエラー:{str(len(errored_userids))}回 想定外のエラー:{str(error_count)}回 <br> https://www.liverank.jp/admin/"
        )
    else:
        msg = make_mime_text(
            mail_to = send_address,
            subject = "エラーなし",
            body = "今日の更新は正常に完了しました"
        )
    send_gmail(msg)

# 件名、送信先アドレス、本文を渡す関数
def make_mime_text(mail_to, subject, body):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["To"] = mail_to
    msg["From"] = send_address
    return msg

# smtp経由でメール送信する関数
def send_gmail(msg):
    server = smtplib.SMTP_SSL(
        "smtp.gmail.com", 465,
        context = ssl.create_default_context())
    server.set_debuglevel(0)
    server.login(send_address, pass_key)
    server.send_message(msg)