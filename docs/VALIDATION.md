# ADEPS-test — 検証範囲

この文書は公開版の検証対象と限界を説明します。テストコマンドの実行成功、公開URLの到達、Maxの実機動作は別々に確認する項目です。過去のローカル版の検証件数や施設固有の結果を、公開版の合格記録として引き継ぎません。

## 数値テスト

依存ライブラリを入れたPython環境で、リポジトリのルートから実行します。

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests -v
```

対象は以下です。

- 線形ridge解、相対正則化のスケール不変性、列ノルム制限、rank不足。
- 合成音場の直接音・一次反射・ゲイン・遅延、共通の時刻原点と位相。
- 未使用点の悪化を改善として扱わないこと。
- FOAのACN/N3D成分、球面調和関数、既知モデルでの線形復元、同一平面のrank低下。
- 参照なし、無音、非有限値、形状不一致、入力上限、JSONへの変換。
- IRの離散時間フーリエ変換、相対閾値による到達目安、参照の有無、調整点と評価点の重複拒否。

ブラウザのPython/WebAssembly版でも同じ数値処理を呼びます。代表条件について、ブラウザとローカルPythonの結果を許容誤差内で比較することが実行環境の確認になります。ブラウザ表示だけを確認して数値同等性を主張しません。

## UI・静的公開

```sh
npm run build
```

確認する操作は、JP／EN切替、配置選択・座標編集・再計算、未更新表示、周波数と行列の選択、IR／アレイ入力、JSON／CSV保存です。GitHub Pagesでは、リポジトリ名を含むベースパスで各画面・ワーカー・Pythonソース・ランタイム・ダウンロードリンクが読み込めることを確認します。

初期12 × 9 × 4 m・12音源のモデルは合成データです。図や数値を測定値として表示しません。静的公開版はブラウザ内計算を使用し、Python APIやMaxブリッジの起動を前提にしません。

## Max

```sh
npm run test:max
```

OSC型・範囲・不正パケット、ローカルUDP往復、ポート競合、パッチの初期ゲート／ゲイン、12出力、手動DSP経路を自動テストで検査します。詳細は[Maxの検証範囲](../max/VALIDATION.md)。

この自動テストはMaxアプリでの発音、音声機器、Dante同期、スピーカーの物理配線、聴感や音圧を検証しません。

## 未実装・実機未検証

- 著者のニューラルADEPSモデル・重み・音声/残響学習条件の再現（独自の小型モデルと推論式は実装済み）。
- ILD・ICの評価と論文の公表結果の完全再計算。WAV経路では独自の明示したSI-SDR集計を実装。
- 測定スイープの出力、マイク収録、逆畳み込み。
- 連続帯域の因果FIRフィルター生成、実時間適用、遅延・ヘッドルーム・バイパスの検証。
- 特定の施設の測量、機器設定、測定音響、音質改善。

入力者が申告した測定条件や規約が、実際のデータと一致するかは別途確認が必要です。小さいマイク空間残差や調整点誤差だけでは、空間復元や客席全体の再生が正しいと結論づけません。

## 2026-09-09 verification

- 39 scientific tests pass in native Python and in Node-hosted Pyodide WebAssembly.
- Six complete result comparisons pass, including shapes, strings and nulls. Maximum absolute numeric difference: 4.80e-10 (tolerance 1e-9 + 1e-8 × abs(native value)).
- Five Max codec/UDP/patch tests pass without emitting audio.
- TypeScript check and production build pass.
- Native: Python 3.11.8, NumPy 2.4.6, SciPy 1.17.1. WASM: Pyodide 314.0.6, NumPy 2.4.6, SciPy 1.18.0.
- WASM comparison does not by itself verify browser delivery, WebGL rendering, or physical audio.

## 2026-09-10 neural extension verification

- 53 native scientific tests pass, including 14 new neural/audio checks; the 5 existing Max tests also pass without audio output.
- Full denoiser-through-likelihood derivative agrees with finite differences at sigma .05/.7/20; an additional independent PyTorch autograd comparison differs by at most 1.34e-15.
- Actual Chrome WebAssembly inference is compared with native Python for the same default 150-step run: 9,736 numbers, maximum absolute difference 4.37e-11. Timing and input hashes of platform-specific floating-point observations are excluded. Full record: [neural-verification.json](neural-verification.json).
- Default 512-bin synthetic inference took 2.51 s in this browser test. A .4 s / 16 kHz WAV segment with 150 iterations took 31.51 s. These measurements support offline testing, not live operation.
- The browser-exported comparison ZIP was reopened: all six WAVs have 6,400 samples, four channels, 16 kHz, explicit ACN/N3D or ACN/SN3D, and a common export gain. The result includes checkpoint hash, settings, trace and reference-conditional metrics.
- The synthetic default is worse than linear encoding: complex FOA NRMSE −6.29 dB linear vs −4.44 dB diffusion, coherence .820 vs .714. This is shown as degradation in the UI. It is not a reproduction of the paper's gains.
- JP/EN switching, reference-free STFT import, cancellation/restart and third-position paper-tab navigation pass in Chrome. At 390 px, the page has no horizontal overflow. The local API neural JSON and WAV ZIP routes also pass; the pinned NumPy/SciPy environment passes all 53 scientific tests.
