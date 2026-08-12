# SportDent Step11 通学中臨床レビュー

## 現在の状態

コードブック`Step11-CB-1.0.0-rc1`は2026-08-12に承認済みです。ユーザー指示により個人名は記録せず、研究責任者・評価者A/B・第三者調停担当者の役割コードで承認履歴を保存しました。開発用A/B Excelは入力可能で、現在はいずれも0／100件です。

## 生成物と役割

`Step11_Main.py --force`は、通学中590件の自由記載から内部CSV、盲検割付および非識別集計を生成する基礎処理です。人が入力するExcelはこの処理で直接生成せず、別の`Step11_ReviewWorkflow.py prepare`で作成します。

現在は、承認済みコードブックを同梱した開発用100件の評価者A・B別Excelに加え、一人運用向けのAI仮分類・確認Excelも生成済みです。最終評価用Excelは、2名独立評価経路を再開して開発用100件を調停し、人手コードブックと機械可読な入力仕様を凍結するまで生成しません。

## 実行コマンド

一人で進める現在の経路では、次の確認用Excelを使います。AI案は研究者が全件確認するまで研究結果へ使用しません。

```bash
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py validate
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py validate --require-complete
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py export-confirmed
```

以下は、将来2名独立評価を追加する場合の経路です。

```bash
# 1回だけ：候補コードブックと開発用A/B Excelを作る（既存Excelは上書きしない）
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py prepare

# コードブックを研究責任者と評価者2名が確認した後だけ実行する
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py approve \
  --approved-by "研究責任者" \
  --reviewer-a-confirmed "評価者A" --reviewer-b-confirmed "評価者B" \
  --adjudicator "調停担当者" \
  --protection-na-rule "保護具の該当なしを選べる承認済み条件" \
  --agreement-threshold "結果を見る前に定めた一致度の指標・数値・CI判定" \
  --sparse-category-rule "κ算出不能・希少カテゴリの事前の扱い" \
  --approval-date YYYY-MM-DD

# CLI引数の代わりに、非公開チェックシートへ記入する場合
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py prepare-approval-sheet
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py check-approval-sheet --require-complete

# 完了検査後も自動承認されない。研究責任者が明示承認した場合だけ実行する
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py approve-from-sheet \
  --confirm-exact "この内容で開発用コードブックを承認する"

# 入力途中の進捗・矛盾検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py validate

# A/B各100件の完了検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py validate --require-complete

# A/B各100件が完了したら、解析より先に提出原本を固定する
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-submissions --phase 開発用 --confirm-exact "開発用A/B回答原本を凍結する"

# 固定済み原本から調停前の評価者間一致を非公開領域へ集計
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewAnalysis.py --phase 開発用

# 不一致項目＋無作為抽出した一致10事例の第三者調停票を作る
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  prepare-adjudication --phase 開発用

# 調停入力中／提出前の検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  validate-adjudication --phase 開発用
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  validate-adjudication --phase 開発用 --require-complete

# 調停済み人手合意値を固定する
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-consensus --phase 開発用 --confirmed-by "責任者" \
  --confirm-exact "この内容で人手合意値を固定する"
```

`approve`は承認前のExcelを非公開アーカイブへ保存してから、A/B Excel、承認記録、承認済みコードブックsnapshot、初期化記録を一組として更新します。回答開始後の承認処理、同じ承認記録の上書き、`prepare`の再実行は停止します。

公開側の`Step11-18_固定コードブック候補.csv`は、候補時点の監査資料として承認後も上書きしません。承認内容の正本は、非公開の`CODEBOOK_APPROVED.json`と版番号付きの承認済みsnapshotです。

承認チェックシートでは「入力値」列だけを編集し、「入力例・推奨案」は参考として残します。シートの存在、保存または完了検査だけでは承認されず、Excel回答欄も解禁されません。本Markdownを直接編集すると固定原本のハッシュが変わるため、承認内容は別紙へ入力してください。

調停票、合意値固定、最終版固定および最終評価用Excel生成の後半プログラムは実装済みです。ただし、現在はA/Bとも回答0件なので未実施です。前段階が完成していないコマンドは停止します。コードブックの修正が必要になった場合も、Excelやlockファイルを手動削除せず、旧版一式を非公開アーカイブへ保全した上で版番号を更新します。

開発用合意値の固定後は、`prepare-final-rules-draft`で最終案・変更履歴・確認表を作り、人が確認してから`freeze-final-rules`を実行します。現実装では選択肢と機械的矛盾規則を開発用版から変更せず、定義や境界例の明確化だけを許します。カテゴリ構造を変える場合は新しいコード版と未使用標本が必要です。互換する自動分類器はまだないため、`--model-rule-status`には`未実装（人手一致度評価のみ）`だけを指定できます。

