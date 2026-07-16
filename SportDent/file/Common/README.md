# Common

## 1. 目的

Step3以降の解析で共通利用する設定ファイルとPython関数を一元管理する。

同じ処理や辞書を`Step3_All`と`Step3_歯牙障害`へ重複配置せず、Commonを1か所修正すれば両方へ反映される構成とする。

---

## 2. 配置先

```text
Meikai/
└─ file/
   └─ Common/
      ├─ README.md
      ├─ Config/
      └─ Utils/
```

---

## 3. Config

### 設定_ストップワード.txt

形態素解析後に除外する一般語を、1行1語で管理する。

例：

```text
する
いる
ある
事故
発生
生徒
児童
```

研究目的に必要な語まで除去しないよう、出力結果を確認しながら修正する。

### 設定_事故カテゴリ辞書.json

自由記述から次の項目を抽出するための辞書。

- 移動手段
- 事故現象
- 誘因
- 衝突対象
- 受傷部位

### 設定_歯種辞書.json

歯牙障害の文章から、前歯・中切歯・側切歯・犬歯・臼歯などを抽出するための辞書。

### 設定_同義語辞書.json

表記揺れや同義表現を代表語へ統一する。

例：

```text
転んだ、倒れた → 転倒
熱傷、やけど → 火傷
```

---

## 4. Utils

### csv_reader.py

複数の日本語文字コード候補でCSVを読み込む。

### output.py

出力先を自動生成し、CSVをUTF-8 with BOMで保存する。

同名CSVは上書きする。

### validation.py

必要列の存在と、入力データが0件でないことを確認する。

### text_utils.py

- ストップワード読込
- JSON辞書読込
- キーワードとラベルの照合
- 同義語統一

---

## 5. Pythonからの利用方法

各Pythonでプロジェクト直下の`file`をimport対象へ追加する。

```python
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "file"))
```

その後、次のように読み込む。

```python
from Common.Utils.csv_reader import load_csv
from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns
from Common.Utils.text_utils import load_stopwords
```

---

## 6. ジャッカード係数

Common自体ではジャッカード係数を計算しない。

Commonは、Step3の特徴作成とStep4以降の類似度解析で共通利用する辞書・関数を提供する。

---

## 7. 修正時の注意

- 辞書を変更するとAllと歯牙障害の両方の結果が変わる
- ストップワードを増やしすぎない
- 同義語統一によって意味の異なる語をまとめない
- 辞書変更後は関連Stepを再実行する
- 出力CSVは上書きされるため、必要な旧結果は別途保存する
