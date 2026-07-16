# Step4 Jaccard解析

## 配置

```text
Meikai/file/Step4_Jaccard解析/
```

## 必要ライブラリ

```bash
python -m pip install pandas numpy scipy
```

## 実行順

```bash
python file/Step4_Jaccard解析/Step4-1_All_特徴間類似度.py
python file/Step4_Jaccard解析/Step4-2_歯牙障害_特徴間類似度.py
python file/Step4_Jaccard解析/Step4-3_All_事例間類似度.py
python file/Step4_Jaccard解析/Step4-4_歯牙障害_事例間類似度.py
python file/Step4_Jaccard解析/Step4-5_All_vs歯牙障害比較.py
```

## 各処理

### Step4-1
Allについて、語特徴・カテゴリ特徴・統合特徴の特徴間Jaccardを算出する。

### Step4-2
歯牙障害について、語特徴・カテゴリ特徴・統合特徴の特徴間Jaccardを算出する。

### Step4-3
Allの各事例について、Jaccard上位10件の類似事例を出す。

### Step4-4
歯牙障害の各事例について、Jaccard上位10件の類似事例を出す。

### Step4-5
All代表特徴集合と歯牙障害代表特徴集合を比較する。

## 重要

Allの事例間解析では、全組合せをCSVへ出力しない。
各事例の上位類似事例だけを保存するため、出力ファイルの巨大化を防ぐ。

## ジャッカード係数

Step4はすべてジャッカード係数を使用する。
