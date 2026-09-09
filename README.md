# ADEPS-test

空間音響の数式と結果を、配置図・周波数特性・行列で確認する研究用テスト環境です。日本語／英語のUI、WebGLの配置表示、スピーカー再生系の合成実験、マイクからFOAへの線形符号化、録音済みインパルス応答（IR）の解析を備えています。

**公式のニューラルADEPS・学習済み重み・拡散推論は未実装です。** このプロジェクトは公式実装ではありません。論文の線形符号化を基礎にした比較と、独立したスピーカー再生実験を扱います。手法の対応と未実装範囲はUIの「論文と実装の範囲」、[読解ノート](docs/ADEPS_REVIEW.md)に記載しています。

## ブラウザで使う

[GitHub Pages](https://keigoyoshida7.github.io/ADEPS-test/)では、計算用のPython/WebAssemblyランタイムをブラウザに読み込みます。初回はランタイムと数値ライブラリの取得に時間がかかります。計算・入力ファイルの解析はブラウザ内で実行します。GitHub PagesはPythonサーバーを実行せず、Maxや音声デバイスへ接続しません。

1. 配置図で合成スピーカーの位置を確認します。
2. 再生実験で追加遅延や正則化を変え、再計算します。
3. 調整点と未使用点の誤差を比較します。調整点だけで改善していても、別の場所では悪化する場合があります。
4. マイク画面では、同一平面の配置にしてFOA復元のrank低下を確認できます。
5. IR画面では合成サンプルZIPを読み込んでから、自分で収録したIRの入力形式を確認できます。
6. JSON・CSVで計算条件と結果を保存できます。表示言語を切り替えても数値は変わりません。

公開版の初期配置は、**12 × 9 × 4 mの合成室、12スピーカー、9調整点、6未使用点**です。特定施設の設定・測量値・測定音響は含みません。3D図は座標の表示で、測定された音圧分布ではありません。

## 自分のPCで動かす

Node.js 22.13以降とnpmを用意し、リポジトリのルートで実行します。

```sh
npm ci
npm run dev
```

表示されたローカルURLを開きます。これはブラウザのPython/WebAssemblyで計算するモードで、Pythonの手動インストールやローカル解析サーバーは不要です。ランタイムの初回取得にはネット接続が必要です。

### ローカルPython API・Maxを使う

Python 3.11以降も必要です。macOSでは **`ADEPS-test.command`** を開くと、依存ライブラリを準備し、ローカルPython APIとローカル接続用UIを起動します。初回はライブラリの取得を行います。ランチャーのターミナルでControl-Cを押すと、そのランチャーが起動したサーバーを終了します。MaxのDSP停止はMaxで行ってください。

手動で起動する場合は、まずPython環境を準備します。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

1つ目のターミナルで解析サーバーを起動します。

```sh
.venv/bin/python backend/server.py
```

2つ目のターミナルで、Python APIへ接続するUIを起動します。

```sh
npm run dev:local
```

`dev:local`はブラウザ内計算ではなく、起動済みのPython APIを使います。詳しくは[ローカル接続の手順](public/info/LOCAL_SETUP.md)と[Maxパッチの説明](max/README.md)を参照してください。

## 実装範囲

| 処理 | このプロジェクトで動く範囲 |
|---|---|
| 再生系 | 直接音＋6面の一次反射と機器誤差を合成し、周波数ごとのridge圧力マッチングを計算 |
| マイク → FOA | 既知の伝達行列Vによる線形符号化。合成デモと行列入力 |
| IR | 同期条件を保ったWAV群の応答、到達時刻の目安、任意の目標IRとの比較 |
| ADEPS | 論文との対応を説明。ニューラルモデル、学習、拡散推論は未実装 |
| Max | ローカル版のみ。状態確認、1〜12ch選択、ミュート。DSPと音量はMaxで手動操作 |

再生系の補正は、各周波数で `G = (HᴴH + λI)⁻¹HᴴT` を解く従来の線形処理です。ADEPSの拡散モデルではありません。各列の2ノルム制限は、同時入力時のピークやSPLを保証しません。書き出す複素行列から、実機用の因果FIRフィルターは生成していません。

複素NRMSEは `20 log10(誤差のノルム / 目標のノルム)`。小さいほど良く、0 dBは誤差の大きさが目標と同じ状態です。聴感評価・音圧・連続帯域の積分値ではありません。未使用点を見ながら条件を調整した後は、新しい点で最終評価してください。

マイクの合成デモは自由空間・無指向性・real ACN/N3D・`exp(+ikr·d)`という本試作の規約です。FOA順はW,Y,Z,Xです。論文で公表されていないSTFT条件や規約を再現したとは扱いません。参照のないデータでは復元品質の誤差・coherenceを出しません。SI-SDR・ILD・ICの評価は未実装です。

## IRの入力

ZIP直下に`manifest.json`を置き、`schema: adeps-test-ir-bundle/1`と`speaker_files`を指定します。1つのWAVが1スピーカー、各WAVのチャンネルが測定点です。[テンプレート](public/examples/manifest-template.json)を参照してください。

- 全WAVでサンプルレート・長さ・チャンネル数・時刻原点・レベル基準を合わせます。個別の自動時間合わせは行いません。
- `target_files`は任意。目標がなければ応答と到達の診断だけを表示します。
- 目標がある場合、`training_indices`と`heldout_indices`に重複しない0始まりの点番号を指定します。
- 入力上限はZIP 32 MB、展開後100 MB、観測IR合計300万サンプル、32スピーカー、64測定点です。
- 10%相対ピーク閾値の到達時刻は目安です。収録・スイープ生成・逆畳み込み・厳密な直接音同定は実行しません。

## 開発・検証・公開

```sh
npm run build
npm run test:max
```

Python数値テストは、依存ライブラリを入れた環境で実行します。

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests -v
```

GitHub Pagesへは静的ビルドを配信します。ブラウザ版にローカルAPIやUDPブリッジを公開する構成ではありません。公開画面とローカル版の違い、検証対象は[検証範囲](docs/VALIDATION.md)に記載しています。

画面はモノクロと游明朝体を基本にしています。フォントファイルは同梱せず、端末にない場合は明朝系の代替書体で表示します。

## 出典

- Milstein, Shlezinger, Rafaely. [Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling](https://arxiv.org/abs/2608.24558v2), arXiv:2608.24558v2, 2026.
- [著者のADEUPSリポジトリ：確認したrevision](https://github.com/Amitmils/ADEUPS/tree/5076f163a1f939c297b55a39b2d9d33e2b224a5f)。このrevisionにはREADMEのみがあり、実行可能なモデルや重みを取り込んだ出典ではありません。
- [数値モデル・指標の説明](docs/NUMERICS_REFERENCE.md)
- [BibTeX](public/info/references.bib)
