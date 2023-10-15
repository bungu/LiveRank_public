import csv
import math
import glob
import re
import os

def get_category_name(tweets,debug=False): # ルール でかい方から取る。
    """
    client側から呼び出す

    input
    tweets ... tweetのstring配列
    debug ... Trueにするとdebug出力

    output
    None ... 分類不可能
    ["AnimeOtaku"] ... 一つまたは二つのカテゴリ配列。
    """
    tweets=pre_processing(tweets)
    tweet="".join(tweets)
    scores_dict=__calculate_category_scores(tweet)
    sum_score=sum([score[1] for score in scores_dict.items()])
    scores=sorted(scores_dict.items(), key=lambda x:-x[1]) # 大きい順
    if debug:
        print(scores)
    first=40 # 圧倒的な時の1つ目カテゴリの閾値
    second=40 # ふたつのカテゴリがが選ばれる時の二つ目のカテゴリまでの閾値
    if sum_score==0:
        return None # カテゴリなし
    if len(scores)==0:
        raise Exception("辞書ファイルがおかしい可能性があります")
        # return None
    if len(scores)==1 or scores[0][1]/sum_score>=first/100:
        return [scores[0][0]]
    if (scores[0][1]+scores[1][1])/sum_score>=first/100:
        return [scores[0][0],scores[1][0]]
    return None # カテゴリなし
import re
def pre_processing(texts): 
  """
  in
  texts:text配列

  out
  texts:text配列
  """
  # texts,tmps=[],texts
  tmps=texts
  texts=[]
  for text in tmps:
    # print(text,text==float("nan"),type(text),type(text)==float)
    if type(text)==float: # 欠損値
        texts.append("")
        continue
    # text = re.sub('@.+ ', '', text) # メンションの削除
    text = re.sub('http.+', '', text) # urlの削除 # TODO 展開の可能性
    text = re.sub(r'\s', '', text) # 空白文字（スペースや改行）の削除 
    # text = text.replace('RT', '') # RTの削除
    # よく使う顔文字の削除
    # text = text.replace(r"＼＼\\ ٩( 'ω' )و //／／", '')
    # text = text.replace(r"⸜(๑’ᵕ’๑)⸝", '')
    texts.append(text)
  return texts

def __calculate_category_scores(tweet):
    """
    """
    category_scores=dict()
    base = os.path.dirname(os.path.abspath(__file__))
    file_name=os.path.normpath(os.path.join(base, f"./raw_word_score_dict/*.csv"))
    files = glob.glob(file_name)
    for file in files:
        match_obj=re.search("([^/]*).csv",file)
        category_name=match_obj.group(1)
        # print(file,category_name)
        score=__calculate_category_score(tweet, category_name)
        # print(category_name,score)
        category_scores[category_name]=score
    # print(category_scores)
    return category_scores


def __calculate_category_score(tweet,category_name):
    """
    tweet本文に対するあるカテゴリのスコアを計算する。
    category_file ... raw/以下にあるファイル。.csvを除く。
    [TODO] なぜか1行目しかできない
    """
    score=0
    base = os.path.dirname(os.path.abspath(__file__))
    file_name=os.path.normpath(os.path.join(base, f"./raw_word_score_dict/{category_name}.csv"))
    # print(file_name,base)
    with open(file_name) as f:
        for row in csv.reader(f):
            # if row[0] not in tweet:
            #     # print(row[0])
            #     continue
            # print(row[0])
            num=tweet.count(row[0])
            # print(num,row[0])
            if len(row)>1 and row[1] is not math.nan:
                score+=int(row[1])*num
            else:
                score+=1*num
    return score

if __name__ =="__main__":
    tweet="数学数学研究室"
    # tweet="実況今期最高聖地実況アニメイト"
    # tweet="海外スタバ"
    # category_file="Ishikitakaikei"
    category_file="MazimeRikei"
    # category_file="AnimeOtaku"
    # result=__calculate_category_score(tweet,category_file)
    # print(result)
    
    # __calculate_category_scores(tweet)

    r=get_category_name(tweet)
    print(r)
