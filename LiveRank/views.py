from django.shortcuts import render,redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Max, Q
from django.core.paginator import Paginator
from django.views import View

from .models import Master,Tags,Main,Main_Last1month,Main_Tops,Ubi_user,Ubi_video,ChatSession, ChatMessage
from .forms import OrderForm,FindForm,VideoForm,ChatForm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import chromedriver_binary
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup

from time import sleep
import locale
from datetime import date, timedelta, datetime
import random
import math

from apiclient.discovery import build

import pytchat
from pytchat import SuperchatCalculator,LiveChat
import requests, json

#gpt
import openai
import re
import os
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt

'''

コードについての説明
クライアントからリクエストが送られた際の処理群が書かれている.
例)ランキングページの場合: 絞り込みの条件に沿った文章(title,h1,h2)を生成, 表示するために条件に合う配信者のデータセットを指定された順序で生成, それらをクライアントに返す.

1013行目以降は大学で履修していた授業のグループワークでこのサイト用の環境を利用していたものであり, このwebサイトとの関係は無い.

'''


# Create your views here.
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 日本語のパラメーターを用意
def set_jap_params(term,order):
    # orderの設定
    if(order == "superchat"):
        order_jap = "スパチャ"
    elif(order == "subscriber"):
        order_jap = "登録者数"
    # termの設定
    if term == "total":
        term_jap = "累計"
    elif term == "monthly":
        term_jap = "月間"
    elif term == "weekly":
        term_jap = "週間"
    elif term == "daily":
        term_jap = "日間"
    
    return {"term_jap":term_jap, "order_jap":order_jap}

# 昨日の日付とデータの分け方を定義
def set_kinou_wakekata():
    kinou = Master.objects.all()[0].last_update
    wakekata = 10
    return {"kinou":kinou, "wakekata":wakekata}

def access_count():
    master = Master.objects.all()[0]
    Master(
        id = master.id,
        last_update = master.last_update,
        pv_count = master.pv_count + 1
    ).save()

def ranking(request,term,order,page):

    access_count()

    if (request.method == 'POST'):
        order = request.POST['order']
    
    term_jap = set_jap_params(term,order)['term_jap']
    order_jap = set_jap_params(term,order)['order_jap']

    kinou = set_kinou_wakekata()["kinou"]
    wakekata = set_kinou_wakekata()["wakekata"]

    h1 = "<div class='tag_h1'><span>"+str(kinou.year)+"</span>年<span>"+str(kinou.month)+"</span>月<span> <div class='tag_h1'>" + term_jap + order_jap + "ランキング"
    kenme = str((page - 1)*wakekata + 1) + "-" + str(page*wakekata)

    if term == "total":
        jikan = datetime.strftime(kinou,'%Y年%m月%d日')+"時点"
    elif term == "monthly":
        a_month_ago = kinou - timedelta(days=31)
        jikan = datetime.strftime(a_month_ago,'%Y年%m月%d日') + datetime.strftime(kinou,' - %Y年%m月%d日')
    elif term == "weekly":
        a_week_ago = kinou - timedelta(days=6)
        jikan = datetime.strftime(a_week_ago,'%Y年%m月%d日') + datetime.strftime(kinou,' - %Y年%m月%d日')
    elif term == "daily":
        jikan = datetime.strftime(kinou,'%Y年%m月%d日')


    if order == "superchat":
        h2 = jikan +  "のスーパーチャット収益ランキングです。\n"+kenme+"件目を表示しています。"
    elif order == "subscriber":
        h2 = jikan + "のチャンネル登録者数のランキングです。\n"+kenme+"件目を表示しています。"
    data = Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).reverse() # prefetch_relatedはN+1問題対策
    pagedata = Paginator(data,wakekata).get_page(page)
    total_pages = []
    for i in range(math.ceil(data.count()/wakekata)):
        total_pages.append(i+1)
    master_lastupdate = Master.objects.get(id = 1).last_update
    params = {
        "title":str(kinou.year)+"年"+str(kinou.month)+"月 " + term_jap + order_jap + "ランキング | ライブランク！",
        "master_lastupdate":master_lastupdate,
        "h1":h1,
        "h2":h2,
        "data":pagedata,
        "total_pages" :total_pages,
        "ranking_addition_number":(page-1) * wakekata ,
        "ichigyo": wakekata / 2,
        "orderform":OrderForm(),
        "findform":FindForm(),
        "term":term,
        "order":order,
        "term_jap":term_jap,
        "order_jap":order_jap,
        "page":page,
        "tagcheck":False,
        "findcheck":False,
    }
    if (request.method == 'POST'):
        params["orderform"] = OrderForm(request.POST)
    return render(request,"LiveRank/ranking.html",params)

