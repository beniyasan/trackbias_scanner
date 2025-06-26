# Netkeiba Race Result Scraper

Netkeiba（競馬サイト）からレース結果データを取得するPython + Playwright スクレイパーです。

## 対応レース

- 地方競馬 (NAR): `https://nar.netkeiba.com/race/result.html?race_id=XXXXXX`
- 中央競馬 (JRA): `https://race.netkeiba.com/race/result.html?race_id=XXXXXX`

## 取得データ

### レース基本情報
- レース名
- レース番号
- 開催日 (YYYY/MM/DD形式)
- 競馬場名（フルネーム：浦和→浦和競馬場）
- 距離
- 馬場状態（トラック状態）
- 馬場状態（表面状態）
- クラス

### 各馬の情報
- 着順
- 枠番
- 馬番
- 馬名
- タイム
- 後3F
- コーナー通過順位（中央競馬のみ）

### その他のデータ
- コーナー通過順位一覧
- ラップタイム

## 使用方法

### 前提条件

- Docker
- Docker Compose

### 実行

1. スクリプトを実行可能にする：
```bash
chmod +x run.sh
```

2. 地方競馬の結果を取得：
```bash
./run.sh "https://nar.netkeiba.com/race/result.html?race_id=202542062612"
```

3. 中央競馬の結果を取得：
```bash
./run.sh "https://race.netkeiba.com/race/result.html?race_id=202509030611"
```

### 出力

- JSONファイルが `output/race_data_{race_id}.json` として保存されます
- コンソールにもJSONデータが表示されます

### 出力例

```json
{
  "race_url": "https://nar.netkeiba.com/race/result.html?race_id=202542062611",
  "race_id": "202542062611",
  "race_type": "nar",
  "race_info": {
    "race_name": "甲武信ヶ岳特別",
    "race_number": "11",
    "race_date": "2025/06/26",
    "venue": "浦和競馬場",
    "distance": "ダ1500m",
    "track_condition": "重",
    "surface_condition": "重",
    "race_class": "サラ系一般 A2"
  },
  "horses": [
    {
      "rank": "1",
      "frame": "2",
      "horse_number": "2",
      "horse_name": "ラブリービュー",
      "time": "1:31.9",
      "last_3f": "36.4"
    }
  ],
  "corner_passing_order": {
    "corner_1": "4,2,5,3,8,7,6,1",
    "corner_2": "4,2,5,8,3,7,1,6",
    "corner_3": "4,2,1,5,8,3,7,6",
    "corner_4": "4,2,3,1,5,7,8,6"
  },
  "lap_times": {
    "distances": ["100m", "300m", "500m", "700m", "900m", "1100m", "1300m", "1500m"],
    "cumulative_times": ["7.5", "17.9", "29.9", "42.6", "55.5", "1:06.8", "1:19.5", "1:31.9"],
    "interval_times": ["7.5", "10.4", "12.0", "12.7", "12.9", "11.3", "12.7", "12.4"]
  }
}
```

## ファイル構成

- `scraper.py`: メインスクリプト
- `Dockerfile`: Docker設定
- `docker-compose.yml`: Docker Compose設定
- `requirements.txt`: Python依存関係
- `run.sh`: 実行スクリプト