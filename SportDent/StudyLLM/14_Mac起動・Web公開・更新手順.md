# Macでの起動・Web公開・更新手順

## 普段はダブルクリックで操作できます

初回設定済みのMacでは、FinderでStudyLLMフォルダを開き、次のファイルをダブルクリックしてください。

- `起動.command`：Mac再起動後や接続できなくなったとき。OllamaとStudyLLMを起動し、ngrokを確認して公開画面を開きます。
- `更新して起動.command`：GitHubの更新を取得し、必要なライブラリをインストールしてから同じ起動処理を行います。

最初の1回だけ、Macのターミナルで次を実行してボタンを取得します。

```bash
cd ~/Documents/SchoolProject
git pull --ff-only origin main
open SportDent/StudyLLM
```

Finderで各ファイルのエイリアスを作り、デスクトップに置くと便利です。ファイル本体はStudyLLMフォルダから移動しないでください。

ボタンは途中で失敗するとエラーを表示して停止します。起動完了後はEnterキーでターミナルを閉じて構いません。Macのスリープ防止は別途必要です。手順書のみの更新は、下記3-1の取得だけでも完了します。

以下は初回設定と、手動で操作する場合の手順です。

この手順書は、Mac上のStudyLLMをOllamaで動かし、ngrok経由でiPadなどから閲覧するためのものです。

研究評価機能を追加した版では、更新・再起動後にメニューの「研究評価ダッシュボード」を利用できます。DBの追加列・評価テーブルは起動時に作成されます。評価項目と操作方法は[研究評価DBとダッシュボード](15_研究評価DBとダッシュボード.md)を参照してください。

次の3つが動いている間だけ、Web上から利用できます。

- Ollama：ローカルLLM
- StudyLLM：入力・判定・保存画面
- ngrok：StudyLLMをインターネットへ公開

Macがスリープ中、ログアウト中、電源オフ、またはインターネット未接続のときは利用できません。

## 1. 最初に設定するとき

### 1-1. Ollamaを準備する

Macの「アプリケーション」からOllamaを起動します。その後、ターミナルで次を実行します。

```bash
ollama list
```

一覧に`qwen3:8b`があれば準備完了です。なければ次を実行します。

```bash
ollama pull qwen3:8b
```

### 1-2. StudyLLMを準備して自動起動を設定する

次のコマンドを上から1行ずつ実行します。

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
chmod +x scripts/install_macos_autostart.sh
./scripts/install_macos_autostart.sh
```

最後のコマンドでは、公開用のユーザー名と12文字以上のパスワードを入力します。入力したパスワードは画面に表示されません。

パスワードやngrokの認証トークンは、チャット、GitHub、画面写真へ載せないでください。

### 1-3. ngrokの自動起動を設定する

ngrokのインストールと認証が済んでいることを確認します。

```bash
ngrok version
```

バージョンが表示されたら、次を実行します。

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
chmod +x scripts/install_ngrok_autostart.sh
./scripts/install_ngrok_autostart.sh
```

### 1-4. 表示を確認する

```bash
open http://127.0.0.1:8000
open http://127.0.0.1:4040
```

- `127.0.0.1:8000`：Mac内でStudyLLMを確認する画面
- `127.0.0.1:4040`：ngrokの状態と公開URLを確認する画面

ngrok画面の`Forwarding`に表示された`https://...ngrok-free...`のURLを、iPadなどで開きます。

## 2. Macの電源を落とした・再起動したとき

Macへログインし、「アプリケーション」からOllamaを起動します。その後、ターミナルで次を実行します。

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
launchctl kickstart -k gui/$(id -u)/jp.sportdent.studyllm
launchctl kickstart -k gui/$(id -u)/jp.sportdent.ngrok
open http://127.0.0.1:8000
open http://127.0.0.1:4040
```

`127.0.0.1:8000`でStudyLLMが表示され、`127.0.0.1:4040`の`Forwarding`に公開URLが表示されれば復旧完了です。

### 接続できない場合

まず、どちらの画面が開かないかを確認します。

- `8000`が開く、`4040`が開かない：StudyLLMは正常で、ngrokが停止しています。
- `8000`が開かない：StudyLLMが停止しています。
- 両方開くが判定が終わらない：Ollamaが停止している可能性があります。

#### 8000は開くが、4040が開かない場合

次を実行してngrokの自動起動設定を再登録します。

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
chmod +x scripts/install_ngrok_autostart.sh
./scripts/install_ngrok_autostart.sh
open http://127.0.0.1:4040
```

