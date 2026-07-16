# Step3_歯牙障害 3-3から3-7

## 配置
すべて以下へ配置する。

```text
Meikai/file/Step3_歯牙障害/
```

## 実行順

```bash
python file/Step3_歯牙障害/Step3-3_歯牙障害_頻出語集計.py
python file/Step3_歯牙障害/Step3-4_歯牙障害_共起語解析.py
python file/Step3_歯牙障害/Step3-5_歯牙障害_ストップワード除去.py
python file/Step3_歯牙障害/Step3-6_歯牙障害_カテゴリ分類.py
python file/Step3_歯牙障害/Step3-7_歯牙障害_特徴語抽出.py
```

## 必要ライブラリ

```bash
python -m pip install pandas numpy scikit-learn
```

## 補足
既存のStep3-3_歯牙障害_頻出語集計.pyは上書きする。