def ranking_top(request):

    access_count()

    order = "superchat"
    term = "monthly"
    page = 1
    order_jap = "スパチャ"
    term_jap = ""

    kinou = set_kinou_wakekata()["kinou"]
    wakekata = set_kinou_wakekata()["wakekata"]

    h1 = "<div class='tag_h1'><span>"+str(kinou.year)+"</span>年<span>"+str(kinou.month)+"</span>月<span> <div class='tag_h1'>" + term_jap + order_jap + "ランキング"
    kenme = str((page - 1)*wakekata + 1) + "-" + str(page*wakekata)
    if order == "superchat":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のスーパーチャット収益ランキングです。\n"+kenme+"件目を表示しています。"
    elif order == "subscriber":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のチャンネル登録者数のランキングです。\n"+kenme+"件目を表示しています。"
    
    data = Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).reverse() # prefetch_relatedはN+1問題対策
    pagedata = Paginator(data,wakekata)
    total_pages = []

    for i in range(math.ceil(data.count()/wakekata)):
        total_pages.append(i+1)
    master_lastupdate = Master.objects.get(id = 1).last_update
    params = {
        "title":"ライブランク！：YouTube" +order_jap + "ランキング【毎日更新】",
        "master_lastupdate":master_lastupdate,
        "h1":h1,
        "h2":h2,
        "data":pagedata.get_page(page),
        "total_pages" :total_pages,
        "ranking_addition_number":(page-1) * wakekata ,
        "ichigyo": wakekata / 2,
        "orderform":OrderForm(),
        "findform":FindForm(),
        "term":term,
        "order":order,
        "term_jap":term_jap,
        "order_jap":order_jap,
        "page":page,
        "tagcheck":False,
        "findcheck":False,
    }
    return render(request,"LiveRank/ranking.html",params)


def redirect_to_top(request):
    return redirect(to="/ranking")

def tag_ranking(request,term,tag,order,page):

    access_count()

    term_jap = set_jap_params(term,order)['term_jap']
    order_jap = set_jap_params(term,order)['order_jap']

    kinou = set_kinou_wakekata()["kinou"]
    wakekata = set_kinou_wakekata()["wakekata"]

    kenme = str((page - 1)*wakekata + 1) + "-" + str(page*wakekata)
    total_pages = []

    if order == "superchat":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のスーパーチャット収益ランキングです。\n"+kenme+"件目を表示しています。"
    elif order == "subscriber":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のチャンネル登録者数のランキングです。\n"+kenme+"件目を表示しています。"
    
    # 以下複数タグ処理の場合のタグの抽出
    if "+" in tag:

        # 同じ列のオブジェクトはOR,違う列のオブジェクトはANDで検索したい
        livetype = ["Vtuber","一般"]
        gender = ["女性","男性"]
        agency = ["所属：ホロライブ","所属：にじさんじ","所属：その他","個人勢"]
        other_filter = ["音楽","Global","国内"]
        filter_kinds = [livetype,agency,gender,other_filter]
        qs = [Q(),Q(),Q(),Q()]
        tags = tag.split("+")

        tag_h = ""
        for i,filter_kind in enumerate(filter_kinds):
            for t in tags:
                if t in filter_kind:
                    if t != "国内":
                        tag_object = Tags.objects.get(tag_name = t)
                        qs[i].add(Q(tags = tag_object),Q.OR)
                    elif t == "国内":
                        tag_object = Tags.objects.get(tag_name = "Global")
                        qs[i].add(~Q(tags = tag_object),Q.OR)
                    tag_h += t + " / "
        tag_h = tag_h[:len(tag_h)-3]
        # Qのandはなんか動かんかったのでfilterで擬似and
        data = Main.objects.prefetch_related("tags").filter(qs[0]).filter(qs[1]).filter(qs[2]).filter(qs[3]).order_by(order+"_"+term).reverse()
        h1 = "<div class='tag_h1'>" +tag_h+ " の</div>" + order_jap + "ランキング(" + term_jap + ")"
        title ="ライブランク！：" +  tag_h.replace("/","") + "の" + order_jap + "ランキング"
        
    else:
        if tag != "国内":
            tag_object = Tags.objects.get(tag_name = tag)
            title = "ライブランク！：" + tag_object.tag_name+" の" + order_jap + "ランキング"
            h1 = "<div class='tag_h1'>" +tag_object.tag_name+ " の</div>" + order_jap + "ランキング(" + term_jap + ")"
            data = Main.objects.prefetch_related("tags").filter(tags=tag_object).order_by(order+"_"+term).reverse()
        elif tag == "国内":
            tag_object = Tags.objects.get(tag_name = "Global")
            title = "ライブランク！：国内 の" + order_jap + "ランキング"
            h1 = "<div class='tag_h1'>国内 の</div>" + order_jap + "ランキング(" + term_jap + ")"
            data = Main.objects.prefetch_related("tags").exclude(tags=tag_object).order_by(order+"_"+term).reverse()
    
    pagedata = Paginator(data,wakekata)
    for i in range(math.ceil(data.count()/wakekata)):
        total_pages.append(i+1)

    master_lastupdate = Master.objects.get(id = 1).last_update

    params = {
        "title":title,
        "master_lastupdate":master_lastupdate,
        "h1":h1,
        "h2":h2,
        "data":pagedata.get_page(page),
        "total_pages" :total_pages,
        "ranking_addition_number":(page-1) * wakekata,
        "orderform":OrderForm(),
        "term":term,
        "order":order,
        "term_jap":term_jap,
        "order_jap":order_jap,
        "tagname":tag,
        "page":page,
        "tagcheck":True,
        "findcheck":False,
    }
    
    return render(request,"LiveRank/ranking.html",params)

