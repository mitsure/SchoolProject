# Step11 通学中臨床レビュー

## 入力開始前の重要事項

通学中590件の自由記載を歯科医師が確認するための内部資料です。コードブック`Step11-CB-1.0.0-rc1`は2026-08-12に承認済みで、開発用A/B Excelの回答欄は入力可能です。ユーザー指示により個人名は記録せず、各担当の役割コードで承認履歴を保存しています。

`InternalReview/`は事故原文、レビュー回答および内部対応情報を含むため非公開です。

## 重要：旧単一分類結果は使用停止中

歯科医師による人手判定前で、現行の旧ルールは出来事の順序を判定できません。旧単一主受傷機転、直接外力、予防可能性、関連検定および図は`Internal_DoNotPublish/`へ隔離しました。ルール改訂と独立した人手評価が完了するまで研究結果として使用しないでください。`Step11-03_複数ラベル語彙検出集計_非識別.csv`は内部の原文検索補助に限定します。

## 監査時点の確認状況

- 3種の機転語のうち2種以上が検出された事例：136／590件
- 転倒語と衝突語の両方が検出された事例：89／590件
- 再生成直後の歯科医師回答：0件

これらは自動語彙検出または入力状況の確認値であり、歯科医師確認済みの臨床結果ではありません。

## Excelで入力するファイル

承認後は、評価者ごと・評価段階ごとに分けたExcelだけへ入力します。CSVは機械処理・照合用であり、人がExcelと並行して編集しません。Excelには計算式や外部リンクを置かず、進捗と矛盾は外部の`Step11_ReviewWorkflow.py validate`で検査します。

- 開発用：`InternalReview/Step11-08A_開発用_評価者A_盲検100件.xlsx`
- 開発用：`InternalReview/Step11-08B_開発用_評価者B_盲検100件.xlsx`

現時点で生成対象とするExcelは、上記の**開発用A/Bだけ**です。最終評価用Excelは、開発用100件の調停、コードブック改訂および最終評価用版の凍結が完了するまで生成しません。後半プログラムは実装済みですが、現在は前提未完了のため下記2ファイルをまだ生成していません。

- 最終評価用：`InternalReview/Step11-16A_最終評価用_評価者A_盲検100件.xlsx`
- 最終評価用：`InternalReview/Step11-16B_最終評価用_評価者B_盲検100件.xlsx`

## 現在の実行状態とコマンド

開発用A/B Excelとコードブック版`Step11-CB-1.0.0-rc1`の承認記録は作成済みです。現在の回答はA/Bとも0／100件です。

```bash
# コードブック確認後に承認を記録し、入力を解禁する
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py approve \
  --approved-by "研究責任者" \
  --reviewer-a-confirmed "評価者A" --reviewer-b-confirmed "評価者B" \
  --adjudicator "調停担当者" \
  --protection-na-rule "保護具の該当なしを選べる承認済み条件" \
  --agreement-threshold "結果を見る前に定めた一致度の指標・数値・CI判定" \
  --sparse-category-rule "κ算出不能・希少カテゴリの事前の扱い" \
  --approval-date YYYY-MM-DD

# 非公開チェックシートを使う場合（「入力値」列だけを編集）
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py check-approval-sheet --require-complete

# 完了検査だけでは解禁されない。研究責任者の明示承認後だけ実行
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py approve-from-sheet \
  --confirm-exact "この内容で開発用コードブックを承認する"

# 保存後の進捗・矛盾検査（入力途中でも実行可）
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py validate

# 提出前のA/B各100件完了検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py validate --require-complete

# 完了検査後、解析より先にA/B提出原本を固定
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-submissions --phase 開発用 --confirm-exact "開発用A/B回答原本を凍結する"

# 固定済み原本だけから評価者間一致を算出
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewAnalysis.py --phase 開発用

# 第三者調停票を生成し、入力後に検査
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  prepare-adjudication --phase 開発用
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  validate-adjudication --phase 開発用 --require-complete

# 人手合意値を固定
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_PostReviewWorkflow.py \
  freeze-consensus --phase 開発用 --confirmed-by "責任者" \
  --confirm-exact "この内容で人手合意値を固定する"
```

開発用Excelがまだ生成されていない、コードブック版が空欄、または「承認済み」の表示がない場合は入力を開始しません。

公開側の`Step11-18_固定コードブック候補.csv`は候補時点の監査資料です。承認後も候補ファイルは上書きせず、承認記録の正本と承認済みsnapshotは非公開領域で版番号付き管理します。

承認内容は`InternalReview/Step11-19_コードブック承認チェックシート.csv`の「入力値」列へ記入します。判定基準Markdown、項目ID、確認項目、入力例または説明列は編集しません。保存しただけでは承認されません。

最初に各評価者が開くのは、自分の**開発用100件**だけです。全590件シート、相手評価者用、最終評価用および`InternalReview/AfterReview_DoNotOpen/`は開かないでください。

## Excelの使い方

