from django.core.management.base import BaseCommand

from django.db.models import Max, Q

from LiveRank.models import Master,Tags,Main,Main_Last1month,Main_Tops
from LiveRank.forms import OrderForm,FindForm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import chromedriver_binary
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup

from time import sleep
from datetime import date, timedelta, datetime
import random
import math

from apiclient.discovery import build

import pytchat
from pytchat import SuperchatCalculator,LiveChat
import requests, json

from socket import gethostname
hostname = gethostname()

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        if "tsudaharujinoMacBook-Pro-2" in hostname:
            Check()
        else:
            print("管理者のPCではないため実行を中断")

def Check():
    # Mainに登録されているユーザーとplayboardにいるユーザーの差分を確認

    # youtubeapiの準備
    # developerKeyはGoogleCloudPlatformで認証して取ってきたAPIキー
        # herokuにはアップロードされているがGithubには非公開
    youtube = build("youtube","v3",developerKey="")

    # 開く
    options = Options()
    # options.add_argument('headless')
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)
    driver.maximize_window()
    driver.get("https://www.google.com/search?q=Playboard&sourceid=chrome&ie=UTF-8")
    driver.find_element(By.CSS_SELECTOR,"a[href='https://playboard.co/en/']").click()
    driver.get("https://playboard.co/en/youtube-ranking/most-superchatted-all-channels-in-japan-monthly") # 月間
    # ↓累計1000万-1500万 + 検索語だが検索はhtml構造が違うのでまだ動かない
    # driver.get("https://playboard.co/en/search?q=VTuber&donationAmount=10000000%3A15000000") 
    # driver.find_element(By.CSS_SELECTOR,'a[href="/en/youtube-ranking/most-superchatted-all-channels-in-japan-daily"]').click()
    # driver.find_element(By.LINK_TEXT, "Most Super Chatted").click()

    b = input("実行する時任意の文字列を入力:")
    # 初期値aから下にスクロールする
    a = -1100
    for n in range(22):
        # sleep(random.uniform(1.5,5.2)) #1.5-5.2秒の間
        a += random.randint(1400,1700)
        driver.execute_script("window.scrollTo(0,{});".format(a))
        sleep(random.uniform(1,2)) #1-2秒

    # htmlの取得
    html = driver.page_source.encode('utf-8')
    soup_total =  BeautifulSoup(html, "html.parser")
    html = 0 # 変数リセットで負担減らそうの会
    sleep(1)

    driver.close()

    # ここforで分岐できたら
    # 実行する時はdo、しない時はpass、それ以外はwhileとかで月間日間週間とかも見れたらいいんじゃね
    soup = soup_total
    update_list = []

    # htmlの中からuseridとスパチャ額を含む部分を摘出
    # 流れ：上から¥を含むスコアタグのtd要素と、そこと並列の孫のnameのh3要素を全部摘出、リストに格納
    userids = soup.select("a.name__label")
    superchat_pasts = soup.select("td:has(a:has(h3)) ~ td.score:-soup-contains('¥')")

    # update_list配列に辞書型で更新要素を格納
    for i,name in enumerate(userids): #enumerateを使うとインデックス番号も回すことができる
        userid = userids[i].get('href').replace('/en/channel/','')
        superchat_past = superchat_pasts[i].get_text(strip = True).replace('¥','').replace(',','')# strip = Trueで空白や改行を削除
        prof = {
            # imgやsubscriber_totalはyoutubeAPIを用いて取得
            'userid' : userid,
            'img' : "https://www.google.com/",
            'name' : "サンプル",
            'superchat_past' : round(int(superchat_past),-4) + random.randint(0,9999), # 4桁切り捨てた後ランダムで0~9999を加算
            'subscriber_total':0
        }
        update_list.append(prof)
    # 取得可否確認
    print(str(update_list[0]["superchat_past"]) + "円を獲得したライバーのデータを一件目に取得")
    soup = 0

    # からの,チャンネル名と登録者情報と画像urlをYouTubeからAPIを用いて取得
        # herokuにはアップロードされているがGithubには非公開
    youtube = build("youtube","v3",developerKey="")
    # Youtubeからuseridを参照してupdate_listにそれぞれ登録者情報を代入
    for i,liver in enumerate(update_list):
        # 取得
        response = youtube.channels().list(
            part = "statistics,snippet",
            id = update_list[i]["userid"]
        ).execute()
        name = response['items'][0]['snippet']["title"]
        if (response['items'][0]['statistics']['hiddenSubscriberCount'] == True):
            subscriber = 0
        else:
            subscriber = response['items'][0]['statistics']['subscriberCount']
        try:
            discription = response['items'][0]['snippet']['description']
        except:
            pass
        img = response['items'][0]['snippet']["thumbnails"]['medium']["url"]
        # updatelistに入れ込む
        update_list[i]["name"] = name
        update_list[i]["subscriber_total"] = subscriber
        update_list[i]["discription"] = discription

    # mainモデルのuseridを配列で出す
    main_userids = Main.objects.all().values_list("userid",flat=True)

    print("以下のライバーが未登録")
    n = 0
    for i,liver in enumerate(update_list):
        # もし取ったデータの中に同一useridがいなかったら新規作成(更新モードの場合いたら更新)
        if not(update_list[i]["userid"] in main_userids):
            print("")
            print("name:"+update_list[i]["name"])
            print("userid:"+update_list[i]["userid"])
            print("superchat_total:"+str(update_list[i]["superchat_past"]))
            print("subscriber_total:"+str(update_list[i]["subscriber_total"]))
            # print("discription:"+ update_list[i]["discription"])
            print("")
            n += 1
    if n == 0:
        print("対象のライバーは全て登録済み")
    else:
        print(str(n) + "人の未登録ライバーを確認")

