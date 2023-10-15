# 自作サイト概要
YouTube人気配信者を対象にしたスーパーチャットの集計サイトです。<br >
事務所や言語圏(日本語/海外)で絞り込んで表示することができます。 <br >
毎日AM10時頃に前日のスーパーチャットを集計するプログラムが動きます。 <br >
レスポンシブ対応しているのでスマホからもご確認いただけます。
 <img width="1400" alt="スクリーンショット 2020-05-07 0 06 18" src="https://user-images.githubusercontent.com/60876388/81193748-c51d9b00-8ff6-11ea-9981-46789f016300.png">
 <img width="350" height="700" src= "https://user-images.githubusercontent.com/60876388/81476543-643bd000-924d-11ea-9d26-cac305ca9f91.jpeg">

# URL
https://www.liverank.jp/ranking <br >

# 使用技術
- Python
    - Django
    - pytchat(スーパーチャット集計用ライブラリ)
    - YoutubeDataAPI v3
    - 外国為替確認API
- HTML/CSS
- Chart.js(グラフ描画用)
- Heroku
    - PostgreSQL

# AWS構成図
<img width="995" alt="スクリーンショット 2020-05-07 11 14 01" src="https://user-images.githubusercontent.com/60876388/81247155-3ccde300-9054-11ea-91eb-d06eb38a63b3.png">

# SEO対策
SEO対策に注力しました。<br >
情報収集する中で複数の情報源で重要だとされた基礎的な要素(キーワード選定、altタグの設定、内部リンクの拡充等)に加え、データ列挙型サイトという形式の競争優位性に着目しました。<br >
2023/10/16時点、このサイトが想定する最も検索数が大きいキーワード「スパチャランキング」の検索結果で1位、2位の表示を達成しています。
(2023/10/09-2023/10/16における検索結果:https://docs.google.com/spreadsheets/d/1nji848QL_ZuHSI6-B5Agxj8MaRMxLexpSLZd7WAKLzA/edit?usp=sharing)

# 機能一覧
- 期間選択(累計/月間/日間)
- 条件絞り込み(事務所/言語圏/性別/Vtuberかどうかなど)
- 検索
- 自動更新(サーバー内)
- 配信者登録ページ()

# テスト
- RSpec
  - 単体テスト(model)
  - 機能テスト(request)
  - 統合テスト(feature)