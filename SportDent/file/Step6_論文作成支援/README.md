# Step6 論文作成支援

## 目的

Step5で整理した解析結果を読み込み、論文本文の下書き、抄録、図表キャプション、論文構成案を作成する。

Step6は新しい統計解析を行わない。
Step1からStep5までの結果を文章化する工程である。

## 配置

```text
Meikai/file/Step6_論文作成支援/
```

## 実行順

```bash
python file/Step6_論文作成支援/Step6-1_Methods下書き作成.py
python file/Step6_論文作成支援/Step6-2_Results下書き作成.py
python file/Step6_論文作成支援/Step6-3_Discussion候補作成.py
python file/Step6_論文作成支援/Step6-4_抄録下書き作成.py
python file/Step6_論文作成支援/Step6-5_Table_Figureキャプション作成.py
python file/Step6_論文作成支援/Step6-6_論文構成案作成.py
```

## 出力先

```text
CreateData/Step6_論文作成支援/
├─ Text/
│  ├─ Methods下書き
│  ├─ Results下書き
│  ├─ Discussion候補
│  └─ 抄録下書き
├─ Captions/
│  ├─ Tableキャプション
│  └─ Figureキャプション
├─ Structure/
│  ├─ 論文構成案
│  └─ 論文完成チェックリスト
└─ 各Stepの解析サマリー.csv
```

## 各Step

### Step6-1
解析工程をMethodsの文章へ変換する。

### Step6-2
Table4、Table5、Table7、Table8からResultsの数値記述を作る。

### Step6-3
Step5-7の考察支援データからDiscussionの論点候補を作る。

### Step6-4
目的、方法、結果、結論から構造化抄録の下書きを作る。

### Step6-5
TableおよびFigureのキャプション案を作る。

### Step6-6
各下書きを統合し、論文構成案と完成チェックリストを作る。

## 重要な注意

- Step6の文章は下書きであり、そのまま提出しない。
- Resultsの数値は元CSVと照合する。
- Discussionには先行研究の検索と引用が必要。
- ジャッカード係数や共起関係から因果関係を主張しない。
- 対象期間、対象件数、除外基準、倫理的配慮は実際の研究条件に合わせて追記する。
