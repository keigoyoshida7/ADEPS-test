# ADEPS-test — ローカルPython APIとMax

GitHub Pages版と`npm run dev`は、ブラウザ内のPython/WebAssemblyで解析します。**Maxとの接続には、このPCで動くローカル版を使ってください。** 公開サイトから直接UDPや音声機器へ接続する機能はありません。

## 1. 起動

Node.js 22.13以降・npm・Python 3.11以降を用意します。macOSでは、ダウンロードしたプロジェクトをまとめて保存し、`ADEPS-test.command`を開きます。初回は依存ライブラリを取得します。

手動起動の場合、プロジェクトのルートで実行します。

```sh
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python backend/server.py
```

上のターミナルを起動したまま、別のターミナルで実行します。

```sh
npm run dev:local
```

UIは`http://127.0.0.1:5178/`、Python APIは`http://127.0.0.1:8871/`です。`npm run dev:local`だけではPythonサーバーは起動しません。Windowsでは仮想環境内のPythonは通常`.venv\Scripts\python.exe`です。

| 用途 | ローカル接続先 |
|---|---|
| UI | TCP 127.0.0.1:5178 |
| Python API | TCP 127.0.0.1:8871 |
| MaxのOSC受信 | UDP 127.0.0.1:8872 |
| PythonのOSC応答受信 | UDP 127.0.0.1:8873 |

## 2. Maxパッチ

Max 9で`max/ADEPS_Test_Channel.maxpat`を開きます。同じフォルダのJavaScriptファイルを一緒に保持してください。追加のSpatやnpmパッケージは不要です。

1. MaxのAudio Statusで出力デバイスと論理出力1〜12の対応を確認します。
2. パッチの`START bridge`を押します。
3. ローカルUIのMax画面で接続確認を行い、必要なテストchを選びます。
4. 発音するときはMax側でDSPを手動オンにし、音量0から少しずつ上げます。
5. 終了時はMax側の`STOP TEST / MUTE`を押します。必要に応じてDSPとブリッジも停止します。

初期状態は全出力ゲート閉・音量0です。選択chを変えるたびに音量0に戻ります。Webからできる操作は接続確認・ch選択・ミュートだけです。DSP開始と音量を上げる操作はMaxで行います。

MaxのS1〜S12はテスト用の論理出力です。3D図のスピーカーやDante番号との自動対応はありません。実際の配線と音声インターフェースの設定に合わせて照合してください。ブリッジの応答は、音声・Dante同期・実際の出音を確認したことにはなりません。

## 3. 終了・問題の切り分け

- ランチャーのControl-Cは、そのランチャーが起動したサーバーを停止します。MaxのDSPは別に停止します。
- ブラウザ内計算を使うだけなら、Python APIとMaxは不要です。
- ポート競合が表示されたら、同じアプリやブリッジの二重起動を確認します。
- APIに接続できない場合はPython側のターミナルを確認します。`npm run dev`と`npm run dev:local`は解析の実行先が異なります。
- Maxの`max-api`はNode for Maxが提供します。`bridge.js`を通常のNodeから直接起動する構成ではありません。
- 応答があっても音が出ない場合は、選択ch・音量・DSP・出力機器・ch対応をMaxで確認します。

このパッチはホワイトノイズによる出力識別用です。マイク収録、スイープ生成、IR推定、校正、補正フィルター、ニューラルADEPSは実装していません。