今回のMac更新後は、次のエラーが表示されました。

```text
Could not find service "jp.sportdent.ngrok" in domain for user gui: 501
```

これはngrok本体や認証トークンの問題ではなく、macOSの自動起動サービスからngrokの登録が外れていた状態です。`install_ngrok_autostart.sh`による再登録で復旧しました。

#### 8000が開かない場合

まずStudyLLMを再起動します。

```bash
launchctl kickstart -k gui/$(id -u)/jp.sportdent.studyllm
open http://127.0.0.1:8000
```

ここでも`Could not find service`が表示された場合は、次を実行して自動起動設定を再登録します。

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
source .venv/bin/activate
./scripts/install_macos_autostart.sh
open http://127.0.0.1:8000
```

このスクリプトでは、公開用ユーザー名と12文字以上のパスワードをもう一度設定します。保存済みDBは削除されませんが、既にログインしている端末では再ログインが必要になります。

#### 画面は開くが、判定が終わらない場合

「アプリケーション」からOllamaを起動し、次でモデルを確認します。

```bash
ollama list
```

`qwen3:8b`が表示されたら、もう一度StudyLLMで判定します。

#### 8000と4040は開くが、iPadから接続できない場合

`http://127.0.0.1:4040`を開き、`Forwarding`に現在表示されている`https://...ngrok-free...`を使います。Macがインターネットに接続され、スリープしていないことも確認します。

研究発表中など、Macをスリープさせたくないときは別のターミナルで次を実行し、そのターミナルを開いたままにします。

```bash
caffeinate -dimsu
```

終了するときは、そのターミナルで`Control + C`を押します。

## 3. GitHub側のデータやプログラムを更新したとき

Codex等でGitHub上のStudyLLMを更新した後、Mac側へ最新版を反映します。Mac本体の再起動は不要です。以下をひと区切りずつ実行してください。

### 3-1. 更新を取得して確認する

```bash
cd ~/Documents/SchoolProject
git pull --ff-only origin main
git log -1 --oneline
```

最後に表示されたコミット番号・説明を、更新時に案内された内容と照らし合わせます。より新しい更新がある場合は、そのコミットが表示されます。

`git pull`にエラーが出た場合は、ここで止めてエラー内容を確認してください。`Already up to date.`は正常ですが、案内された修正が含まれているかも確認します。

今回の起動エラーは、修正前の`8cf2044`のまま起動していたことが原因でした。修正コミット`7652c02`を取得して再起動すると復旧しました。この番号は今回の記録であり、今後の更新で毎回一致させる番号ではありません。

手順書だけの更新なら、ここで完了です。以下の再起動は不要です。

### 3-2. プログラムを更新した場合はStudyLLMを再起動する

```bash
cd ~/Documents/SchoolProject/SportDent/StudyLLM
source .venv/bin/activate
python -m pip install -r requirements.txt
```

エラーがなければ、次を実行します。

```bash
launchctl kickstart -k gui/$(id -u)/jp.sportdent.studyllm
```

数秒待ってから画面を開きます。再起動コマンドがエラーなしで終わっても、アプリが起動できたとは限らないため、画面まで確認してください。

```bash
open http://127.0.0.1:8000
```

ログイン画面が開いたら、いつもの公開URLでも確認します。ngrokが動いていれば、再設定・再起動は不要です。

開かない場合は、次の結果で起動エラーを確認します。

```bash
cd ~/Documents/SchoolProject
git log -1 --oneline
curl -I --max-time 5 http://127.0.0.1:8000
tail -n 40 SportDent/StudyLLM/logs/studyllm.err.log
```

相談するときは、この実行結果だけを共有してください。ローカル画面は開くのに公開URLだけ開かない場合は、「2. 接続できない場合」のngrokの手順を使います。

画面上でデータを保存・編集しただけなら、`git pull`も再起動も不要です。

なお、画面から「確定保存」したデータは次のファイルに保存されています。

```text
~/Documents/SchoolProject/SportDent/StudyLLM/data/reviews.sqlite3
```

この保存DBはGitHubからの`git pull`では更新・削除されません。
