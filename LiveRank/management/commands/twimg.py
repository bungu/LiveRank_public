from django.core.management.base import BaseCommand

from LiveRank.models import Master,Main,Tags

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import chromedriver_binary
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup

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

class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        if "tsudaharujinoMacBook-Pro-2" in hostname:
            Take()
        else:
            print("管理者のPCではないため実行を中断")

def Take():
    # 開く
    options = webdriver.ChromeOptions()
    # options.add_argument('headless')
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    driver = webdriver.Chrome(ChromeDriverManager().install(),options = options)

    driver.get("http://127.0.0.1:8000/no2_4")
    driver.set_window_size(500,1000)

    term = "daily"

    if term == "daily":
        term_jap = "日間"
    elif term == "weekly":
        term_jap = "週間"
    elif term == "monthly":
        term_jap = "月間"

    hololive = False

    driver.find_element(By.CLASS_NAME,'input').send_keys("")
    driver.find_element(By.NAME,'order').send_keys("superchat")
    driver.find_element(By.NAME,'term').send_keys(term)
    if hololive == True:
        driver.find_element(By.NAME,'tag').send_keys("hololive")
    driver.find_element(By.CLASS_NAME,'submit').click()
    sleep(0.5)


    pyperclip.copy("</br>")
    print("クリップボードに</br>をコピーしました")
    choice = input("保存しない場合何か入力 保存する場合Enter:")
    if choice == "":
        driver.find_element(By.TAG_NAME,'body').send_keys(Keys.COMMAND,"0")
        h = driver.find_element(By.TAG_NAME,"body").size["height"]*2
        w = driver.find_element(By.TAG_NAME,"body").size["width"]*2
        driver.save_screenshot('./0_tweet_img/img2_4.png')

        img = cv2.imread('./0_tweet_img/img2_4.png')
        # 指定サイズで切り取り
        img_ = img[0 : h, 0 : w]
        cv2.imwrite("./0_tweet_img/img2_4.png", img_)

    # driver.get("https://www.liverank.jp/no1")
    driver.get("http://127.0.0.1:8000/no1")

    driver.set_window_size(600,1000)
    driver.find_element(By.NAME,'pass').send_keys("")
    driver.find_element(By.NAME,'order').send_keys("superchat")
    driver.find_element(By.NAME,'term').send_keys(term)
    if hololive == True:
        driver.find_element(By.NAME,'tag').send_keys("hololive")
    driver.find_element(By.CLASS_NAME,'submit').click()
    sleep(0.5)

    choice = input("保存しない場合何か入力 保存する場合Enter:")
    if choice == "":
        driver.find_element(By.TAG_NAME,'body').send_keys(Keys.COMMAND,"0")
        h = driver.find_element(By.CLASS_NAME,"body").size["height"]*2
        w = driver.find_element(By.CLASS_NAME,"body").size["width"]*2
        driver.save_screenshot('./0_tweet_img/img1.png')

        img = cv2.imread('./0_tweet_img/img1.png')

        img_ = img[0 : h, 0 : w]
        cv2.imwrite("./0_tweet_img/img1.png", img_)

    driver.close()
    if 0 < datetime.now().hour < 8:
        kinou = date.today() - timedelta(days = 2)
    else:
        kinou = date.today() - timedelta(days = 1)
    kinou = datetime.strftime(kinou,'%Y/%m/%d')
    text = urllib.parse.quote("国内YouTube配信者 " + term_jap + "スパチャ額TOP4("+ kinou + ")") +"%0A%0A"

    global_tag = Tags.objects.get(tag_name = "Global")
    top4 = Main.objects.all().order_by("superchat_"+term).exclude(tags = global_tag).reverse()[:4]

    if hololive == True:
        text = urllib.parse.quote("ホロライブ " + term_jap + "スパチャ額TOP4("+ kinou + ")") +"%0A%0A"
        tag_object = Tags.objects.get(tag_name = "所属：ホロライブ")
        top4 = Main.objects.all().order_by("superchat_"+term).filter(tags = tag_object).reverse()[:4]

    n = 1
    for liver in top4:
        text += urllib.parse.quote(str(n) + ". " + liver.name) 
        if len(liver.name) >= 28:
            text += "注意!28文字以上"
        text += "%0A"
        n += 1
    # text += urllib.parse.quote(str(n) + "." + liver.name + " " + str("{:,}".format(liver.superchat_daily))+"円") + "%0A"

    # text = urllib.parse.quote(text)

    text = text[:len(text) - 3]
    
    url = "https://twitter.com/intent/tweet?text="+text

    pyperclip.copy(url)
    print("ツイートurlをコピーしました")




