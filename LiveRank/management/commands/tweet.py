
from django.core.management.base import BaseCommand

from time import sleep
from datetime import date, timedelta, datetime
import random
import math

from socket import gethostname

from LiveRank.models import Master,Tags,Main,Main_Last1month,Main_Tops
from LiveRank.forms import OrderForm,FindForm

from apiclient.discovery import build

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import chromedriver_binary
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

import urllib.parse
import pyperclip

from bs4 import BeautifulSoup


class Command(BaseCommand):
    help = "updateコマンド"

    def handle(self, *args, **options):
        # なんかここに書いたものが実行される
        Make()

def Make():
    text = "こんにちは"
    text = urllib.parse.quote(text)
    
    url = "https://twitter.com/intent/tweet?text="+text

    pyperclip.copy(url)
    print("ツイートurlをコピーしました")


