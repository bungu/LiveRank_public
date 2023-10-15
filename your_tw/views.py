if not __name__ =="__main__":
    from django.shortcuts import render
    from django.shortcuts import redirect
    from . import api
    import json
    from server import calculate_category
    import server.generate_rand as s
    import server.create_ogp as ogp
    import os

# Create your views here.
def index(request):

    state = s.generate_state()
    code_verifier = s.generate_code_verifier()
    request.session["state"]=state
    request.session["code_verifier"]=code_verifier
    # request.session.set_expiry(60) # session を60秒に設定。defaultは2週間
    # djangoでは、ブラウザのcookieにsessionIDを発行し、それと紐づけて
    # デフォルトではサーバーのDBに保存される。
    # request.session.set_expiry(0) # 0の場合、ブラウザを閉じた時にクッキーを破棄する。
    # settings.py のSESSION_COOKIE_AGEに記載

    challenge_method="S256"
    code_challenge=s.get_urlsafe_code_challenge(code_verifier)

    SCOPE="tweet.read%20users.read"
    
    twitter_auth_uri=f"https://twitter.com/i/oauth2/authorize"
    twitter_auth_uri+=f"?response_type=code"
    twitter_auth_uri+=f"&client_id={os.environ['CLIENT_ID']}"
    twitter_auth_uri+=f"&redirect_uri={os.environ['REDIRECT_URI']}"
    twitter_auth_uri+=f"&scope={SCOPE}"
    twitter_auth_uri+=f"&state={state}"
    twitter_auth_uri+=f"&code_challenge={code_challenge}"
    twitter_auth_uri+=f"&code_challenge_method={challenge_method}"
    params={
        "twitter_auth_uri":twitter_auth_uri
    }
    return render(request,"firstpage/index.html",params)

def api_and_category(request):
    # urlからコードを取得
    if "code" not in request.GET or "state" not in request.GET:
        # TODO エラー処理
        print(f'code:{"code" not in request.GET} , state:{"state" not in request.GET}')
        # request.session.clear() # request.session.set_expiry(0) なので不要だが。。
        # raise Exception("invalid body") 
        return redirect(to="/tweet_diagnose")
    authorization_code = request.GET.get("code")
    state=request.GET.get("state")
    if state!=request.session.get("state"):
        # TODO エラー処理
        print("state is not same")
        # request.session.clear() # request.session.set_expiry(0) なので不要だが。。
        # raise Exception("state is invalid.")
        return redirect(to="/tweet_diagnose")
    code_verifier=request.session.get("code_verifier")
    # request.session.clear() # request.session.set_expiry(0) なので不要だが。。
    
    # コードから諸々の処理を経てツイート(文字列配列)を取得
    tweets = api.take_tweets(authorization_code,code_verifier)


    # 文字列配列からカテゴリを計算
    categories = calculate_category.get_category_name(tweets,True)

    # カテゴリに合わせたurlに遷移
    if categories == None:
        return redirect(to='/tweet_diagnose/show_results/Zatta/Zatta')
    if len(categories) == 1:
        return redirect(to='/tweet_diagnose/show_results' + '/' + categories[0]  + '/Kyukyokuno')
    if len(categories) == 2:
        return redirect(to='/tweet_diagnose/show_results' + '/' +categories[0] + '/' + categories[1])

def create_params(type1,type2):
    #仮で設定したもの、type1が一番多い特徴量、type2が二番目に多い特徴量
    # type1 = "G"
    # type2 = "I"

    type_dic_Ad ={
        "MazimeRikei":"勉強好きな",
        "Yakyuzuki":"野球好きな",
        "Ishikitakaikei":"意識高い",
        "NetGameHaizin":"ネトゲ好きな",
        "AnimeOtaku":"アニメ好きな",
        "Shukatsu":"就活中の",
        "Kyukyokuno":"究極の",
        "Zatta":"特徴なき" # ZattaはZatta Zattaなので前半は無し
    }

    type_dic_Noun ={
        "MazimeRikei":"理系オタク",
        "Yakyuzuki":"野球バカ",
        "Ishikitakaikei":"意識高い系",
        "NetGameHaizin":"ゲーム廃人",
        "AnimeOtaku":"二次元オタク",
        "Shukatsu":"就活生",
        "Zatta":"普通人"
    }

    type_dic_en ={
        "MazimeRikei":"serious idiot",
        "Yakyuzuki":"baseball freak",
        "Ishikitakaikei":"buffle idiot",
        "NetGameHaizin":"game lover",
        "AnimeOtaku":"anime lover",
        "Shukatsu":"job hunter",
        "Zatta":"unclassifiable"
    }

    images ={
        "MazimeRikei":"img/mazime.png",
        "Yakyuzuki":"img/yakyu.png",
        "Ishikitakaikei":"img/isiki.png",
        "NetGameHaizin":"img/game.png",
        "AnimeOtaku":"img/anime.png",
        "Shukatsu":"img/syukatu.png",
        "Zatta":"img/zatta.png"
    }

    type_dic_message = {
        "MazimeRikei":"あなたのツイートは全体的につまんないですね。",
        "Yakyuzuki":"あなたの人生は、野球によって浸食されています。",
        "Ishikitakaikei":"正直あまり、好きじゃないです。",
        "NetGameHaizin":"課金しすぎてませんか？",
        "AnimeOtaku":"現実きちんとみれてますか?",
        "Shukatsu":"まあ、頑張ってください。",
        "Zatta":"ちょっとぐらい尖ってみてもいいんじゃない？"
    }
    ogp_image_file=f"img/ogp/{type1}{type2}.png"
    params = {
        "type_dic_Ad":type_dic_Ad[type2],
        "type_dic_Noun":type_dic_Noun[type1],
        "type_dic_en":type_dic_en[type1],
        "img":images[type1],
        "type_dic_message":type_dic_message[type1],
        "ogp_img":ogp_image_file
    }
    return params

#結果のページ（result.htmlをひらくための関数）
def show_results(request,type1,type2):
    params=create_params(type1, type2)
    # 画像生成の際はDBを使う必要があり、今回は動的に生成しない。
    # ogp.create_ogp_image(
    #     ogp_image_file,
    #     params["img"],
    #     f'{params["type_dic_Ad"]}{params["type_dic_Noun"]}', 
    #     params["type_dic_en"],
    #     params["type_dic_message"]
    # )
    return render(request,"resultpage/result.html",params)

def information(request):
    return render(request,"information/information.html")

if __name__ =="__main__": # 本番サーバーでは動かさない。OGP画像生成用
    import sys
    from os.path import dirname, abspath
    sys.path.append(dirname(dirname(abspath(__file__))))
    import server.create_ogp as ogp
    type1s=["MazimeRikei","Yakyuzuki","Ishikitakaikei","NetGameHaizin","AnimeOtaku","Shukatsu"]
    type2s=["MazimeRikei","Yakyuzuki","Ishikitakaikei","NetGameHaizin","AnimeOtaku","Shukatsu","Kyukyokuno"]
    for type1 in type1s:
        for type2 in type2s:
            params=create_params(type1, type2)
            ogp.create_ogp_image(
                params["ogp_img"],
                params["img"],
                f'{params["type_dic_Ad"]}{params["type_dic_Noun"]}', 
                params["type_dic_en"],
                params["type_dic_message"]
                )
    type1="Zatta"
    type2="Zatta"
    params=create_params(type1, type2)
    ogp.create_ogp_image(
        params["ogp_img"],
        params["img"],
        f'{params["type_dic_Ad"]}{params["type_dic_Noun"]}', 
        params["type_dic_en"],
        params["type_dic_message"]
        )
    