def tag_top(request,tag):

    access_count()

    order = "superchat"
    term = "total"
    order_jap = "スパチャ"
    term_jap = "累計"
    page = 1

    kinou = set_kinou_wakekata()["kinou"]
    wakekata = set_kinou_wakekata()["wakekata"]

    kenme = str((page - 1)*wakekata + 1) + "-" + str(page*wakekata)
    total_pages = []

    h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のスーパーチャット収益ランキングです。\n"+kenme+"件目を表示しています。"
    
    # 以下データの抽出
    tag_object = Tags.objects.get(tag_name = tag)
    title ="ライブランク！：" + tag_object.tag_name+" の" + order_jap + "ランキング"
    h1 = "<div class='tag_h1'>" +tag_object.tag_name+ " の</div>" + order_jap + "ランキング(" + term_jap + ")"
    data = Main.objects.prefetch_related("tags").filter(tags=tag_object).order_by(order+"_"+term).reverse()
    
    pagedata = Paginator(data,wakekata)
    for i in range(math.ceil(data.count()/wakekata)):
        total_pages.append(i+1)

    master_lastupdate = Master.objects.get(id = 1).last_update

    params = {
        "title":title,
        "master_lastupdate":master_lastupdate,
        "h1":h1,
        "h2":h2,
        "data":pagedata.get_page(page),
        "total_pages" :total_pages,
        "ranking_addition_number":(page-1) * wakekata,
        "orderform":OrderForm(),
        "term":term,
        "order":order,
        "term_jap":term_jap,
        "order_jap":order_jap,
        "tagname":tag,
        "page":page,
        "tagcheck":True,
        "findcheck":False,
    }
    
    return render(request,"LiveRank/ranking.html",params)

def filter(request,term,order):
    filters = {
        "vtuber":"Vtuber",
        "notV":"一般",
        "nijisanji":"所属：にじさんじ",
        "hololive":"所属：ホロライブ",
        "others":"所属：その他",
        "indivisuals":"個人勢",
        "female":"女性",
        "male":"男性",
        "Global":"Global",
        "music":"音楽",
        "japan":"国内",
        }
    active_filters = []
    tags = ""
    for f in list(filters.keys()):
        if request.POST.get(f):
            active_filters.append(f)
            tags += (filters[f] + "+")
    if len(tags) == 0:
        return redirect(to='/ranking/superchat/total/1')
    tags = tags[:len(tags)-1]
    # params = {
    #     "a":request.POST.get("vtuber"),
    #     "b":tags,
    #     "c":active_filters
    # }
    # return render(request,"LiveRank/filter_test.html",params)
    return redirect(to='/ranking/' + order + '/' + term + '/' +tags+'/1')

def find_ranking(request,term,order,find,page):

    access_count()

    term_jap = set_jap_params(term,order)['term_jap']
    order_jap = set_jap_params(term,order)['order_jap']

    kinou = set_kinou_wakekata()["kinou"]
    wakekata = set_kinou_wakekata()["wakekata"]

    q = Q()
    q.add(Q(name__icontains = find),Q.OR)
    q.add(Q(discription__icontains = find),Q.OR) #icontainsだと大文字小文字を区別しない
    # タグ名を検索に含める処理
    if Tags.objects.filter(tag_name__icontains = find).count() >= 1:
        tag = Tags.objects.filter(tag_name__icontains = find)[0]
        q.add(Q(tags = tag),Q.OR)
        data = Main.objects.prefetch_related("tags").filter(q).distinct(order+"_"+term).order_by(order+"_"+term).reverse()
    else:
        data = Main.objects.filter(q).order_by(order+"_"+term).reverse()
    pagedata = Paginator(data,wakekata)
    total_pages = []
    for i in range(math.ceil(data.count()/wakekata)):
        total_pages.append(i+1)
    h1 = find +" に関連するライバーの" + order_jap + "ランキング(" + term_jap + ")"
    kenme = str((page - 1)*wakekata + 1) + "-" + str(page*wakekata)
    if order == "superchat":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のスーパーチャット収益ランキングです。\n検索ワードがチャンネル名、タグ、概要欄のいずれかに含まれるライバーが表示されます。\n"+kenme+"件目を表示しています。"
    elif order == "subscriber":
        h2 = datetime.strftime(kinou,'%Y年%m月%d日')+"時点のチャンネル登録者数のランキングです。\n検索ワードがチャンネル名、タグ、概要欄のに含まれるライバーが表示されます。\n"+kenme+"件目を表示しています。"
    if data.count() == 0:
        h2 = h2 + "\n配信者の登録申請は下記お問い合わせフォームよりお願い致します。"

    master_lastupdate = Master.objects.get(id = 1).last_update
    params = {
        "title":"ライブランク！：" + find +" に関連するライバーの" + order_jap + "ランキング",
        "master_lastupdate":master_lastupdate,
        "h1":h1,
        "h2":h2,
        "data":pagedata.get_page(page),
        "total_pages" :total_pages,
        "ranking_addition_number":(page-1) * wakekata,
        "orderform":OrderForm(),
        "term":term,
        "order":order,
        "term_jap":term_jap,
        "order_jap":order_jap,
        "find":find,
        "page":page,
        "tagcheck":False,
        "findcheck":True,
    }
    
    return render(request,"LiveRank/ranking.html",params)

def find(request):
    if(request.method == "POST"):
        if request.POST.get('find') != "":
            find = request.POST.get('find')
            return redirect(to="find_ranking/superchat/total/"+find+"/1")
        else:
            return redirect(to="ranking/superchat/total/1")
    else:
        return redirect(to="ranking/superchat/total/1")
        # return redirect(to="")


