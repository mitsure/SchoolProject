# Macでの起動・Web公開・更新手順

この手順書は、Mac上のStudyLLMをOllamaで動かし、ngrok経由でiPadなどから閲覧するためのものです。

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

Codex等でGitHub上のStudyLLMを更新した後、Mac側へ最新版を反映します。

```bash
cd ~/Documents/SchoolProject
git pull origin main
cd SportDent/StudyLLM
source .venv/bin/activate
python -m pip install -r requirements.txt
launchctl kickstart -k gui/$(id -u)/jp.sportdent.studyllm
launchctl kickstart -k gui/$(id -u)/jp.sportdent.ngrok
open http://127.0.0.1:8000
open http://127.0.0.1:4040
```

これで、更新後のStudyLLMと公開URLを確認できます。

なお、画面から「確定保存」したデータは次のファイルに保存されています。

```text
~/Documents/SchoolProject/SportDent/StudyLLM/data/reviews.sqlite3
```

この保存DBはGitHubからの`git pull`では更新・削除されません。
