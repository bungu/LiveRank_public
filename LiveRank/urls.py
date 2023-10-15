from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

# app_name = "chat"

# このurlにアクセスが来た時にどの関数を呼び出すか,という指示が出されている
urlpatterns = [
    path('',views.redirect_to_top,name='redirect_to_top'),
    path('ranking',views.ranking_top,name='ranking_top'),
    path('ranking/<order>/<term>/<int:page>',views.ranking,name='ranking'),
    path('ranking/<order>/<term>/<tag>/<int:page>',views.tag_ranking,name='tag_ranking'),
    path('ranking/<tag>',views.tag_top,name='tag_top'),
    # path('orderform/<term>',views.orderform,name='orderform'),
    # path('orderform/<term>/<tag>',views.orderform_tag,name='orderform'),
    path('find',views.find,name='find'),
    path('find_ranking/<order>/<term>/<find>/<int:page>',views.find_ranking,name='find_ranking'),

    path('filter/<order>/<term>',views.filter,name='filter'),

    path('liver/<userid>',views.liver,name='liver'), # numの値を入力されたもので定義してviewsの処理にも適用している
    path('policy',views.policy,name='policy'),
    path('statistic_policy',views.statistic_policy,name='statistic_policy'),
    
    # path('register',views.register,name='register'),
    path('add',views.add,name='add'),
    path('no1',views.no1,name='no1'),
    path('no2_4',views.no2_4,name='no2_4'),

    # path('test',views.test,name='test'), 
    # path('delete',views.main_delete,name='delete'),

    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    # path('sitemap.xml', TemplateView.as_view(template_name='sitemap.xml', content_type='text/plain')),
    # path('sitemap.xml', TemplateView.as_view(template_name='sitemap.xml', content_type='text/plain')),
    path('ads.txt', TemplateView.as_view(template_name='ads.txt', content_type='text/plain')),
    path('favicon.ico', views.favicon,name='favicon'),

    path('ubiquitous_ai', views.ubi_ai,name='ubi_ai'),
    path('ubiquitous_setting', views.ubi_set,name='ubi_set'),
    path('ubiquitous_information/<machine>', views.ubi_info,name='ubi_info'),
    path('ubiquitous_pc/<name>', views.ubi_pc,name='ubi_pc'),
    path('ubiquitous_video/<name>', views.ubi_video,name='ubi_video'),
    path('ubiquitous_measure/<part>/<name>', views.ubi_mea,name='ubi_mea'),

    # 以下gpt
    path('index', views.index, name="index"),
    path('start_new/', views.start_new, name='start_new'),
    path('continue/<int:session_id>/', views.continue_session, name='continue_session'),
    path('delete_session/<int:session_id>/', views.delete_session, name = 'delete_session'), 
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 動画出す時のやつ(よくわからん)