def liver(request,userid):

    access_count()

    liver = Main.objects.get(userid=userid)
    day_records = Main_Last1month.objects.filter(userid=userid).filter(day__lte=date.today() - timedelta(days=1)).order_by("day").reverse()
    daylist = day_records.values_list("day",flat=True)
    days = list(map(str, daylist))

    dailylist = Main_Last1month.objects.filter(userid=userid).filter(day__lte=date.today() - timedelta(days=1)).order_by("day").reverse()
    dailyslist_chat = dailylist.values_list("superchat_daily",flat=True)
    dailys_chat = list(map(str, dailyslist_chat))

    # 加算版(スパチャ)
    chat_sum = []
    a = 0
    dailyslist_chat_reverse = dailyslist_chat.reverse()
    for daily in dailyslist_chat_reverse:
        a += daily
        chat_sum.append(a)

    totals_subsc = Main_Last1month.objects.filter(userid=userid).filter(day__lt=date.today()  - timedelta(days=1)).values_list("subscriber_total",flat=True).order_by("day").reverse()
    # デイリー(差分)と加算版を取得する必要がある
    # デイリー(差分)
    dailys_subsc = []
    for i in range(len(totals_subsc)-1):
        if not(totals_subsc[i+1] == 0):
            a =  totals_subsc[i] - totals_subsc[i+1]
        else:
            a = 0
        dailys_subsc.append(a)
    dailys_subsc = list(map(int, dailys_subsc))
    dailys_subsc.reverse()
    

    # 加算版(登録者)
    subsc_sum = list(map(int, totals_subsc))
    a = 0
    # for daily in dailys_subsc:
    #     a += daily
    #     subsc_sum.append(a)
    

    # ランキングナンバー取得
    orders = ["superchat","subscriber"]
    terms = ["total","monthly","weekly","daily"]
    numbering = {}
    for order in orders:
        for term in terms:
            livers = Main.objects.all().order_by(order+"_"+term).reverse()
            for i,liver_ in enumerate(livers):
                if liver_.userid == liver.userid:
                    numbering[term+"_"+order+"_rank"] = i + 1 # iは1つ少ないため
                    if numbering[term+"_"+order+"_rank"] % 10 == 0:
                        numbering[term+"_"+order+"_pagenumber"] = math.floor(numbering[term+"_"+order+"_rank"] / 10)
                    else:
                        numbering[term+"_"+order+"_pagenumber"] = math.floor(numbering[term+"_"+order+"_rank"] / 10) + 1
    print(numbering)
    
    master_lastupdate = Master.objects.get(id = 1).last_update

    params = {
        "title":str(liver.name) + "のスパチャ収益、チャンネル登録者数のページ【毎日更新】",
        "master_lastupdate":master_lastupdate,
        "liver":liver,
        "userid":userid,
        "days":days,
        "day_records":day_records,
        "daily_superchat": dailys_chat,
        "sum_superchat": chat_sum,
        "daily_subscriber": dailys_subsc,
        "sum_subscriber": subsc_sum,

        "total_superchat_rank": numbering["total_superchat_rank"],
        "weekly_superchat_rank": numbering["weekly_superchat_rank"],
        "monthly_superchat_rank": numbering["monthly_superchat_rank"],

        "total_subscriber_rank": numbering["total_subscriber_rank"],
        "weekly_subscriber_rank": numbering["weekly_subscriber_rank"],
        "monthly_subscriber_rank": numbering["monthly_subscriber_rank"],

        "total_subscriber_pagenumber": numbering["total_subscriber_pagenumber"],
        "total_superchat_pagenumber": numbering["total_superchat_pagenumber"],

        "monthly_subscriber_pagenumber": numbering["monthly_subscriber_pagenumber"],
        "monthly_superchat_pagenumber": numbering["monthly_superchat_pagenumber"],

        "weekly_subscriber_pagenumber": numbering["weekly_subscriber_pagenumber"],
        "weekly_superchat_pagenumber": numbering["weekly_superchat_pagenumber"],
    }
    
    return render(request,"LiveRank/liver.html",params)

def policy(request):

    access_count()

    params = {}
    return render(request,"LiveRank/policy.html",params)

def statistic_policy(request):

    access_count()

    params = {}
    return render(request,"LiveRank/statistic_policy.html",params)

