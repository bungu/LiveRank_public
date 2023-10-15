from django import forms
from .models import Main,Ubi_video


class VideoForm(forms.ModelForm):
    class Meta:
        model = Ubi_video
        fields = ("video",)
        # フィールドについては全件指定であれば以下の書き方でも可
        # fields = '__all__'
        labels = {
        "video": "動画",
        }

# 多分今使ってない
class OrderForm(forms.Form):
    data = [
        ('subscriber','登録者順'),
        ('superchat','スパチャ順')
    ]
    # 後ほどchoicesに入れるやつ
    order = forms.ChoiceField(
        choices = data,
        widget=forms.widgets.RadioSelect(),
        label = 'order',
    )

class FindForm(forms.Form):
    find = forms.CharField(
        label = 'find',
        required = False,
        widget = forms.widgets.TextInput(),
    )

# gpt用
class ChatForm(forms.Form):
    sentence = forms.CharField(label='ゴルフスイングアドバイザー', widget=forms.Textarea(), required=True)