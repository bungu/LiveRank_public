from django.core.management.base import BaseCommand

from LiveRank.models import Master,Main,Main_Last1month,Main_Sponsor,Error

from time import sleep
from datetime import date, timedelta, datetime, timezone
from apiclient.discovery import build

import pytchat_patched as pytchat
import requests, json

from socket import gethostname

import smtplib, ssl
from email.mime.text import MIMEText

from dotenv import load_dotenv
import os

from kanjiconv import KanjiConv
import isodate

# .envを読み込む
load_dotenv(".env")

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        Update(updated = [], error_count = 0)

def Update(updated:list, error_count:int):
    '''
    主となる関数 ここから下の関数を呼び出して動かす
    '''
    
    # 想定外のエラーが起きても動くように全体をtryで囲む
    try:
        # 時刻を取得、日本時間に合わせてtodayを設定
        now = datetime.now()
        print("時刻："+ str(now))

        # 時差の関係で0:00~8:59とそれ以外を分岐して処理
        if (now.hour < 9) and ("MacBook" in gethostname()):
            today = now.date() - timedelta(days = 1)
            print("0-9時かつMacでの更新であるため昨日をtodayとして進行")
        else:
            today = now.date()
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
            update_liver_with_yt_api(youtube, liver)
            count += 1
            print(f"進捗：{str(count)}/{str(livers.count())} {liver.name} のAPI系統の更新が完了")
        print("YoutubeAPI関連のメインモデル更新が完了")
        print()

        # スポンサーモデルの更新
        update_sponsors(youtube)
        print("YoutubeAPI関連のスポンサーモデル更新が完了")
        print()

        # 更新したのでMainモデルを保険的に再取得
        livers =  Main.objects.all()

        # 各ライバーについてスーパーチャットとlast1monthの更新
        errored_ids = [] # エラーが発生したライバーのidを格納するリスト
        progress = 0
        for liver in livers:
            progress += 1
            print(f"進捗：{str(progress)}/{livers.count()} {liver.name}")
            if liver.userid in updated:
                print(liver.name + "は今回の実行で既に更新済み")
                continue
            # 欠けているlast1monthを作成
            create_lacking_last1month(today, liver)

            # last1monthの登録者数を更新
            update_last1month_subscriber(today, liver)

            # スーパーチャット, 配信時間の更新 エラーが起きやすい
            response = update_last1month_streaming(today, liver, youtube)
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
        # エラー回数をメールで送信
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

        error_count += 1
        # 想定外のエラーをエラーモデルに保存
        Error(
            error = str(e),
            date = today,
            hostname = gethostname()
        ).save()
        # 30回まで再帰する 既にアップデートが完了しているライバーの配列を渡し、更新しないようにする
        if error_count <= 30:
            Update(updated = updated, error_count = error_count)
        else:
            print("エラーが30回以上発生したため、処理を中止します")
            send_email(
                errored_userids = errored_ids,
                errorcount = error_count
            )
    