def add(request):
    if (request.method == 'POST'):
        main_userids = Main.objects.all().values_list("userid",flat=True)
        userid = request.POST.get('userid')
        superchat_total = request.POST.get('superchat_total')
        superchat_past = request.POST.get('superchat_total')
        # パスワード確認
        if request.POST.get('pass') == 'opayouliverank':
            # 新規登録の時のみ実行
            if not userid in main_userids:
                # YouTubeから登録者,概要,サムネURLを更新
                youtube = build("youtube","v3",developerKey="")
                data = youtube.channels().list(
                        part = "statistics,snippet",
                        id = userid
                            ).execute()
                print(data)
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

                # last1monthを昨日から一ヶ月後まで作成
                for i in range(31):
                    Main_Last1month(
                        userid = userid,
                        name = name,
                        # 今日から31日後まで
                        day = date.today() + timedelta(days = i-1),
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
                print("登録済みのライバーです")
        else:
            print("passエラー")
        return redirect(to='/admin/LiveRank/main/')
    else: 
        params = {}
        return render(request,"LiveRank/add.html",params)

def no1(request):
    orders = ["superchat","subscriber"]
    terms = ["total","monthly","weekly","daily"]
    # もしorderとtermが規定のもの以外だったらパス
    if not(request.POST.get('order') in orders) and not(request.POST.get('order') in terms):
        params = {
            "title":" 1位画像作成",
            "to":"no1"
        }
        return render(request,"LiveRank/bunki.html",params)
    if (request.method == 'POST'):
        if request.POST.get('pass') == "opayouliverank":
            order = request.POST.get('order')
            term = request.POST.get('term')
            if request.POST.get('tag') == "hololive":
                tagcheck = True
                tag = "所属：ホロライブ"
            else:
                tagcheck = False
            global_tag = Tags.objects.get(tag_name = "Global")

            if tagcheck == True:
                tag_object = Tags.objects.get(tag_name = tag)
                topliver = Main.objects.all().order_by(order+"_"+term).filter(tags = tag_object).reverse()[0]
            else:
                topliver = Main.objects.all().order_by(order+"_"+term).exclude(tags = global_tag).reverse()[0]

            if len(topliver.name) > 19:
                livername_dan = 2
            else:
                livername_dan = 1
            # 曜日
            locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
            youbi = "(" + Master.objects.get(id = 1).last_update.strftime('%a') + ")"

            params = {
                "liver":topliver,
                "last_update":Master.objects.get(id = 1).last_update,
                "youbi":youbi,
                "livername_dan":livername_dan,
                "term":term,
                "tagcheck":tagcheck
            }
            return render(request,"LiveRank/no1.html",params)
        else:
            params = {
                "title":"1位画像作成",
                "to":"no1"
            }
            return render(request,"LiveRank/bunki.html",params)
    else:
        params = {
            "title":"1位画像作成",
            "to":"no1"
        }
        return render(request,"LiveRank/bunki.html",params)

def no2_4(request):
    if (request.method == 'POST'):
        orders = ["superchat","subscriber"]
        terms = ["total","monthly","weekly","daily"]
        # もしorderとtermが規定のもの以外だったらパス
        if not(request.POST.get('order') in orders) and not(request.POST.get('order') in terms):
            params = {
                "title":"2-4位画像作成",
                "to":"no2_4"
            }
            return render(request,"LiveRank/bunki.html",params)
        elif request.POST.get('pass') == "opayouliverank":
            order = request.POST.get('order')
            term = request.POST.get('term')
            if request.POST.get('tag') == "hololive":
                tagcheck = True
                tag = "所属：ホロライブ"
            else:
                tagcheck = False

            page = 1
            wakekata = 10
            global_tag = Tags.objects.get(tag_name = "Global")
            if tagcheck == False:
                data = Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).exclude(tags = global_tag).reverse()[1:4] # prefetch_relatedはN+1問題対策
            elif tagcheck == True:
                tag_object = Tags.objects.get(tag_name = tag)
                data = Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).filter(tags = tag_object).reverse()[1:4] # prefetch_relatedはN+1問題対策

            pagedata = Paginator(data,wakekata)
            master_lastupdate = Master.objects.get(id = 1).last_update
            params = {
                "data":pagedata.get_page(page),
                "ranking_addition_number":1,
                "ichigyo": wakekata / 2,
                "term":term,
                "order":order,
                "page":page,
                "tagcheck":tagcheck,
                "findcheck":False,
            }
            return render(request,"LiveRank/no2_4.html",params)
        else:
            params = {
                "title":"2-4位画像作成",
                "to":"no2_4"
            }
            return render(request,"LiveRank/bunki.html",params)
    else:
        params = {
            "title":"2-4位画像作成",
            "to":"no2_4"
        }
        return render(request,"LiveRank/bunki.html",params)


