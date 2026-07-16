# Step5 結果整理

## 目的

Step1からStep4までの解析結果を、論文・学会発表で使用しやすい表、グラフ、ランキング、考察材料へ変換する。

## 配置

```text
Meikai/file/Step5_結果整理/
```

## 必要ライブラリ

```bash
python -m pip install pandas numpy matplotlib
```

Step5-6の画像・PDF出力では`HeiseiMin-W3`を指定する。

## 実行順

```bash
python file/Step5_結果整理/Step5-1_全体比較集計.py
python file/Step5_結果整理/Step5-2_歯牙障害特徴ランキング.py
python file/Step5_結果整理/Step5-3_Jaccard結果整理.py
python file/Step5_結果整理/Step5-4_事故パターン分析.py
python file/Step5_結果整理/Step5-5_論文掲載表作成.py
python file/Step5_結果整理/Step5-6_論文掲載グラフ作成.py
python file/Step5_結果整理/Step5-7_考察支援データ作成.py
```

## 出力先

```text
CreateData/Step5_結果整理/
├─ Tables/
├─ Figures/
├─ 考察支援/
└─ 各Stepの解析サマリー.csv
```

## Table番号

- Table1: All vs 歯牙障害 頻出語比較
- Table2: All vs 歯牙障害 特徴語比較
- Table3: All vs 歯牙障害 カテゴリ比較
- Table4: 歯牙障害 特徴語ランキング
- Table5: 歯牙障害 特徴カテゴリランキング
- Table6: Jaccard上位ペア
- Table7: 歯牙障害 Jaccard上位ペア
- Table8: 歯牙障害 事故パターンランキング
- Table9: 歯牙障害 パターン構成要素

## Figure番号

- Figure1: 歯牙障害特徴語Top20
- Figure2: 歯牙障害特徴カテゴリTop20
- Figure3: 歯牙障害Jaccard上位ペア
- Figure4: 歯牙障害事故パターンTop15

## 注意

- Jaccard係数は関連性・類似性を示すが、因果関係を示さない。
- 事故パターンの構成要素の並びは、時系列順序を意味しない。
- カテゴリ分類結果はCommonの辞書品質に依存する。
- FigureのPDF・画像はHeiseiMin-W3を指定するため、実行環境へ同フォントが必要。