def update_liver_with_yt_api(
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

    # ひらがな変換用のオブジェクトを作成
    kanji_conv = KanjiConv(separator="")

    # 取得したjsonから必要な情報を抽出
    # アカウント削除等で取得できない時のために例外処理
    try: 
        name = response['items'][0]['snippet']["title"]
        if (response['items'][0]['statistics']['hiddenSubscriberCount'] == True):
            subscriber = 0
        else:
            subscriber = response['items'][0]['statistics']['subscriberCount']
        # 概要欄と画像URLの取得は失敗したとしても続行できるため別途例外処理
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

        # 検索用に、概要欄,名前欄をひらがなに変換して保存
        for text_ in [liver.name, liver.discription]:
            # テキストからアルファベットと記号を排除
            text = ''.join([char for char in text_ if '\u4e00' <= char <= '\u9fff' or '\u3040' <= char <= '\u30ff' or char.isspace()])
            hiragana_text = str(kanji_conv.to_hiragana(text))
            # hiragana_textから「きごう」という文字列を排除 排除しきれない記号文字が「きごう」と表現されるため
            hiragana_text = hiragana_text.replace("きごう", "")
            if text_ == liver.name:
                liver.name_hiragana = hiragana_text
            else:
                liver.discription_hiragana = hiragana_text

        if (liver.tags.all()):
            liver.tagcheck = True
        else:
            liver.tagcheck = False
        
        # 保存
        liver.save()

    # 例外が起きた場合はエラーを表示して非更新対象とする
    # チャンネル消去でよく起こるエラーであるため保存しない
    except:
        import traceback
        traceback.print_exc()
        print("userid:"+liver.userid+"のライバーは上記のエラーで非更新対象")

def update_sponsors(youtube: object):
    '''
    スポンサーモデルを更新
    上と異なる処理であるため別に実行
    '''
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
    ライバーの昨日までの欠けているlast1monthレコードを作成する関数
    last1monthレコードには過去1ヶ月分のライバーの登録者数、スーパーチャット、配信時間が記録される
    """
    # ユーザーIDを取得
    userid = liver.userid

    # last1monthのレコードを取得、日付の配列を作成
    months = Main_Last1month.objects.filter(userid=userid)
    months_days = months.values_list("day",flat=True)
    
    # 昨日までの範囲で「ない日」のlast1monthを作る
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

def live_duration(
        yt: object,  
        video_id: str
        ):
    '''
    配信時間を取得する関数
    yt: YoutubeAPIオブジェクト
    video_id: ビデオID
    '''     
    it = yt.videos().list(part="liveStreamingDetails,contentDetails", id=video_id).execute()["items"][0]
    l = it.get("liveStreamingDetails") or {}
    if "actualStartTime" in l:
        s = datetime.fromisoformat(l["actualStartTime"].replace("Z", "+00:00"))
        # 終了時間がない場合は現在時刻を代入
        e = l.get("actualEndTime")
        e = datetime.fromisoformat(e.replace("Z", "+00:00")) if e else datetime.now(timezone.utc)
        return e - s
    # actualStartTimeがない場合はdurationを返す
    return isodate.parse_duration(it["contentDetails"]["duration"])

def update_last1month_subscriber(
        today: date,
        liver: object
    ):
    ''' 
    last1monthの登録者数を更新する関数
    '''
    # ユーザーIDを取得
    userid = liver.userid

    # last1monthのレコードを取得
    all_last_1months = Main_Last1month.objects.filter(userid = userid).order_by("day").reverse()

    # 最新のレコードの登録者数を更新
    latest_month = all_last_1months.first()
    latest_month.subscriber_total = liver.subscriber_total
    latest_month.subscriber_lastupdate = today
    latest_month.save()

    # 登録者数が欠けている日のレコードを更新
    near_subscriber_total = latest_month.subscriber_total
    for month in all_last_1months:
        # 登録者数がintにキャストできるかどうか、0でないか確認
        try:
            int(month.subscriber_total)
            assert int(month.subscriber_total) != 0
            near_subscriber_total = month.subscriber_total # 通過すれば最近の値として保存
        except:
            # 登録者数が欠けている場合、最近(未来側)の登録者数を代入する
            month.subscriber_total = near_subscriber_total
            month.subscriber_lastupdate = today
            month.save()

def update_last1month_streaming(
        today: date,
        liver:object,
        youtube: object
    ):
    '''
    過去1ヶ月のスーパーチャットと配信時間を更新する関数
    '''

    # 日本円に変換するために通貨の配列をAPIから取得しておく
    url = requests.get("http://api.aoikujira.com/kawase/json/jpy")
    text = url.text
    json_currency = json.loads(text)

    # ユーザーIDを取得
    userid = liver.userid

    # エラーが起きたかどうかを記録する変数
    errored = False

    # 更新されてない日の動画を取得

    # 全てのmonthsを取得
    months = Main_Last1month.objects.filter(userid=userid) # 更新

    # 過去のレコードのうちスパチャが欠けてる日(lastupdateがデフォルトである日)の最小値を取得
    # 欠けてる日のレコードを格納する配列
    superchat_yet_months = []

    for month in months:
        if month.streaming_lastupdate == date(2020,1,1) and month.day < today:
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
    print("予定個数:" + str(len(response["items"])))
    print("superchat_yet_months:" + str(superchat_yet_months))
    for i in range(len(response["items"])):
        # エラーが起きない動画のみ扱う
        try:
            # 日付を確認
            publish_raw = response["items"][i]["snippet"]["publishedAt"]
            publish_dt = datetime.fromisoformat(publish_raw.replace("Z", "+00:00"))
            publish_date = publish_dt.date()
            # superchat_yet_months(スパチャが更新されていないレコード)にある日付に出た動画なら保存
            print("動画投稿日:" + str(publish_date))
            print("未更新フラグ:" + str(publish_date in superchat_yet_months))
            if publish_date in superchat_yet_months:
                yet = {
                    "day": publish_date,
                    "videoid": response["items"][i]["id"]["videoId"],
                    "title": response["items"][i]["snippet"]["title"],
                    "publishTime": publish_dt.strftime("%Y-%m-%d %H:%M")
                }
                print("タイトル：" + yet["title"])
                print("投稿日時：" + yet["publishTime"] + "\n")
                yet_videos.append(yet)
        except:
            errored = True
            import traceback
            traceback.print_exc()
            
    # Pychatにかけてスパチャを取得
    for n in range(len(yet_videos)):
        default_superchat = -1 
        default_duration = timedelta(seconds=0)
        yet_videos[n]["superchat"] = default_superchat
        yet_videos[n]["duration"] = default_duration
        try:
            videoid_ = yet_videos[n]["videoid"]
            print('タイトル:' + yet_videos[n]["title"])
            print('videoid:' + videoid_)
            print('publishTime:' + yet_videos[n]["publishTime"])
            try:
                duration = live_duration(youtube, videoid_)
                yet_videos[n]["duration"] = duration
                print('配信時間:' + str(duration))
            except Exception:
                import traceback
                traceback.print_exc()
                print("配信時間の取得に失敗")
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

    # last1monthのスパチャと配信時間を更新
    if len(yet_videos) > 0:
        for yet in yet_videos:
            month = Main_Last1month.objects.filter(userid = liver.userid).filter(day = yet["day"])[0]
            if yet["duration"] != default_duration: # 配信時間が取得できている場合、配信時間を加算する
                month.stream_time_daily = month.stream_time_daily + yet["duration"]
            if yet["superchat"] != default_superchat: # スパチャが取得できている場合、スパチャ額を加算する
                month.superchat_daily = month.superchat_daily + yet["superchat"]
                month.streaming_lastupdate = today
            month.save()

            # スパチャが更新された場合、streaming_lastupdateを更新する
            if yet["superchat"] != default_superchat:
                month = Main_Last1month.objects.filter(userid = liver.userid).filter(day = yet["day"])[0]
                # 後からアーカイブが公開される可能性等を考慮し、記録なしかつ今日から5日以内の場合streaming_lastupdateをデフォに戻しておく
                if month.superchat_daily == 0 and timedelta(days = 1) <= today - month.day < timedelta(days = 5):
                    month.streaming_lastupdate = date(2020,1,1)
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
    # 年初は配信時間の累計をリセット（当年専用のため）
    if today.month == 1 and today.day == 1:
        liver.stream_time_yearly = timedelta(seconds=0)
        liver.stream_time_past = timedelta(seconds=0)
        liver.save()

    # monthsの中で32日前以前があったら消してMainのsuperchat_pastを更新
    months = Main_Last1month.objects.filter(userid = liver.userid)
    for month in months:
        if month.day < today - timedelta(days = 31):
            print("統合前のsuperchatpastは"+str(liver.superchat_past))
            print(str(month.day) + "のスパチャ記録は" + str(month.superchat_daily))
            liver.superchat_past = liver.superchat_past + month.superchat_daily
            # 当年分のみ「last1month外の配信時間」として加算
            if month.day.year == today.year:
                liver.stream_time_past = liver.stream_time_past + month.stream_time_daily
            liver.LastUpdate_SuperchatPast = today
            if month.day.year == today.year:
                liver.LastUpdate_StreamTimePast = today
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
    
    # 直近7件までの合計を週次、最新1件を日次として扱う
    if countable.count() > 0:
        months_7 = countable[:7]
        for i in months_7:
            superchat_weekly += i.superchat_daily
        # daily記録は最新のlast1monthのスパチャを取得（型チェックは従来通り）
        try:
            int(countable[0].superchat_daily)
            superchat_daily = countable[0].superchat_daily
        except:
            superchat_daily = 0
    else:
        superchat_weekly = 0
        superchat_daily = 0

    # 期間系登録者数の更新
    countable_subscriber = Main_Last1month.objects.filter(userid=liver.userid).filter(subscriber_total__gt=0).order_by("day").reverse()

    countable_subscriber_count = countable_subscriber.count()

    # countableの数が0でない場合、通常更新
    if countable_subscriber_count > 0:

        # 月次登録者数記録の導出
        # 現在→過去日付順で並べているため、最後の要素を取ると「登録者記録が0ではない最も前の記録」を出すことができる
        oldest_subscriber = countable_subscriber.last().subscriber_total
        newest_subscriber = countable_subscriber[0].subscriber_total

        subscriber_monthly = newest_subscriber - oldest_subscriber

        # 週間登録者数記録の導出（直近7件までの差分）
        recent_subscribers = list(countable_subscriber[:7])
        subscriber_weekly = newest_subscriber - recent_subscribers[-1].subscriber_total

        # 日間登録者数記録の導出（最新1件の差分）
        if countable_subscriber_count >= 2:
            subscriber_daily = newest_subscriber - countable_subscriber[1].subscriber_total
        else:
            subscriber_daily = 0

    # countableの数が0の場合、期間系登録者数は全て0
    else:
        subscriber_monthly = 0
        subscriber_weekly = 0
        subscriber_daily = 0

    # 期間系配信時間の更新
    # 今日より前のlast1monthだけを対象にする
    countable_stream = Main_Last1month.objects.filter(userid=liver.userid).filter(day__lt=today).order_by("day").reverse()
    stream_time_monthly = timedelta(seconds=0)
    stream_time_weekly = timedelta(seconds=0)

    # 月間の更新
    for month in countable_stream:
        stream_time_monthly += month.stream_time_daily

    # 週間・日間の更新（直近7件までの合計 / 最新1件）
    if countable_stream.count() > 0:
        months_7 = countable_stream[:7]
        for i in months_7:
            stream_time_weekly += i.stream_time_daily
        stream_time_daily = countable_stream[0].stream_time_daily
    else:
        stream_time_weekly = timedelta(seconds=0)
        stream_time_daily = timedelta(seconds=0)

    # 年次は当年分の合計
    year_streams = Main_Last1month.objects.filter(
        userid=liver.userid,
        day__year=today.year,
        day__lt=today
    )
    stream_time_yearly = liver.stream_time_past
    for month in year_streams:
        stream_time_yearly += month.stream_time_daily
    
    # 更新
    liver.superchat_total = liver.superchat_past + superchat_monthly

    liver.superchat_monthly = superchat_monthly
    liver.superchat_weekly = superchat_weekly
    liver.superchat_daily = superchat_daily

    liver.subscriber_monthly = subscriber_monthly
    liver.subscriber_weekly = subscriber_weekly
    liver.subscriber_daily = subscriber_daily

    liver.stream_time_monthly = stream_time_monthly
    liver.stream_time_weekly = stream_time_weekly
    liver.stream_time_daily = stream_time_daily
    liver.stream_time_yearly = stream_time_yearly

    liver.save()

# 送信先のアドレス、パスキーを環境変数から取得
send_address = os.environ["ADMIN_MAIL_ADDRESS"]
pass_key = os.environ["ADMIN_MAIL_PASSKEY"]

# メールを送信する関数
def send_email(
        errored_userids: list,
        error_count: int
    ):
    if len(errored_userids) != 0 or error_count != 0:
        msg = make_mime_text(
            mail_to = send_address,
            subject = "エラー発生",
            body = f"今日の更新においてエラーが発生しました \nスパチャエラー:{str(len(errored_userids))}回 想定外のエラー:{str(error_count)}回 <br> https://www.liverank.jp/admin/"
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
