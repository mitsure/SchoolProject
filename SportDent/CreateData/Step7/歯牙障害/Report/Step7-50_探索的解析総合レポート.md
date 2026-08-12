# SportDent Step7 探索的解析 総合レポート：歯牙障害

- 生成日：2026-08-11
- 対象件数：1,583件
- 歯牙障害：1,583件
- 歯牙障害以外：0件
- 列数：18列
- 全セル欠損率：12.54%

## 解析目的

Step2で抽出・目視確認されたカテゴリ別データを用い、歯牙障害の特徴と研究仮説を探索した。
本レポートは探索結果の整理であり、因果推論や交絡調整済みの効果推定ではない。

## 主要知見

重要因子ランキングは、このデータセットでは解析不能または未生成だった。

研究テーマ候補ランキングは、このデータセットでは解析不能または未生成だった。

## 成果物一覧

### Table（15ファイル）

- `Table/Step7-01_解析対象項目棚卸し.csv`
- `Table/Step7-02_列別データ品質.csv`
- `Table/Step7-03_列別欠損値.csv`
- `Table/Step7-03_欠損パターン.csv`
- `Table/Step7-05_カテゴリ一覧.csv`
- `Table/Step7-07_年度別件数推移.csv`
- `Table/Step7-08_基本統計量一覧.csv`
- `Table/Step7-23_単語頻度_事例出現率.csv`
- `Table/Step7-24_品詞_品詞細分類集計.csv`
- `Table/Step7-27_Ngram_2gram_3gram.csv`
- `Table/Step7-33_Apriori_頻出項目集合.csv`
- `Table/Step7-35_AssociationRule.csv`
- `Table/Step7-36_クラスタ代表特徴.csv`
- `Table/Step7-36_クラスタ構成.csv`
- `Table/Step7-37_PCA_主要負荷量.csv`

### Summary（16ファイル）

- `Summary/Step7-02_データ品質診断サマリー.csv`
- `Summary/Step7-03_欠損値解析サマリー.csv`
- `Summary/Step7-04_重複データ確認サマリー.csv`
- `Summary/Step7-06_カテゴリ数集計.csv`
- `Summary/Step7-22_発生時間帯比較_適用可否.csv`
- `Summary/Step7-28_Jaccard_既存成果利用.csv`
- `Summary/Step7-29_WordCloud_非採用.csv`
- `Summary/Step7-30_文長基本統計.csv`
- `Summary/Step7-32_類似文章検索_既存成果利用.csv`
- `Summary/Step7-34_FPGrowth_非採用.csv`
- `Summary/Step7-36_クラスタ数評価.csv`
- `Summary/Step7-37_PCA_寄与率.csv`
- `Summary/Step7-38_tSNE_非採用.csv`
- `Summary/Step7-39_UMAP_非採用.csv`
- `Summary/Step7-45_SankeyDiagram_非採用.csv`
- `Summary/Step7-50_成果物一覧.csv`

### CSV（9ファイル）

- `CSV/Step7-04_ID重複候補.csv`
- `CSV/Step7-04_完全一致重複候補.csv`
- `CSV/Step7-26_共起ネットワーク_エッジ.csv`
- `CSV/Step7-26_共起ネットワーク_ノード.csv`
- `CSV/Step7-30_事例別文長.csv`
- `CSV/Step7-36_事例別クラスタ.csv`
- `CSV/Step7-37_PCA_事例スコア.csv`
- `CSV/Step7-40_異常値確認候補.csv`
- `CSV/Step7-41_希少事例.csv`

### Figure（2ファイル）

- `Figure/Step7-47_共起_NetworkGraph.png`
- `Figure/Step7-47_共起_NetworkGraph.svg`

### Report（2ファイル）

- `Report/Step7-01〜50_Result.txt`
- `Report/Step7-50_探索的解析総合レポート.md`

## 解釈上の重要な注意

- Step2のカテゴリ別抽出ファイルを統合したデータであり、元データベース全体を直接解析していない。
- カテゴリ間に同一事例が含まれる可能性があるため、入力診断と重複候補を併せて確認する。
- 多数の探索的比較を含む。BH補正済み結果を優先し、未補正p値のみで結論を決めない。
- オッズ比、相関、共起、関連ルールは因果関係を意味しない。
- 希少事例は自動除外していない。公表時は再識別リスクとセル秘匿を検討する。
- Sankey、WordCloud、FP-Growth、t-SNE、UMAPは、重複・誤読・解釈上の理由から非採用として記録した。

## 論文反映前の確認事項

1. 上位テーマについて、年齢・学校種・活動場面などの交絡を調整した多変量解析を行う。
2. 『高校・通学中・自転車・道路』のように意味的に重なる因子を同時投入する際は、多重共線性を確認する。
3. 主要表の分母、欠損カテゴリの扱い、0.5補正の有無をMethodsに明記する。
4. Step6のResults・Discussion・抄録へ反映する知見を研究者が最終選択する。
