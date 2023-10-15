from django.core.management.base import BaseCommand

from LiveRank.models import Master,Main,Tags,YT_record,Main_Last1month
from time import sleep
from datetime import date, timedelta, datetime
import random

# from apiclient.discovery import build

import requests, json

import urllib.parse
import pyperclip

from socket import gethostname
hostname = gethostname()

import numpy as np
import cv2

import csv
import pandas
import os

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Record()

def Record():
    a = os.getcwd()
    print(a)

    today = datetime.today()
    if today.hour >= 9:
        recent_day = date.today()
    else:
        recent_day = date.today() - timedelta(days = 1)
    
    os.makedirs("0_kiroku/"+str(recent_day), exist_ok=True)
    
    record_switch = False
    labels = ['総合','男性','女性','個人勢']

    if recent_day.day == 1 or (recent_day.day == 31 or recent_day.day == 30):
        for label in labels:
            # 記録対象のlast1monthを抽出
            print(label)
            if label == '総合':
                mains = Main.objects.all()
            elif label == '男性':
                boy_tag = Tags.objects.get(tag_name = '男性')
                mains = Main.objects.filter(tags=boy_tag)
            elif label == '女性':
                girl_tag = Tags.objects.get(tag_name = '女性')
                mains = Main.objects.filter(tags=girl_tag)
            elif label == '個人勢':
                indies_tag = Tags.objects.get(tag_name = '個人勢')
                mains = Main.objects.filter(tags=indies_tag)

    # ↑本番用(ラベル管理) ↓テスト用
    # if True:
    #     label = "男性"
    #     boy_tag = Tags.objects.get(tag_name = '男性')
    #     mains = Main.objects.filter(tags=boy_tag)

                # 15位に入るライバーを抽出

            # 条件に合う全ライバーをlast1monthの記録を含む形式に変えて辞書配列に変換
            livers = [] # 辞書配列
            cleared = 0
            liverscount = mains.count()
            for liver in mains:
                print(str(cleared) + "/" + str(liverscount))
                # print(liver.name)
                months = Main_Last1month.objects.filter(userid = liver.userid).order_by("day")
                total = 0
                record = []
                for month in months:
                    total += month.superchat_daily
                    # print("day:"+str(month.day))
                    # print("superchat:"+str(month.superchat_daily))
                    record.append(total)
                # print(record)

                tags = []
                tag_objects = liver.tags.all()
                for tag in tag_objects:
                    tags.append(tag.tag_name)
                if "所属：ホロライブ" in tags:
                    tag_ = "ホロライブ"
                elif "所属：にじさんじ" in tags:
                    tag_ = "にじさんじ"
                elif "Vtuber" in tags:
                    if "所属：その他" in tags:
                        tag_ = "Vtuber(その他)"
                    if "個人勢" in tags:
                        tag_ = "Vtuber(個人勢)"
                elif "一般" in tags:
                    tag_ = "一般"
                else: tag_ = ""

                a = {
                    "name":liver.name,
                    # 事務所タグ挿入
                    "tag":tag_,
                    "imageurl":liver.img,
                    "userid":liver.userid,
                    "record":record
                    }
                if len(record) == 31:
                    livers.append(a)
                cleared += 1
            
            top_livers  = [] # 期間中1回でもtop15に入ったライバーの辞書配列
            top_livers_userid = [] # 期間中1回でもtop15に入ったライバーのuserid配列
            top_livers_name = [] # 期間中1回でもtop15に入ったライバーのname配列

            # 31日分繰り返す
            for i in range(0,31):
                # その日のtop15人を抽出
                daily_top_livers = [] # その日のtop15ライバーが格納される辞書配列

                for liver in livers:
                    # まずライバーを無条件にトップリストに加える
                    daily_top_livers.append(liver)
                    # 次に上位15人のみ残す(最小のライバーを出して15人になるまで除外する)
                    while (len(daily_top_livers) > 15):
                        daily_top_livers_record  = []
                        # その日の記録のみの配列を作成, 最小値を導出
                        for liver_ in daily_top_livers:
                            daily_top_livers_record.append(liver_["record"][i])
                        min_record = min(daily_top_livers_record)
                        # 最小値を持つライバーを同定, daily_top_liversから除外
                        for liver_ in daily_top_livers:
                            if liver_["record"][i] == min_record:
                                min_liver = liver_
                        daily_top_livers.remove(min_liver)
                
                print(str(i) + "日目のtop15")
                for l in daily_top_livers:
                    print("name:" + l["name"])
                    print("record:" + str(l["record"][i]))
                print("")
                
                # top15に入ったことがあるuseridを配列に追加
                for one_of_tops in daily_top_livers:
                    if not(one_of_tops["userid"] in top_livers_userid):
                        top_livers_userid.append(one_of_tops["userid"])
                        top_livers_name.append(one_of_tops["name"] + str(i) + "日目, 入賞時スパチャ:" + str(one_of_tops["record"][i]))
                        top_livers.append(one_of_tops)
                
            print(top_livers_userid)
            print(top_livers_name)
            print(len(top_livers_name))

            # ユーザーid取得完了
        
            # 配列内のuseridのlast1monthの写し(name,userid,superchatrecord)をYouTubeレコードに保存
            title = str(recent_day) + "_" + label
            with open('0_kiroku/' + str(recent_day) + "/" + title + '.csv', 'w') as file:
                    # with open('0_kiroku/samune_' + str(recent_day) + "/" + title + '.csv', 'w') as samune_file:
                        writer = csv.writer(file)
                    #     samune_writer = csv.writer(samune_file)
                        header = ["名前","タグ","url"]

                        recording = recent_day - timedelta(days = 30)
                        for i in range(31):
                            month = recording.month
                            day = recording.day
                            header += [str(recording.month) + "/" + str(recording.day)]
                            recording = recording + timedelta(days = 1)
                        writer.writerow(header)

                        for liver in top_livers:
                            row = [liver["name"],liver["tag"],liver["imageurl"]]
                            row += liver["record"]

                            writer.writerow(row)
                        writer.writerow(["ラベル:"+label])