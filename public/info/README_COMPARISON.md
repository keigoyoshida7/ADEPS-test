# ADEPS-test — Maxで方式を切り替える

`ADEPS_Method_Comparison.maxpat` は、同じ観測から復元した9方式と参照音を、再生位置を揃えて比較するMax 9用パッチです。配布バンクを展開し、同梱の `max/` フォルダをまとめて保持してください。Node for Maxの標準 `max-api` を使うため、npm installは不要です。既存の `ADEPS_Experiment.maxpat` とは別のパッチです。

## 手順

1. 配布ZIPを展開し、`max/ADEPS_Method_Comparison.maxpat` を開きます。開いただけでは音は出ません。
2. **Controllerを開始**、続いて **同梱バンク / Load bundled bank** を押します。展開フォルダ直下の `max-comparison.json` を読み、10本のWAVのハッシュと規約を検証します。Maxのバッファ読込が全て完了すると `READY` になります。他のバンクは **別バンクを開く** でJSONを選べます。同梱バンクのないリポジトリ側のパッチでは、別バンクのJSONを選んでください。
3. メニューで方式を選びます。最初は `linear_tuned`。Webのローカル版からも、同じバンクの方式を選択できます。方式の変更は再生開始・ミュート解除を行いません。
4. **MaxのAudio Statusで機器と出力1–12の接続先を確認**します。RUNとDSPを手動で有効にし、共通音量を0から少しずつ上げます。手動の調整範囲は0〜1です。1は配布音のゲインを保つ値で、現地の安全音圧を保証する値ではありません。
5. 再生中に方式を変えると、同じ再生位置のまま50msで切り替わります。**STOP / MUTE** は再生と共通音量を0にします。再開時には音量を再度設定します。

このパッチの出力は、12台への**デコード済み信号**です。4chを4台へ直結する使い方ではありません。既存のAFCオブジェクト入力へ12chをそのまま送らず、現地担当者と入力経路・既存処理・ゲインを照合してください。

## 何を比較するか

参照、標準Linear、調整Linear、既知雑音Linear、既存ADEPS、調整ADEPS、空間事前分布のみ、波形整合のみ、ADEPS+α、ADEPS+αのノイズ除去器OFFです。ラベルはバンクの記録を表示します。各方法の条件・結果はWebの比較ページと配布記録を参照してください。

配布バンクは2種類です。1場面版は合成テストscene 0の0.248秒。32場面版は全テスト短片を同じ順番で並べた12.586秒で、Webではこちらを初期選択にしています。各短片は0.248秒で、共通の端フェードと150msの間隔があります。方式・場面ごとの音量補正はありません。**現地の音を新しく録音・推定する機能や、部屋の校正機能ではありません。** 保存音の復元方式による違いを、同じスピーカー系で聴くための準備です。連続音声の推論ではなく、短片だけで音楽・会話全般や実会場での推定品質は判断できません。

## 同期、音量、12ch変換

- 入力は16kHz / FLOAT32 / 4ch **ACN/N3D、W・Y・Z・X**。旧ExperimentパッチのSN3D表記とは異なります。
- 各WAVには同じ `shared_gain` が既に適用済みです。Maxでこの値を再び掛けません。方法ごとの音量正規化・AGCはありません。
- 1本の `phasor~` から生成したミリ秒位置信号を、全10本の `play~` へ同時に送ります。方法の変更はクロックを触らず、10個の重みだけを同じ50msで線形補間します。同一音同士の切替でゲインが増える等電力クロスフェードは使いません。
- ループ末尾に共通250msの無音区間、外端に共通5msのフェードがあります。配布WAV自体は変更しません。バンク自身に共通の端フェードがある場合は、この再生フェードも重なります。境界近傍は未加工WAVの評価数値と同じ信号ではありません。
- MaxのDSPサンプルレートが16kHz以外の場合、`play~` の位置参照による補間を全方法に同じ条件で使います。ここで高域の推定情報が増えることはありません。
- 共通の12×4行列を使い `g(t)=D a(t)` とします。標準バンクのDは保存配置、仮定した聴取点 `[0,0,1.2] m`、λ=0.001に基づきます。元座標はX右/Y前/Z上、FOA座標へ `[Y,-X,Z]` と変換。`Y` の行は `[1,√3dy,√3dz,√3dx]`、`D=Y(YᵀY+λI)⁻¹` です。
- 出力S1–S12は保存プロジェクトID順です。Dante番号の同定ではありません。**11/12は以前の画面記録と順序が逆なので、出力前に現地で照合してください。** 聴取点・距離補償・部屋の補正・スピーカーの実際のゲインは未校正です。
- Nodeの応答が1.5秒途絶えるとパッチは停止・ミュートします。ローカルのSTOPはNodeを経由しません。DSPの起動、機器選択、音量上げをネットワークから行うAPIはありません。

