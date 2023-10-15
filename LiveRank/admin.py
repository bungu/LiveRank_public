from django.contrib import admin
from .models import Master,Tags,Main,Main_Last1month,Main_Tops,Ubi_user,Ubi_video
from .models import Master,Main,Main_Last1month,Main_Tops

# Register your models here.

class monthAdmin(admin.ModelAdmin):
    search_fields = ('name','userid','day')
    list_filter = ('superchat_lastupdate','day','superchat_daily')
    list_per_page = 500
    list_display = ("name","day","subscriber_total","subscriber_lastupdate","superchat_daily","superchat_lastupdate")

    ordering = ('userid',)

class mainAdmin(admin.ModelAdmin):
    search_fields = ('name','userid')
    list_filter = ('tagcheck','LastUpdate_SuperchatPast')
    list_display = ("name","tagcheck","LastUpdate_SuperchatPast")

class topsAdmin(admin.ModelAdmin):
    search_fields = ('name','userid','day')
    list_filter = ('userid',)
    list_display = ("name","order")

class tagsAdmin(admin.ModelAdmin):
    list_display = ("priority","tag_name","id")
    ordering = ('priority',)

class masterAdmin(admin.ModelAdmin):
    list_display = ("last_update","pv_count","id")

class Ubi_VideoAdmin(admin.ModelAdmin):
    list_display = ("id","video",)

class Ubi_UserAdmin(admin.ModelAdmin):
    list_display = ("id","name","start_time","shoulder_left")


admin.site.register(Master,masterAdmin)
admin.site.register(Main,mainAdmin)
admin.site.register(Main_Last1month,monthAdmin)
admin.site.register(Main_Tops,topsAdmin)
admin.site.register(Tags,tagsAdmin)
admin.site.register(Ubi_video,Ubi_VideoAdmin)
admin.site.register(Ubi_user,Ubi_UserAdmin)