1. `メタデータ`で評価段階、評価者コード、コードブック版および承認状態を確認する。
2. `判定基準`を読んでから`入力`を開く。
3. `承認済み`表示を確認する。承認後に黄色になる回答セルだけへドロップダウンで入力し、レビューIDと原文は変更しない。
4. 空欄は未入力のままとし、読んでも決められない場合は選択肢の「判定不能」を選ぶ。
5. 「記載なし」「なし（明記）」「該当なし」「その他」を区別する。「その他」はコメントを入力する。
6. Excelを保存し、外部の`Step11_ReviewWorkflow.py validate`を実行して、出力された検査レポートで空欄、コード外入力、矛盾およびコメント不足が0件になったことを確認する。Excel内に数式や外部リンクは置かない。
7. 完了後はファイル名、シート名、列、レビューIDまたは原文を変更せず提出する。

Excelのシート保護は誤操作を防ぐためのもので、パスワード暗号化やアクセス制御の代わりではありません。

## 開発から最終評価までの順序

### 一人運用（現在の実施経路）

`InternalReview/SoloAssistedReview/Step11-32_一人研究者確認用_開発用100件.xlsx`を使用します。AI案が入力済みなので、`AI確認優先度`の最優先→要確認→通常の順で原文と照合し、修正後に各行の`行確認`を`確認済み`にします。A/B原本は変更しません。

```bash
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py validate
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py validate --require-complete
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_SoloAssistedReview.py export-confirmed
```

この経路はAI仮分類を研究者1名が全件確認する方式であり、2名独立評価、Cohenのκまたは調停済みGold Standardとは扱いません。

590件AI暫定分類の標本監査では、開発用と重複しない100件の次のExcelへ、AI回答を見ずに入力します。

`InternalReview/SoloAssistedReview/Audit100/Step11-47_一人確認用_AI標本監査100件.xlsx`

```bash
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_AIAuditWorkflow.py validate
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_AIAuditWorkflow.py validate --require-complete
.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_AIAuditWorkflow.py score
```

入力完了前は`score`が停止し、AI回答と歯牙障害区分は`AfterAudit_DoNotOpen/`へ隔離されます。

### 2名独立評価（将来の追加検証経路）

1. 研究者がコードブック候補を承認し、開発用版番号を付ける。
2. 開発用100件を評価者A・Bが別ファイルで独立評価する。
3. A/B双方の完了後、第三者が別の調停シートへ合意値と調停理由を記録する。A/B原回答は変更しない。
4. 開発用で見つかった定義上の問題と変更内容を履歴へ残す。
5. 最終評価用の人手コードブックと機械可読な入力仕様を版番号付きで凍結する。
6. 凍結後にだけ、重複しない最終評価用100件をA・Bが独立評価する。
7. 最終評価中は選択肢、定義、分類規則を変更しない。新たな問題は逸脱記録へ残す。
8. 調停前A/B回答から評価者間一致を算出し、調停後合意値は将来のGold候補として固定する。
9. 互換する自動分類器・予測封印・unblind・採点工程は未実装である。旧自動回答を性能評価へ流用しない。

調停票、合意値固定、最終版固定および最終評価用Excel生成の後半プログラムは実装済みですが、現時点では未実施です。開発用合意値固定後に`prepare-final-rules-draft`→人による3資料の確認→`freeze-final-rules`→`prepare-final-excels`の順で進めます。最終評価中の進捗は`validate-submissions --phase 最終評価用`で検査します。候補コードブックの確認で修正が出た場合も、Excelやlockファイルを手動削除せず、旧候補一式を非公開アーカイブへ保全して版番号を更新してから再生成します。

現実装では選択肢と機械的矛盾規則を開発用版から変更せず、最終版では定義・境界例だけを明確化します。カテゴリ構造を変える場合は新コード版と未使用標本が必要です。凍結後訂正用revision経路は未実装なので、訂正が必要なら原本を上書きせず工程を停止します。

## 空欄と判定不能

- 空欄：未入力または入力途中。提出時には必須欄0件とする。
- 判定不能：原文を確認したが情報不足等で決められない。有効な入力値として件数を残す。
- 記載なし：原文に言及がない。事実として「なし」とは限らない。
- なし（明記）：否定内容が原文に明記される。
- 該当なし：その項目が適用されない。
- その他：既定カテゴリ外。コメント必須。

判定不能例は精度計算から黙って除外せず、判定可能件数、判定不能件数および各指標の分母を報告します。

## 回答保護と情報管理

レビューIDは元データ順や歯牙障害区分を示さない暗号学的乱数による不透明IDです。公開集計の1〜4件セルは、差し引きによる復元を防ぐ二次セルとともに非表示にしています。

人手回答を開始した後はStep11を再生成しません。既存のCSVまたはExcelに回答がある場合は、再生成・上書きを停止する必要があります。回答済みファイルのA/B原本、調停前原本および版番号を保存し、修正が必要な場合も原回答を上書きせず変更履歴を残します。

`InternalReview/AfterReview_DoNotOpen/`は、各段階のA/B評価と人の合意値が固定されるまで開かないでください。原文、内部ID、レビューID対応表、回答、コメントおよび調停記録は、公開資料、投稿補足資料、共有リポジトリ、外部AIまたは許可されていないクラウドサービスへ送らないでください。

公開できるのは、小セル抑制・二次セル抑制を行った集計値のみです。個票、原文、自由コメント、旧単一自動分類結果は公開しません。