## ローカルWebとの制御

Maxは `127.0.0.1:8874` でOSCを受信し、返信を `127.0.0.1:8875` に送ります。既存チャンネル確認ブリッジの8872/8873とは別です。Pages版から直接UDPは使えないため、Web操作にはローカルAPIが必要です。Max側だけでメニューを操作することもできます。

| 要求 | 返信 |
|---|---|
| `/adeps-compare/ping [seq:int32]` | `/adeps-compare/status [seq, ready:0/1, selectedId:string, inputSHA:string]` |
| `/adeps-compare/select [methodId:string, expectedInputSHA:string]` | `/adeps-compare/ack ["select", methodId, inputSHA]` |
| `/adeps-compare/mute []` | `/adeps-compare/ack ["mute", "", inputSHA]` |

`ready=1` は10本のファイル検証とMaxバッファの読込確認が済んだ状態です。選択ACKは制御メッセージをMaxに渡した確認で、スピーカーが鳴ったことの確認ではありません。DSP・実際の音圧・ミュート状態は返信から推測しません。別バンクのSHAを指定した選択は拒否します。未知方式・形式不正・自動再生/ゲイン変更指示も受け付けません。

## English quick guide

Extract the bank ZIP and keep all files in `max/` together. Open `ADEPS_Method_Comparison.maxpat`, start its controller, then click **Load bundled bank**. This reads the root `max-comparison.json` next to the `max/` folder. Use **Other bank** to select another manifest. Wait for READY after all ten four-channel buffers are verified. Choose a method, check the audio device and twelve output routes, enable RUN/DSP manually, and raise the common gain from zero. STOP sets playback and gain to zero. Selecting a method never starts audio or raises the gain.

All methods use one signal-rate playhead, a 50ms linear method crossfade, one common gain, and the same ACN/N3D-to-12-channel decoder. The WAVs already contain the common export gain. Playback adds a shared 250ms loop gap and 5ms outer-edge fades. The source is a saved synthetic test; this patch does not infer a new venue recording or calibrate the room. Confirm saved output IDs against physical routes, particularly channels 11 and 12. Web control requires the local API; the online page cannot send UDP directly.

Two banks are available: one 0.248-second example, and a 12.586-second montage containing all 32 test crops in the same order. The montage is the default Web selection. Every crop is 0.248 seconds with common edge fades and 150ms gaps; this is not continuous-speech inference. There is no per-method or per-scene normalization.

## 検証・出典

`node --test max/method-comparison.test.js` でバンク破損、同期グラフ、初期無音、バッファ確認、OSC照合を検証できます。`node max/build-method-comparison-patch.js` は同じパッチを再生成します。これらのCPUテストは実機の音声出力試験とは別です。

使用した公式仕様: [play~の位置入力](https://docs.cycling74.com/reference/play~/)、[buffer~の読込完了](https://docs.cycling74.com/reference/buffer~/)、[Bufferの実データ寸法](https://docs.cycling74.com/apiref/js/buffer/)、[matrix~の接続係数](https://docs.cycling74.com/reference/matrix~/)、[phasor~](https://docs.cycling74.com/reference/phasor~/)、[Node for Max](https://docs.cycling74.com/apiref/nodeformax/)。