def register(request):
    # mainが存在しない or mainがあるかlast1monthが存在しないライバーを対象に処理

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
    driver.get("https://playboard.co/en/youtube-ranking/most-superchatted-all-channels-in-japan-total")
    # driver.find_element(By.CSS_SELECTOR,'a[href="/en/youtube-ranking/most-superchatted-all-channels-in-japan-daily"]').click()
    # driver.find_element(By.LINK_TEXT, "Most Super Chatted").click()

    a = input("確認：更新したいライバーのlast1monthを削除してから実行\n実行する場合任意の文字列を入力:")
    if (a):
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
        update_list[i]["img"] = img

    # mainモデルのuseridを配列で出す
    main_userids = Main.objects.all().values_list("userid",flat=True)

    for i,liver in enumerate(update_list):
        # もし取ったデータの中に同一useridがいなかったら新規作成(更新モードの場合いたら更新)
        if(update_list[i]["userid"] in main_userids):
            # 更新するか否か分岐(同一useridのlast1monthが存在するかどうか)
            print(Main_Last1month.objects.filter(userid = update_list[i]["userid"]).count())
            if Main_Last1month.objects.filter(userid = update_list[i]["userid"]).count() == 0 :
                liver = Main.objects.get(userid = update_list[i]["userid"])
                # タグチェック分岐
                if (liver.tags.all()):
                    Main(
                        id = liver.id,
                        userid = update_list[i]["userid"],
                        img = update_list[i]["img"],
                        name = update_list[i]["name"],
                        discription = update_list[i]["discription"],
                        superchat_past = update_list[i]["superchat_past"],
                        LastUpdate_SuperchatPast = date.today() - timedelta(days = 1),
                        superchat_total = update_list[i]["superchat_past"],
                        subscriber_total = update_list[i]["subscriber_total"],
                        tagcheck = True,
                        # id込み合計11個 (+期間系6個)
                    ).save()
                    print(update_list[i]["name"]+"のレコードを更新(last1monthをこれから作成)　スパチャ額："+update_list[i]["superchat_past"])
                else:
                    Main(
                        id = liver.id,
                        userid = update_list[i]["userid"],
                        img = update_list[i]["img"],
                        name = update_list[i]["name"],
                        discription = update_list[i]["discription"],
                        superchat_past = update_list[i]["superchat_past"],
                        LastUpdate_SuperchatPast = date.today() - timedelta(days = 1),
                        superchat_total = update_list[i]["superchat_past"],
                        subscriber_total = update_list[i]["subscriber_total"],
                        tagcheck = False,
                        # id込み合計10個 (+tag +期間系6個)
                    ).save()
                    print(update_list[i]["name"]+"のレコードを更新(last1monthをこれから作成)　スパチャ額："+update_list[i]["superchat_past"])
            else:
                print(update_list[i]["name"]+"のlast1monthが存在したため更新処理はなし")
        # 同じuseridがなかった場合新規作成
        else:
            Main(
                userid = update_list[i]["userid"],
                img = update_list[i]["img"],
                name = update_list[i]["name"],
                discription = update_list[i]["discription"],
                superchat_past = update_list[i]["superchat_past"],
                LastUpdate_SuperchatPast = date.today() - timedelta(days = 1),
                superchat_total = update_list[i]["superchat_past"],
                subscriber_total = update_list[i]["subscriber_total"],
                tagcheck = False,
                # id抜き合計9個 (+tag +期間系6個)
            ).save()
            print(update_list[i]["name"]+"のレコードを作成  スパチャ額："+str(update_list[i]["superchat_past"]))

    # 登録したライバー達に、last1monthとtopsが無い場合のみそれらを作成
    main_livers = Main.objects.all().values("name","userid","superchat_past","subscriber_total")

    # まずLast1monthの作成
    # 含まれるidのリストを作成
    month_ids = Main_Last1month.objects.all().values_list("userid",flat=True)
    tops_ids = Main_Tops.objects.all().values_list("userid",flat=True)

    for prof in main_livers:
        # mainにいる配信者のlast1monthが存在しない場合に作成
        if not (prof["userid"] in month_ids):
            # iを始点0で32になるまで(つまり31まで)レコードを作成
            for i in range(31):
                Main_Last1month(
                    userid = prof["userid"],
                    name = prof["name"],
                    # 昨日から30日後まで(計31個)
                    # ↓本番用
                    day = date.today() + timedelta(days = i),
                    # ↓テスト用で昨日から作る　本番でやるとダブル加算になる
                    # day = date.today() + timedelta(days = i-1),
                    superchat_lastupdate = date.today(),
                    subscriber_lastupdate = date.today(),
                    # superchat_dailyはデフォルト
                    # subscriber_totalはデフォルト
                    # 意図したデフォルト込みid抜き合計5個
                ).save()
                print(date.today() + timedelta(days = i-1))
        # last1monthがあるライバーの場合, 個数をチェック
        else:
            count = 0
            for month_id in month_ids:
                if month_id == prof["userid"]:
                    count += 1
            if count != 31:
                print(prof["name"]+"のlast1monthが"+str(count)+"個あります")
        
        # 次にtopsを作成    
        if not (prof["userid"] in tops_ids):
            Main_Tops(
                name = prof["name"],
                userid = prof["userid"],
                order = 1,
                superchat_tops = prof["superchat_past"],
                subscriber_tops = prof["subscriber_total"],
            ).save()
    return redirect(to='ranking')


def test(request):
    userid = "UCl_gCybOJRIgOXw6Qb4qJzQ"
    # daylist = Main_Last1month.objects.filter(userid=userid).values_list("day",flat=True)
    # print(list(map(str, daylist)))
    # print(date(2020,1,1))
    # dailyslist = Main_Last1month.objects.filter(userid=userid).values_list("superchat_daily",flat=True)
    # dailys = list(map(str, dailyslist))
    # print(dailys)

    months = Main_Last1month.objects.filter(userid=userid).filter(day__lt=date.today()).order_by("day").reverse()
    print(months[1].name)
    for i in months:
        print(i.day)

    livers = Main.objects.all()
    # for liver in livers:
    #     months = Main_Last1month.objects.filter(userid = liver.userid)
    #     monthly = 0
    #     for month in months:
    #         monthly += month.superchat_daily
    #     Main(
    #         id = liver.id,
    #         userid = liver.userid,
    #         img = liver.img,
    #         name = liver.name,
    #         # 期間スパチャ,登録者は直後に更新するためデフォ
    #         superchat_past = liver.superchat_past,
    #         LastUpdate_SuperchatPast = liver.LastUpdate_SuperchatPast,
    #         subscriber_total = liver.subscriber_total,
    #         superchat_total = liver.superchat_past + monthly,
    #         discription = liver.discription,
    #         tagcheck = liver.tagcheck,
    #         # id込み10個 (期間系6個+タグ欠け)
    #     ).save()
    return redirect(to='')
    
def main_delete(request):
    # 一旦消す用
    # main_livers = Main.objects.all()
    # for liver in main_livers:
    #     liver.delete()
    
    month_livers = Main_Last1month.objects.all()
    for month in month_livers:
        month.delete()

    # top_livers = Main_Tops.objects.all()
    # for liver in top_livers:
    #     liver.delete()
    
    # b = Main_Last1month.objects.filter(userid = "UCkIimWZ9gBJRamKF0rmPU8w")
    # b.delete()
    return redirect(to='/admin')

