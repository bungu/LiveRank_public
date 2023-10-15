
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
    base = "https://www.liverank.jp"
    orders = ["/superchat","/subscriber"]
    terms = ["/total","/weekly","/daily"]
    tags = ["/%E5%A5%B3%E6%80%A7",
            "/%E7%94%B7%E6%80%A7",
            "/Vtuber",
            "/Global",
            "/%E4%B8%80%E8%88%AC",
            "/%E9%9F%B3%E6%A5%BD",
            "/%E6%89%80%E5%B1%9E%EF%BC%9A%E3%81%AB%E3%81%98%E3%81%95%E3%82%93%E3%81%98",
            "/%E6%89%80%E5%B1%9E%EF%BC%9A%E3%83%9B%E3%83%AD%E3%83%A9%E3%82%A4%E3%83%96",
            "/%E5%80%8B%E4%BA%BA%E5%8B%A2",
            "/%E6%89%80%E5%B1%9E%EF%BC%9A%E3%81%9D%E3%81%AE%E4%BB%96",
            "/Vtuber%2B%E5%80%8B%E4%BA%BA%E5%8B%A2",
            "/Vtuber%2B%E7%94%B7%E6%80%A7",
            "/Vtuber%2B%E5%A5%B3%E6%80%A7",
            "/Vtuber%2BGlobal",
            "/%E6%89%80%E5%B1%9E%EF%BC%9A%E3%81%AB%E3%81%98%E3%81%95%E3%82%93%E3%81%98%2B%E7%94%B7%E6%80%A7",
            "/%E6%89%80%E5%B1%9E%EF%BC%9A%E3%81%AB%E3%81%98%E3%81%95%E3%82%93%E3%81%98%2B%E5%A5%B3%E6%80%A7",
            ]
    urls = [base+"/ranking"]
    # 女性,男性,Vtuber,一般,音楽,所属：にじさんじ,所属：ホロライブ,個人勢,所属：その他,Vtuber+個人勢,Vtuber+男性,Vtuber+女性,Vtuber+Global,所属：にじさんじ+男性,所属：にじさんじ+女性

    # メインページ
    for order in orders:
        for term in terms:
            a = base + "/ranking" + order + term + "/1"
            urls.append(a)

    for order in orders:
        for term in terms:
            for tag in tags:
                a = base + "/ranking" + order + term + tag + "/1"
                urls.append(a)
    
    tag_singles = tags[:9]
    for tag in tag_singles:
        a = base + "/ranking" + tag
        urls.append(a)
    
    livers = Main.objects.all()
    print("ライバー数:"+str(livers.count()))
    for liver in livers:
        a = base + "/liver/" + liver.userid
        urls.append(a)

    # for url in urls:
    #     print(url)
    
    last_update = date.today()
    last_update = datetime.strftime(last_update,'%Y-%m-%dT00:30:00+00:00')

    hontai = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'

    for url in urls:
        hontai += " <url>\n  <loc>"+url+"</loc>\n  <lastmod>"+ last_update +"</lastmod>\n </url>\n"
        # print(" <loc>"+url+"</loc>")
        # print(" <lastmod>"+ last_update +"</lastmod>")
        # print("</url>")
    
    hontai += "\n\n</urlset>"

    print(last_update)
    print(hontai[:200])

    # sitemap = open("LiveRank/static/sitemap.xml",mode = 'w',encoding='UTF-8')

    # sitemap.write(hontai)

    # sitemap.close

    sitemap = open("LiveRank/static/LiveRank/sitemap.xml",mode = 'w',encoding='UTF-8')

    sitemap.write(hontai)

    sitemap.close