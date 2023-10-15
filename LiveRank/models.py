from django.db import models
from django.utils import timezone
from datetime import date,datetime
from django.core.validators import FileExtensionValidator

# Create your models here.

class Master(models.Model):
    last_update = models.DateField(default = date(2020,1,1))
    pv_count = models.IntegerField(default = 0)

class Tags(models.Model):
    # 基本情報
    priority = models.IntegerField()
    #タグ
    tag_name = models.CharField(max_length=20)

    def __str__(self):
        return self.tag_name

    # Mainモデルとの対応(こちらにはいらない)
    # livers = models.ManyToManyField(Main)

class Main(models.Model):
    # 基本情報3個
    userid = models.CharField(max_length=50)
    img = models.URLField(max_length=200)
    name = models.CharField(max_length=100)

    # スパチャ関連6個
    superchat_total = models.IntegerField(default=0)
    superchat_daily = models.IntegerField(blank=True,default=0)
    superchat_weekly = models.IntegerField(blank=True,default=0)
    superchat_monthly = models.IntegerField(blank=True,default=0)

    superchat_past = models.IntegerField(blank=True,default=0)
    LastUpdate_SuperchatPast = models.DateTimeField(default=datetime(2020,1,1))

    # 登録者関連4個
    subscriber_total = models.IntegerField()
    subscriber_daily = models.IntegerField(blank=True,default=0)
    subscriber_weekly = models.IntegerField(blank=True,default=0)
    subscriber_monthly = models.IntegerField(blank=True,default=0)

    # 概要
    discription = models.TextField(max_length=3000,blank=True,default="システムによる記載待ち")

    # タグモデルとの対応2個
    tags = models.ManyToManyField(Tags)
    tagcheck = models.BooleanField(default=False)

    # 合計id,tags抜き15個(tagsは記載必要なし)

    def __str__(self):
        return self.name

class Main_Last1month(models.Model):
    # 基本情報
    userid = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    day = models.DateField()

    # スパチャ関連
    superchat_daily = models.IntegerField(blank=True,default=0)

    # 登録者関連
    subscriber_total = models.IntegerField(blank=True,default=0)

    # 更新日
    superchat_lastupdate = models.DateField(default= date(2020,1,1))

    subscriber_lastupdate = models.DateField(default= date(2020,1,1))

    # id抜き合計7個 id込み合計8個

class Main_Tops(models.Model):
    # 基本情報
    userid = models.CharField(max_length=50)
    order = models.IntegerField()
    name = models.CharField(max_length=100,null=True)

    # スパチャ関連
    superchat_tops = models.IntegerField(blank=True,default=0)

    # 登録者関連
    subscriber_tops = models.IntegerField(blank=True,default=0)

class YT_record(models.Model):
    # 基本情報
    userid = models.CharField(max_length=50)
    img = models.URLField(max_length=200)
    name = models.CharField(max_length=100)
    # ラベル
    label = models.CharField(max_length=20)
    # 日付とスパチャと一応登録者数
    day = models.DateField()
    superchat_record = models.IntegerField()
    subscriber_record = models.IntegerField()

class Ubi_video(models.Model):
    name = models.CharField(max_length=100,default="Guest")
    video = models.FileField(
        upload_to= '%Y/%m/%d/%H/%M',
        # verbose_name='添付ファイル',
        # validators=[FileExtensionValidator([".mpg",".mpeg", ".mp4", ".webm", ".mov", ".avi"])],
        # なんか動かんかった
        # validators=[FileExtensionValidator([".mov",])]
    )

class Ubi_user(models.Model):
    name =  models.CharField(max_length=50)

    start_time = models.DateTimeField(default = date(2020,1,1))
    shoulder_right = models.TextField(default="")
    shoulder_left = models.TextField(default="")
    leg_right = models.TextField(default="")
    leg_left = models.TextField(default="")

# gpt用
class ChatSession(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    by_user = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)