def youtube(request,term,order,page):
    if (request.method == 'POST'):
        if request.POST.get('pass') == 'opayouliverank':
            data = Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).reverse()[:20]
            chats = list(Main.objects.prefetch_related("tags").all().order_by(order+"_"+term).reverse().values_list(order+"_"+term,flat=True))[:20]
            livers = []

            for i,liver in enumerate(data):
                livers.append({
                    "userid":liver.userid,
                    "img":"",
                    "name":liver.name,
                    "superchat":chats[i],
                })
            params = {
                "data":data,
            }
        else:
            {"title":"YouTube画像作成",
            "to":"youtube"
            }
            return render(request,"LiveRank/bunki.html",params)

def favicon(request):
    params = {}
    return render(request,"LiveRank/favicon.html",params)



#########################
#                       #
# これ以降は授業用ページ    #
#                       #
#########################

def ubi_ai(request):
    params = {}
    return render(request,"LiveRank/ubi_ai.html",params)

def ubi_set(request):
    if (request.method == 'POST'):
        params = {}
        machine = request.POST.get('machine_choice')
        return redirect(to='/ubiquitous_information/'+ machine)
    params = {}
    return render(request,"LiveRank/ubi_set.html",params)

def ubi_info(request,machine):
    if request.method == "GET":
        if machine == "pc":
            machine_jap = "pc"
        elif machine == "video":
            machine_jap = "ビデオカメラ"
        if machine == "shoulder_left":
            machine_jap = "左肩"
        elif machine == "shoulder_right":
            machine_jap = "右肩"
        elif machine == "leg_left":
            machine_jap = "左脚"
        elif machine == "leg_right":
            machine_jap = "右脚"
        users = Ubi_user.objects.all()
        params={
            "machine":machine,
            "machine_jap":machine_jap,
            "users":users,
        }
        return render(request,"LiveRank/ubi_info.html",params)
    elif request.method == 'POST':
        if machine == "pc":
            name = request.POST.get('name')
            time = request.POST.get('start_time')
            hour = int(time[:2])
            minute = int(time[-2:])
            Ubi_user(
                name = name,
                start_time = datetime(2023,7,21,hour,minute,0)
            ).save()
            params = {
            }
            return redirect(to='/ubiquitous_pc/'+name)
        elif machine == "video":
            name = request.POST.get('name')
            return redirect(to='/ubiquitous_video/' + name)
        else:
            name = request.POST.get('name')
            return redirect(to='/ubiquitous_measure/' + machine + "/" + name)


def ubi_pc(request,name):
    user = Ubi_user.objects.filter(name = name)[0]
    # try:
    # if len(str(user.shoulder_left)) >= 300:
    #     user_text_ = "データ：\n左肩：\nx軸 y軸 z軸\n" +  user.shoulder_left[:300] + "\nこれを元にアドバイスください\n"
    # else:
    #     user_text_ = "データ：\n左肩：\nx軸 y軸 z軸\n" +  user.shoulder_left + "これを元にアドバイスください\n"
    # except:
    user_text_ = ""
    try:
        video = Ubi_video.objects.filter(name = user.name)[0]
    except:
        video = Ubi_video.objects.filter(id=12)[0]
    video_path = video.video
    params = {
        "video_path":video_path,
        "user":user,
        "user_text":user_text_
    }
    return render(request,"LiveRank/ubi_pc.html",params)

def ubi_mea(request,part,name):
    if request.method == "GET":
        user = Ubi_user.objects.filter(name = name)[0]
        if part == "shoulder_left":
            part_jap = "左肩"
        elif part == "shoulder_right":
            part_jap = "左肩"
        elif part == "leg_right":
            part_jap = "左肩"
        elif part == "leg_left":
            part_jap = "左肩"
        else:
            part_jap = "加速度"
        params = {
            "part":part,
            "part_jap":part_jap,
            "user":user
        }
        return render(request,"LiveRank/ubi_mea.html",params)
    elif request.method == "POST":
        user = Ubi_user.objects.filter(name = name)[0]
        user.shoulder_left = request.POST.get('text_acc')
        user.save()
        return redirect(to="/ubiquitous_setting")

def ubi_video(request,name):
    if request.method == "GET":
        video_form = VideoForm()
        user = Ubi_user.objects.filter(name = name)[0]
        params = { 
            "video_form": video_form,
            "user":user
            }
        return render(request, "LiveRank/ubi_video.html", params)
    elif request.method == 'POST':
        params = {}
        user = Ubi_user.objects.filter(name = name)[0]
        video_form = VideoForm(request.POST, request.FILES)
        video = video_form.save()
        video.name = name
        video.save()
        return redirect(to='/ubiquitous_pc/'+user.name)
    else:
        params = {}
        return render(request,"LiveRank/ubi_set.html",params)

#以下GPT
def index(request):
    """
    チャット画面
    """
    # 応答結果
    chat_results = ""
    if request.method == "POST":
        # ChatGPTボタン押下時
        form = ChatForm(request.POST)
        if form.is_valid():
            sentence = form.cleaned_data['sentence']
            openai.api_key = OPENAI_API_KEY

            # 新規チャットセッションを開始または既存のチャットセッションを取得
            session_id = request.session.get('chat_session_id')
            if session_id is None:
                chat_session = ChatSession.objects.create()
                request.session['chat_session_id'] = chat_session.id
            else:
                chat_session = ChatSession.objects.filter(id=session_id)[0]

            # ユーザのメッセージを保存
            ChatMessage.objects.create(session=chat_session, content=sentence, by_user=True)

            # ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {   "role": "system", "content": """
