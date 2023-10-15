from django.contrib import admin
from . import views
from django.urls import path,include

urlpatterns = [
    path("",views.index),
    path("callback/",views.api_and_category), # クエリパラメーターはパスなしの判定
    path("information/",views.information),
    path("show_results/<type1>/<type2>",views.show_results,name="show_results")
]