```bash
# 開発用の人手合意値を固定した後
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py prepare-final-rules-draft

# FinalRulesDraft内の3資料を人が確認／記入した後だけ実行
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-final-rules --final-version "Step11-CB-1.0.0-final1" \
  --confirmed-by "責任者" --change-summary "変更内容" \
  --model-rule-status "未実装（人手一致度評価のみ）" \
  --confirm-exact "この内容で最終評価用規則を固定する"

# 凍結後にだけ、開発用と重複しない最終評価用A/B Excelを生成
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  prepare-final-excels --confirm-exact "凍結規則で最終評価用Excelを生成する"

# 最終評価の入力中／提出前検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  validate-submissions --phase 最終評価用
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  validate-submissions --phase 最終評価用 --require-complete

# 最終評価も原本固定→一致度解析→調停→合意値固定の順に行う
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-submissions --phase 最終評価用 --confirm-exact "最終評価用A/B回答原本を凍結する"
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewAnalysis.py --phase 最終評価用
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  prepare-adjudication --phase 最終評価用
```

基礎処理とExcel準備処理が扱う内部資料は次のとおりです。

- 全590件の盲検内部シート
- 開発用100件の評価者A・B別ファイル
- 開発用100件の評価者A・B別Excel
- 開発用と重複しない最終評価用100件の割付情報（Excelは凍結後まで生成しない）
- Excel入力用の選択肢、判定基準およびメタデータ
- 自動回答と歯牙障害区分を伏せた対応表
- 公開可能な小セル・二次セル抑制済み集計

人が編集する正本は評価者別Excelとし、CSVを同時に編集して二重管理しないでください。CSVは機械処理・照合用の派生ファイルとして扱います。Excelには歯牙障害区分、自動回答、相手評価者の回答を含めません。

## 実施順序

1. コードブック候補を研究者と評価者が確認し、開発用版を承認する。承認前は入力しない。
2. 開発用100件だけを評価者A・Bが別々のExcelへ独立入力する。
3. A/B双方の完了と品質検査後、第三者が別の調停シートへ合意値と理由を記録する。元のA/B回答は上書きしない。
4. 開発用の結果に基づく変更を履歴化し、最終評価用の人手コードブックと機械可読な入力仕様を凍結する。
5. 凍結後にだけ最終評価用100件を配布し、A・Bが独立入力する。最終評価中は規則を変更しない。
6. 調停前A/B回答から評価者間一致を算出し、調停後合意値を将来のGold候補として固定する。
7. 互換する自動分類器、予測封印、unblindおよび採点工程は未実装である。旧自動回答を流用せず、実装・事前凍結後にだけ別工程で性能を評価する。

最初に歯科医師へ渡すのは、各自の開発用100件のExcelだけです。全590件シート、相手評価者用ファイル、最終評価用ファイルおよび`AfterReview_DoNotOpen/`は開かないでください。

## Excel入力仕様

- `入力`：レビューIDと原文は常にロックする。回答セルも承認前はロックし、`approve`成功後だけ編集可能にする。
- `判定基準`：承認前は候補、`approve`成功後は承認済みコードブックの版と定義を表示する。
- `選択肢`：名前付き範囲を用いたドロップダウンの元データとする。
- `メタデータ`：評価段階、評価者コード、コードブック版、元CSVのハッシュを保存する。

Excelには計算式や外部リンクを置きません。進捗、空欄、コード外入力、矛盾、コメント不足および完了件数は、保存後に外部の`Step11_ReviewWorkflow.py validate`で算出し、検査レポートで確認します。

空欄は未入力、明示的な「判定不能」は評価済みとして扱います。「記載なし」「なし（明記）」「該当なし」「その他」は別の値です。必須欄の空欄、選択肢外文字またはコードブック上の矛盾があるファイルは完了扱いにしません。

## 再生成と回答保護

既存出力または人手入力がある場合は自動上書きしません。Excelを入力媒体とする場合、再生成前の人手入力検出はCSVだけでなく`.xlsx`も対象にする必要があります。回答開始後は`Step11_Main.py --force`を実行しないでください。

再生成が許されるのは、人手回答が0件で、コードブック改訂に伴う再作成を研究者が承認した場合だけです。再生成前の成果物は`CreateData/RegenerationBackups/`へ非公開権限で保存します。

## 使用停止結果

旧単一分類は複数機転の順序を扱えないため使用停止中です。旧集計・図・レポートは`CreateData/Step11_通学中臨床レビュー/Internal_DoNotPublish/`へ隔離し、図にも「使用停止・人手未確認」と表示します。`Step11-03_複数ラベル語彙検出集計_非識別.csv`は原文検索補助に限定し、人の正解や独立した仮説検証として扱いません。

## 情報管理

自動回答、歯牙障害区分、内部IDとの対応表は`CreateData/Step11_通学中臨床レビュー/InternalReview/AfterReview_DoNotOpen/`へ隔離します。各段階でA/B評価と人の合意値が固定されるまで開かないでください。

`CreateData/Step11_通学中臨床レビュー/InternalReview/`、`Internal_DoNotPublish/`および再生成バックアップは、所有者のみ読み書きできる権限で管理します。Excelのシート保護は誤編集防止にすぎず、アクセス制御の代替ではありません。いずれも公開資料、共有リポジトリ、外部AIまたは許可されていないクラウドサービスへ送らないでください。