===
＃役割：

ユーザーは一生懸命にゴルフの上達を目指しています。上達するための一手段として、自分の左肩に加速度計を装着し、スイング時の加速度データを収集しています。


＃目標：

ユーザーの目指す目標は、収集した加速度データを分析し、そのデータからスイングの問題点や改善すべきポイントを見つけ出すことです。その結果をもとに具体的で効果的なアドバイスを提供します。

初めに、ユーザーの左肩の加速度データの平均値を教えていただくことで、分析を始め、アドバイスだけをユーザーにあげてください。

分析が終わったら、ユーザーに他のデータがないかを聞き、次の分析ができるように準備をしてください。
                     
＃注意：
                     
サーバーが終わりと言ったらもうこれ以上データの強要はせず、このセッションを終わりにすること。

===
                        """},
                    {"role": "user", "content": sentence},
                ],
            )
            chat_results_raw = response["choices"][0]["message"]["content"]

            # ChatGPTの応答を保存
            ChatMessage.objects.create(session=chat_session, content=chat_results_raw, by_user=False)

            chat_results_cleaned = re.sub(r'(\d+\.)', r'\1\n', chat_results_raw)
            chat_results_items = [item.rstrip('。').strip() for item in chat_results_cleaned.split('\n') if item.strip()]
            chat_results_items = [re.sub(r'\.$', '', item) for item in chat_results_items]

            chat_results = '<table>' + ''.join(f'<tr><td>{item.split(".")[0]}</td><td>{item.split(".")[1].strip() if "." in item else ""}</td></tr>' for item in chat_results_items) + '</table>'
    else:
        form = ChatForm()

    sessions = ChatSession.objects.all()

    context = {
        'form': form,
        'chat_results': chat_results,
        'sessions': sessions
    }
    return render(request, 'index.html', context)


#新しいセッションを作った時用のほとんど index 関数と同じ働きをしているクラス
class ChatView(View):
    def get(self, request):
        form = ChatForm()
        sessions = ChatSession.objects.all()
        context = {
            'form': form,
            'sessions': sessions,
            'new_session': request.session.get('new_session', False)
        }
        return render(request, 'index.html', context)

    def post(self, request):
        form = ChatForm(request.POST)
        if form.is_valid():
            sentence = form.cleaned_data['sentence']
            openai.api_key = OPENAI_API_KEY

            session_id = request.session.get('chat_session_id')
            if session_id is None:
                chat_session = ChatSession.objects.create()
                request.session['chat_session_id'] = chat_session.id
            else:
                chat_session = ChatSession.objects.filter(id=session_id)[0]

            ChatMessage.objects.create(session=chat_session, content=sentence, by_user=True)

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """
===
＃役割：
ユーザーは一生懸命にゴルフの上達を目指しています。上達するための一手段として、自分の左肩、右肩、右足、左足の4つの部位に加速度計を装着し、スイング時の加速度データを収集しています。

＃目標：

ユーザーの目指す目標は、収集した加速度データを分析し、そのデータからスイングの問題点や改善すべきポイントを見つけ出すことです。その結果をもとに具体的で効果的なアドバイスを提供します。

初めに、ユーザーの左肩の加速度データの平均値を教えていただくことで、分析を始め、アドバイスだけをユーザーにあげてください。

分析が終わったら、ユーザーに他のデータがないかを聞き、次の分析ができるように準備をしてください。
                     
＃注意：
                     
サーバーが終わりと言ったらもうこれ以上データの強要はせず、このセッションを終わりにすること。
===
                        """},
                    {"role": "user", "content": sentence},
                ],
            )

            chat_results = response["choices"][0]["message"]["content"]

            # ChatGPTの応答を保存
            ChatMessage.objects.create(session=chat_session, content=chat_results, by_user=False)

            form = ChatForm()

            sessions = ChatSession.objects.all()

            context = {
                'form': form,
                'chat_results': chat_results,
                'sessions': sessions
            }
            return render(request, 'index', context)


def new_session(request):
    request.session.pop('chat_session_id', None)
    request.session['new_session'] = True
    return redirect('index')


def start_new(request):
    """
    Start a new chat session.
    """
    # Create a new ChatSession object and save it to the database.
    chat_session = ChatSession.objects.create()

    # Store the new session's ID in the user's session.
    request.session['chat_session_id'] = chat_session.id

    # Redirect the user to the index page.
    return redirect('index')

def continue_session(request, session_id):
    """
    Continue an existing chat session.
    """
    # Get the ChatSession object with the given ID.
    chat_session = ChatSession.objects.get(id=session_id)

    # Store the session's ID in the user's session.
    request.session['chat_session_id'] = chat_session.id

    # Redirect the user to the index page.
    return redirect('index')

#セッションを削除する時用の csrf トークン取得関数
@csrf_exempt
def delete_session(request, session_id):
    if request.method == 'DELETE':
        try:
            session = ChatSession.objects.get(id=session_id)
            session.delete()
            return JsonResponse({'status': 'success'})
        except ChatSession.DoesNotExist:
            return JsonResponse({'status': 'Session not found'}, status=404)