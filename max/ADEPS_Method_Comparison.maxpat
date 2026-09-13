{
  "patcher": {
    "fileversion": 1,
    "appversion": {
      "major": 9,
      "minor": 0,
      "revision": 0,
      "architecture": "x64",
      "modernui": 1
    },
    "classnamespace": "box",
    "rect": [
      80,
      70,
      1020,
      815
    ],
    "openinpresentation": 1,
    "default_fontname": "Yu Mincho",
    "default_fontsize": 12,
    "bgcolor": [
      0.045,
      0.045,
      0.045,
      1
    ],
    "boxes": [
      {
        "box": {
          "id": "title",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            16,
            980,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 25,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "ADEPS-test / 方式を選んで、同じ音を比較する",
          "presentation": 1,
          "presentation_rect": [
            25,
            16,
            980,
            42
          ]
        }
      },
      {
        "box": {
          "id": "subtitle",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            65,
            980,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "METHOD COMPARISON · 同期FOAバンク → 共通N3Dデコーダー → 12ch / One playhead, one output gain",
          "presentation": 1,
          "presentation_rect": [
            25,
            65,
            980,
            40
          ]
        }
      },
      {
        "box": {
          "id": "stop_all",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            112,
            260,
            33
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 0,
          "outputmode": 1,
          "textcolor": [
            1,
            1,
            1,
            1
          ],
          "bgcolor": [
            0.17,
            0.17,
            0.17,
            1
          ],
          "text": "STOP / MUTE",
          "presentation": 1,
          "presentation_rect": [
            25,
            112,
            260,
            33
          ]
        }
      },
      {
        "box": {
          "id": "muted_default",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            305,
            114,
            540,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "起動・読込・停止時は音量0 / Gain starts at zero",
          "presentation": 1,
          "presentation_rect": [
            305,
            114,
            540,
            40
          ]
        }
      },
      {
        "box": {
          "id": "dsp",
          "maxclass": "ezdac~",
          "numinlets": 2,
          "numoutlets": 0,
          "patching_rect": [
            930,
            111,
            42,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            930,
            111,
            42,
            42
          ]
        }
      },
      {
        "box": {
          "id": "dsp_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            830,
            119,
            100,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "DSP手動 →",
          "presentation": 1,
          "presentation_rect": [
            830,
            119,
            100,
            40
          ]
        }
      },
      {
        "box": {
          "id": "start_node",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            172,
            250,
            33
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 0,
          "outputmode": 1,
          "textcolor": [
            1,
            1,
            1,
            1
          ],
          "bgcolor": [
            0.17,
            0.17,
            0.17,
            1
          ],
          "text": "1  Controllerを開始 / Start",
          "presentation": 1,
          "presentation_rect": [
            25,
            172,
            250,
            33
          ]
        }
      },
      {
        "box": {
          "id": "open_bundled",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            290,
            172,
            295,
            33
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 0,
          "outputmode": 1,
          "textcolor": [
            1,
            1,
            1,
            1
          ],
          "bgcolor": [
            0.17,
            0.17,
            0.17,
            1
          ],
          "text": "2  同梱バンク / Load bundled bank",
          "presentation": 1,
          "presentation_rect": [
            290,
            172,
            295,
            33
          ]
        }
      },
      {
        "box": {
          "id": "open_bank",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            600,
            172,
            225,
            33
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 0,
          "outputmode": 1,
          "textcolor": [
            1,
            1,
            1,
            1
          ],
          "bgcolor": [
            0.17,
            0.17,
            0.17,
            1
          ],
          "text": "別バンクを開く / Other bank",
          "presentation": 1,
          "presentation_rect": [
            600,
            172,
            225,
            33
          ]
        }
      },
      {
        "box": {
          "id": "stop_node",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            840,
            172,
            130,
            33
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 0,
          "outputmode": 1,
          "textcolor": [
            1,
            1,
            1,
            1
          ],
          "bgcolor": [
            0.17,
            0.17,
            0.17,
            1
          ],
          "text": "Controller停止",
          "presentation": 1,
          "presentation_rect": [
            840,
            172,
            130,
            33
          ]
        }
      },
      {
        "box": {
          "id": "node",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            30,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "node.script method-comparison-entry.js @autostart 0 @watch 0"
        }
      },
      {
        "box": {
          "id": "script_start",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "script start"
        }
      },
      {
        "box": {
          "id": "script_stop",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "script stop"
        }
      },
      {
        "box": {
          "id": "load_bundled",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "load_bundled"
        }
      },
      {
        "box": {
          "id": "dialog",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            770,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "opendialog"
        }
      },
      {
        "box": {
          "id": "native_path",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            955,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "conformpath slash boot"
        }
      },
      {
        "box": {
          "id": "load_bank",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend load"
        }
      },
      {
        "box": {
          "id": "status_display",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            217,
            950,
            48
          ],
          "fontname": "Yu Mincho",
          "fontsize": 14,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "Controller stopped / 音声出力は停止中",
          "presentation": 1,
          "presentation_rect": [
            25,
            217,
            950,
            48
          ]
        }
      },
      {
        "box": {
          "id": "status_prepend",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            850,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend set"
        }
      },
      {
        "box": {
          "id": "route",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 11,
          "patching_rect": [
            30,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "route ready mute status duration buffer weights decoder menu selected alive"
        }
      },
      {
        "box": {
          "id": "node_print",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            215,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "print ADEPS-comparison-node"
        }
      },
      {
        "box": {
          "id": "section",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            278,
            950,
            32
          ],
          "fontname": "Yu Mincho",
          "fontsize": 19,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "3  再生方式 / Reconstruction method",
          "presentation": 1,
          "presentation_rect": [
            25,
            278,
            950,
            32
          ]
        }
      },
      {
        "box": {
          "id": "method",
          "maxclass": "umenu",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            320,
            945,
            32
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "items": [
            "reference",
            ",",
            "linear_default",
            ",",
            "linear_tuned",
            ",",
            "linear_noise",
            ",",
            "adeps_current",
            ",",
            "adeps_tuned",
            ",",
            "spatial_only",
            ",",
            "consistency_only",
            ",",
            "plus",
            ",",
            "plus_no_denoiser"
          ],
          "presentation": 1,
          "presentation_rect": [
            25,
            320,
            945,
            32
          ]
        }
      },
      {
        "box": {
          "id": "select_index",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            400,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend select_index"
        }
      },
      {
        "box": {
          "id": "selected_display",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            362,
            945,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 17,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "No bank loaded",
          "presentation": 1,
          "presentation_rect": [
            25,
            362,
            945,
            42
          ]
        }
      },
      {
        "box": {
          "id": "selected_prepend",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            585,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend set"
        }
      },
      {
        "box": {
          "id": "selection_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            411,
            945,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "方式選択だけでは再生しません。再生中は位置を保持して50msで切替えます。/ Selection keeps the shared playhead.",
          "presentation": 1,
          "presentation_rect": [
            25,
            411,
            945,
            42
          ]
        }
      },
      {
        "box": {
          "id": "run",
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            25,
            474,
            35,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            25,
            474,
            35,
            35
          ]
        }
      },
      {
        "box": {
          "id": "run_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            73,
            477,
            250,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "4  LOOP RUN（手動）",
          "presentation": 1,
          "presentation_rect": [
            73,
            477,
            250,
            40
          ]
        }
      },
      {
        "box": {
          "id": "master_gain",
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            370,
            474,
            110,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "minimum": 0,
          "maximum": 1,
          "format": 6,
          "presentation": 1,
          "presentation_rect": [
            370,
            474,
            110,
            35
          ]
        }
      },
      {
        "box": {
          "id": "gain_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            496,
            477,
            475,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "5  共通音量 0–1 / Shared gain",
          "presentation": 1,
          "presentation_rect": [
            496,
            477,
            475,
            40
          ]
        }
      },
      {
        "box": {
          "id": "play_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            523,
            945,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "RUN → MaxのAudio Statusで出力先確認 → DSP → 音量を少しずつ上げる。停止後は再度音量を設定。",
          "presentation": 1,
          "presentation_rect": [
            25,
            523,
            945,
            40
          ]
        }
      },
      {
        "box": {
          "id": "loop_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            563,
            945,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "全方式を同時に読み、選択分だけ出力。末尾250ms無音、外端5ms共通フェード。短片は0.248秒の検証例です。",
          "presentation": 1,
          "presentation_rect": [
            25,
            563,
            945,
            40
          ]
        }
      },
      {
        "box": {
          "id": "output_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            612,
            945,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "出力1–12＝保存プロジェクトID順。物理/Dante番号は別途照合。11/12は以前の画面記録と逆のため確認。",
          "presentation": 1,
          "presentation_rect": [
            25,
            612,
            945,
            42
          ]
        }
      },
      {
        "box": {
          "id": "scope_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            657,
            945,
            42
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "同じ合成観測からの保存済み比較。現地の新録音を推定する処理ではありません。AFCの既存入力にはそのまま接続しないでください。",
          "presentation": 1,
          "presentation_rect": [
            25,
            657,
            945,
            42
          ]
        }
      },
      {
        "box": {
          "id": "meter_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            705,
            945,
            25
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "デコード後（共通音量適用済み）/ Decoded output levels",
          "presentation": 1,
          "presentation_rect": [
            25,
            705,
            945,
            25
          ]
        }
      },
      {
        "box": {
          "id": "meter0",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            25,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            25,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel0",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S1",
          "presentation": 1,
          "presentation_rect": [
            25,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter1",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            104,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            104,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel1",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            104,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S2",
          "presentation": 1,
          "presentation_rect": [
            104,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter2",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            183,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            183,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel2",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            183,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S3",
          "presentation": 1,
          "presentation_rect": [
            183,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter3",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            262,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            262,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel3",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            262,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S4",
          "presentation": 1,
          "presentation_rect": [
            262,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter4",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            341,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            341,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel4",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            341,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S5",
          "presentation": 1,
          "presentation_rect": [
            341,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter5",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            420,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            420,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel5",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            420,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S6",
          "presentation": 1,
          "presentation_rect": [
            420,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter6",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            499,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            499,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel6",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            499,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S7",
          "presentation": 1,
          "presentation_rect": [
            499,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter7",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            578,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            578,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel7",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            578,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S8",
          "presentation": 1,
          "presentation_rect": [
            578,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter8",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            657,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            657,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel8",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            657,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S9",
          "presentation": 1,
          "presentation_rect": [
            657,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter9",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            736,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            736,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel9",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            736,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S10",
          "presentation": 1,
          "presentation_rect": [
            736,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter10",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            815,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            815,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel10",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            815,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S11",
          "presentation": 1,
          "presentation_rect": [
            815,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "meter11",
          "maxclass": "meter~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            894,
            740,
            68,
            14
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            894,
            740,
            68,
            14
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel11",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            894,
            757,
            68,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 11,
          "textcolor": [
            0.92,
            0.92,
            0.92,
            1
          ],
          "text": "S12",
          "presentation": 1,
          "presentation_rect": [
            894,
            757,
            68,
            24
          ]
        }
      },
      {
        "box": {
          "id": "zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "initial_zero",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            955,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loadmess 0"
        }
      },
      {
        "box": {
          "id": "not_ready",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1140,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sel 0"
        }
      },
      {
        "box": {
          "id": "ready_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            912,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "run_stopped",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            30,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sel 0"
        }
      },
      {
        "box": {
          "id": "gain_zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "watchdog_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            400,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "watchdog_cancel",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "stop"
        }
      },
      {
        "box": {
          "id": "watchdog",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            770,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "delay 1500"
        }
      },
      {
        "box": {
          "id": "watchdog_not_ready",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "watchdog_error",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "set Controller heartbeat lost / STOPPED"
        }
      },
      {
        "box": {
          "id": "period",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            974,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+ 250."
        }
      },
      {
        "box": {
          "id": "frequency",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "expr 1000. / $f1"
        }
      },
      {
        "box": {
          "id": "running_frequency",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "* 0."
        }
      },
      {
        "box": {
          "id": "phasor",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "phasor~ 0. @phaseoffset 0."
        }
      },
      {
        "box": {
          "id": "position_ms",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 1."
        }
      },
      {
        "box": {
          "id": "run_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            770,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i i"
        }
      },
      {
        "box": {
          "id": "restart_select",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            955,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sel 1"
        }
      },
      {
        "box": {
          "id": "restart_phase",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0."
        }
      },
      {
        "box": {
          "id": "run_ramp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1036,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 10"
        }
      },
      {
        "box": {
          "id": "run_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "fade_in",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "/~ 5."
        }
      },
      {
        "box": {
          "id": "remaining_ms",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "!-~ 0."
        }
      },
      {
        "box": {
          "id": "fade_out",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "/~ 5."
        }
      },
      {
        "box": {
          "id": "fade_minimum",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "minimum~"
        }
      },
      {
        "box": {
          "id": "envelope",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip~ 0. 1."
        }
      },
      {
        "box": {
          "id": "gain_clip",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip 0. 1."
        }
      },
      {
        "box": {
          "id": "gain_pack",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1098,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 100"
        }
      },
      {
        "box": {
          "id": "gain_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "envelope_run",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "master_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer_route",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 11,
          "patching_rect": [
            585,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "route 0 1 2 3 4 5 6 7 8 9"
        }
      },
      {
        "box": {
          "id": "weights",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 10,
          "patching_rect": [
            770,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "unpack 0. 0. 0. 0. 0. 0. 0. 0. 0. 0."
        }
      },
      {
        "box": {
          "id": "buffer_confirm",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "js method-comparison-buffer.js #0"
        }
      },
      {
        "box": {
          "id": "buffer0",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1140,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-0 0 4"
        }
      },
      {
        "box": {
          "id": "play0",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            1325,
            1160,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-0 4"
        }
      },
      {
        "box": {
          "id": "loaded0",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 0"
        }
      },
      {
        "box": {
          "id": "weight_pack0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            400,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted0_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted0_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted0_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted0_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer1",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1325,
            1222,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-1 0 4"
        }
      },
      {
        "box": {
          "id": "play1",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            30,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-1 4"
        }
      },
      {
        "box": {
          "id": "loaded1",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 1"
        }
      },
      {
        "box": {
          "id": "weight_pack1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            585,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted1_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted1_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted1_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted1_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1284,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer2",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-2 0 4"
        }
      },
      {
        "box": {
          "id": "play2",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            215,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-2 4"
        }
      },
      {
        "box": {
          "id": "loaded2",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 2"
        }
      },
      {
        "box": {
          "id": "weight_pack2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            770,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted2_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted2_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted2_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1346,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted2_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer3",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            215,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-3 0 4"
        }
      },
      {
        "box": {
          "id": "play3",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            400,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-3 4"
        }
      },
      {
        "box": {
          "id": "loaded3",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 3"
        }
      },
      {
        "box": {
          "id": "weight_pack3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            955,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted3_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted3_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1408,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted3_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted3_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer4",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            400,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-4 0 4"
        }
      },
      {
        "box": {
          "id": "play4",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            585,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-4 4"
        }
      },
      {
        "box": {
          "id": "loaded4",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 4"
        }
      },
      {
        "box": {
          "id": "weight_pack4",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight4",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            1140,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted4_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1470,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted4_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted4_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted4_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer5",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            585,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-5 0 4"
        }
      },
      {
        "box": {
          "id": "play5",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            770,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-5 4"
        }
      },
      {
        "box": {
          "id": "loaded5",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 5"
        }
      },
      {
        "box": {
          "id": "weight_pack5",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight5",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            1325,
            1532,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted5_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted5_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted5_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted5_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer6",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            770,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-6 0 4"
        }
      },
      {
        "box": {
          "id": "play6",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            955,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-6 4"
        }
      },
      {
        "box": {
          "id": "loaded6",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 6"
        }
      },
      {
        "box": {
          "id": "weight_pack6",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1594,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight6",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted6_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted6_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted6_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted6_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer7",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            955,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-7 0 4"
        }
      },
      {
        "box": {
          "id": "play7",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            1140,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-7 4"
        }
      },
      {
        "box": {
          "id": "loaded7",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1656,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 7"
        }
      },
      {
        "box": {
          "id": "weight_pack7",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight7",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            215,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted7_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted7_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted7_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted7_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer8",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1140,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-8 0 4"
        }
      },
      {
        "box": {
          "id": "play8",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            1325,
            1718,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-8 4"
        }
      },
      {
        "box": {
          "id": "loaded8",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 8"
        }
      },
      {
        "box": {
          "id": "weight_pack8",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight8",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            400,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted8_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted8_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted8_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted8_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "buffer9",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1325,
            1780,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "buffer~ #0-cmp-9 0 4"
        }
      },
      {
        "box": {
          "id": "play9",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 5,
          "patching_rect": [
            30,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "play~ #0-cmp-9 4"
        }
      },
      {
        "box": {
          "id": "loaded9",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loaded 9"
        }
      },
      {
        "box": {
          "id": "weight_pack9",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 50"
        }
      },
      {
        "box": {
          "id": "weight9",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            585,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "weighted9_0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted9_1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted9_2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "weighted9_3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1842,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "decoder",
          "maxclass": "newobj",
          "numinlets": 4,
          "numoutlets": 13,
          "patching_rect": [
            30,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "matrix~ 4 12 0. @ramp 50"
        }
      },
      {
        "box": {
          "id": "dac",
          "maxclass": "newobj",
          "numinlets": 12,
          "numoutlets": 0,
          "patching_rect": [
            215,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "dac~ 1 2 3 4 5 6 7 8 9 10 11 12"
        }
      },
      {
        "box": {
          "id": "sum0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            400,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~ 0."
        }
      },
      {
        "box": {
          "id": "foa0",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            585,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "sum1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            770,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~ 0."
        }
      },
      {
        "box": {
          "id": "foa1",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            955,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "sum2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1140,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~ 0."
        }
      },
      {
        "box": {
          "id": "foa2",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1325,
            1904,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "sum3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1966,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~ 0."
        }
      },
      {
        "box": {
          "id": "foa3",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            215,
            1966,
            178,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "start_node",
            0
          ],
          "destination": [
            "script_start",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "script_start",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "open_bundled",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "open_bundled",
            0
          ],
          "destination": [
            "load_bundled",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "load_bundled",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_node",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_node",
            0
          ],
          "destination": [
            "script_stop",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "script_stop",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "open_bank",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "open_bank",
            0
          ],
          "destination": [
            "dialog",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "dialog",
            0
          ],
          "destination": [
            "native_path",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "native_path",
            0
          ],
          "destination": [
            "load_bank",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "load_bank",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "status_prepend",
            0
          ],
          "destination": [
            "status_display",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "node",
            0
          ],
          "destination": [
            "route",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            2
          ],
          "destination": [
            "status_prepend",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "node",
            1
          ],
          "destination": [
            "node_print",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "method",
            0
          ],
          "destination": [
            "select_index",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "select_index",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            7
          ],
          "destination": [
            "method",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            8
          ],
          "destination": [
            "selected_prepend",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "selected_prepend",
            0
          ],
          "destination": [
            "selected_display",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "initial_zero",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_all",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            1
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero",
            0
          ],
          "destination": [
            "run",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero",
            0
          ],
          "destination": [
            "master_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            0
          ],
          "destination": [
            "not_ready",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "not_ready",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            0
          ],
          "destination": [
            "ready_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run",
            0
          ],
          "destination": [
            "ready_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run",
            0
          ],
          "destination": [
            "run_stopped",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run_stopped",
            0
          ],
          "destination": [
            "gain_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "gain_zero",
            0
          ],
          "destination": [
            "master_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            9
          ],
          "destination": [
            "watchdog_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog_order",
            1
          ],
          "destination": [
            "watchdog_cancel",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog_cancel",
            0
          ],
          "destination": [
            "watchdog",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog_order",
            0
          ],
          "destination": [
            "watchdog",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog",
            0
          ],
          "destination": [
            "zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog",
            0
          ],
          "destination": [
            "watchdog_not_ready",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog_not_ready",
            0
          ],
          "destination": [
            "ready_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog",
            0
          ],
          "destination": [
            "watchdog_error",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "watchdog_error",
            0
          ],
          "destination": [
            "status_display",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            3
          ],
          "destination": [
            "period",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "period",
            0
          ],
          "destination": [
            "frequency",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "frequency",
            0
          ],
          "destination": [
            "running_frequency",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ready_gate",
            0
          ],
          "destination": [
            "run_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run_order",
            1
          ],
          "destination": [
            "restart_select",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "restart_select",
            0
          ],
          "destination": [
            "restart_phase",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "restart_phase",
            0
          ],
          "destination": [
            "phasor",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run_order",
            0
          ],
          "destination": [
            "running_frequency",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "running_frequency",
            0
          ],
          "destination": [
            "phasor",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "phasor",
            0
          ],
          "destination": [
            "position_ms",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "period",
            0
          ],
          "destination": [
            "position_ms",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ready_gate",
            0
          ],
          "destination": [
            "run_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run_ramp",
            0
          ],
          "destination": [
            "run_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero",
            0
          ],
          "destination": [
            "run_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero",
            0
          ],
          "destination": [
            "running_frequency",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "fade_in",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "remaining_ms",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            3
          ],
          "destination": [
            "remaining_ms",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "remaining_ms",
            0
          ],
          "destination": [
            "fade_out",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "fade_in",
            0
          ],
          "destination": [
            "fade_minimum",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "fade_out",
            0
          ],
          "destination": [
            "fade_minimum",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "fade_minimum",
            0
          ],
          "destination": [
            "envelope",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "master_gain",
            0
          ],
          "destination": [
            "gain_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "gain_clip",
            0
          ],
          "destination": [
            "gain_pack",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "gain_pack",
            0
          ],
          "destination": [
            "gain_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "envelope",
            0
          ],
          "destination": [
            "envelope_run",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "run_signal",
            0
          ],
          "destination": [
            "envelope_run",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "envelope_run",
            0
          ],
          "destination": [
            "master_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "gain_signal",
            0
          ],
          "destination": [
            "master_signal",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            4
          ],
          "destination": [
            "buffer_route",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            5
          ],
          "destination": [
            "weights",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_confirm",
            0
          ],
          "destination": [
            "node",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            0
          ],
          "destination": [
            "buffer0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer0",
            1
          ],
          "destination": [
            "loaded0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded0",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            0
          ],
          "destination": [
            "weight_pack0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack0",
            0
          ],
          "destination": [
            "weight0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play0",
            0
          ],
          "destination": [
            "weighted0_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight0",
            0
          ],
          "destination": [
            "weighted0_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play0",
            1
          ],
          "destination": [
            "weighted0_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight0",
            0
          ],
          "destination": [
            "weighted0_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play0",
            2
          ],
          "destination": [
            "weighted0_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight0",
            0
          ],
          "destination": [
            "weighted0_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play0",
            3
          ],
          "destination": [
            "weighted0_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight0",
            0
          ],
          "destination": [
            "weighted0_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            1
          ],
          "destination": [
            "buffer1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer1",
            1
          ],
          "destination": [
            "loaded1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded1",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            1
          ],
          "destination": [
            "weight_pack1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack1",
            0
          ],
          "destination": [
            "weight1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play1",
            0
          ],
          "destination": [
            "weighted1_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight1",
            0
          ],
          "destination": [
            "weighted1_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play1",
            1
          ],
          "destination": [
            "weighted1_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight1",
            0
          ],
          "destination": [
            "weighted1_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play1",
            2
          ],
          "destination": [
            "weighted1_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight1",
            0
          ],
          "destination": [
            "weighted1_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play1",
            3
          ],
          "destination": [
            "weighted1_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight1",
            0
          ],
          "destination": [
            "weighted1_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            2
          ],
          "destination": [
            "buffer2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer2",
            1
          ],
          "destination": [
            "loaded2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded2",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            2
          ],
          "destination": [
            "weight_pack2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack2",
            0
          ],
          "destination": [
            "weight2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play2",
            0
          ],
          "destination": [
            "weighted2_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight2",
            0
          ],
          "destination": [
            "weighted2_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play2",
            1
          ],
          "destination": [
            "weighted2_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight2",
            0
          ],
          "destination": [
            "weighted2_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play2",
            2
          ],
          "destination": [
            "weighted2_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight2",
            0
          ],
          "destination": [
            "weighted2_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play2",
            3
          ],
          "destination": [
            "weighted2_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight2",
            0
          ],
          "destination": [
            "weighted2_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            3
          ],
          "destination": [
            "buffer3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer3",
            1
          ],
          "destination": [
            "loaded3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded3",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            3
          ],
          "destination": [
            "weight_pack3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack3",
            0
          ],
          "destination": [
            "weight3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play3",
            0
          ],
          "destination": [
            "weighted3_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight3",
            0
          ],
          "destination": [
            "weighted3_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play3",
            1
          ],
          "destination": [
            "weighted3_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight3",
            0
          ],
          "destination": [
            "weighted3_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play3",
            2
          ],
          "destination": [
            "weighted3_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight3",
            0
          ],
          "destination": [
            "weighted3_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play3",
            3
          ],
          "destination": [
            "weighted3_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight3",
            0
          ],
          "destination": [
            "weighted3_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            4
          ],
          "destination": [
            "buffer4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer4",
            1
          ],
          "destination": [
            "loaded4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded4",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            4
          ],
          "destination": [
            "weight_pack4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack4",
            0
          ],
          "destination": [
            "weight4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play4",
            0
          ],
          "destination": [
            "weighted4_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight4",
            0
          ],
          "destination": [
            "weighted4_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play4",
            1
          ],
          "destination": [
            "weighted4_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight4",
            0
          ],
          "destination": [
            "weighted4_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play4",
            2
          ],
          "destination": [
            "weighted4_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight4",
            0
          ],
          "destination": [
            "weighted4_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play4",
            3
          ],
          "destination": [
            "weighted4_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight4",
            0
          ],
          "destination": [
            "weighted4_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            5
          ],
          "destination": [
            "buffer5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer5",
            1
          ],
          "destination": [
            "loaded5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded5",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            5
          ],
          "destination": [
            "weight_pack5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack5",
            0
          ],
          "destination": [
            "weight5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play5",
            0
          ],
          "destination": [
            "weighted5_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight5",
            0
          ],
          "destination": [
            "weighted5_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play5",
            1
          ],
          "destination": [
            "weighted5_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight5",
            0
          ],
          "destination": [
            "weighted5_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play5",
            2
          ],
          "destination": [
            "weighted5_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight5",
            0
          ],
          "destination": [
            "weighted5_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play5",
            3
          ],
          "destination": [
            "weighted5_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight5",
            0
          ],
          "destination": [
            "weighted5_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            6
          ],
          "destination": [
            "buffer6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer6",
            1
          ],
          "destination": [
            "loaded6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded6",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            6
          ],
          "destination": [
            "weight_pack6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack6",
            0
          ],
          "destination": [
            "weight6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play6",
            0
          ],
          "destination": [
            "weighted6_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight6",
            0
          ],
          "destination": [
            "weighted6_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play6",
            1
          ],
          "destination": [
            "weighted6_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight6",
            0
          ],
          "destination": [
            "weighted6_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play6",
            2
          ],
          "destination": [
            "weighted6_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight6",
            0
          ],
          "destination": [
            "weighted6_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play6",
            3
          ],
          "destination": [
            "weighted6_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight6",
            0
          ],
          "destination": [
            "weighted6_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            7
          ],
          "destination": [
            "buffer7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer7",
            1
          ],
          "destination": [
            "loaded7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded7",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            7
          ],
          "destination": [
            "weight_pack7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack7",
            0
          ],
          "destination": [
            "weight7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play7",
            0
          ],
          "destination": [
            "weighted7_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight7",
            0
          ],
          "destination": [
            "weighted7_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play7",
            1
          ],
          "destination": [
            "weighted7_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight7",
            0
          ],
          "destination": [
            "weighted7_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play7",
            2
          ],
          "destination": [
            "weighted7_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight7",
            0
          ],
          "destination": [
            "weighted7_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play7",
            3
          ],
          "destination": [
            "weighted7_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight7",
            0
          ],
          "destination": [
            "weighted7_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            8
          ],
          "destination": [
            "buffer8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer8",
            1
          ],
          "destination": [
            "loaded8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded8",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            8
          ],
          "destination": [
            "weight_pack8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack8",
            0
          ],
          "destination": [
            "weight8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play8",
            0
          ],
          "destination": [
            "weighted8_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight8",
            0
          ],
          "destination": [
            "weighted8_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play8",
            1
          ],
          "destination": [
            "weighted8_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight8",
            0
          ],
          "destination": [
            "weighted8_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play8",
            2
          ],
          "destination": [
            "weighted8_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight8",
            0
          ],
          "destination": [
            "weighted8_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play8",
            3
          ],
          "destination": [
            "weighted8_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight8",
            0
          ],
          "destination": [
            "weighted8_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer_route",
            9
          ],
          "destination": [
            "buffer9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "position_ms",
            0
          ],
          "destination": [
            "play9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "buffer9",
            1
          ],
          "destination": [
            "loaded9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "loaded9",
            0
          ],
          "destination": [
            "buffer_confirm",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weights",
            9
          ],
          "destination": [
            "weight_pack9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight_pack9",
            0
          ],
          "destination": [
            "weight9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play9",
            0
          ],
          "destination": [
            "weighted9_0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight9",
            0
          ],
          "destination": [
            "weighted9_0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play9",
            1
          ],
          "destination": [
            "weighted9_1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight9",
            0
          ],
          "destination": [
            "weighted9_1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play9",
            2
          ],
          "destination": [
            "weighted9_2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight9",
            0
          ],
          "destination": [
            "weighted9_2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "play9",
            3
          ],
          "destination": [
            "weighted9_3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weight9",
            0
          ],
          "destination": [
            "weighted9_3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "route",
            6
          ],
          "destination": [
            "decoder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted0_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted1_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted2_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted3_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted4_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted5_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted6_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted7_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted8_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted9_0",
            0
          ],
          "destination": [
            "sum0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sum0",
            0
          ],
          "destination": [
            "foa0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "master_signal",
            0
          ],
          "destination": [
            "foa0",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "foa0",
            0
          ],
          "destination": [
            "decoder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted0_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted1_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted2_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted3_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted4_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted5_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted6_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted7_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted8_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted9_1",
            0
          ],
          "destination": [
            "sum1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sum1",
            0
          ],
          "destination": [
            "foa1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "master_signal",
            0
          ],
          "destination": [
            "foa1",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "foa1",
            0
          ],
          "destination": [
            "decoder",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted0_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted1_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted2_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted3_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted4_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted5_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted6_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted7_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted8_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted9_2",
            0
          ],
          "destination": [
            "sum2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sum2",
            0
          ],
          "destination": [
            "foa2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "master_signal",
            0
          ],
          "destination": [
            "foa2",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "foa2",
            0
          ],
          "destination": [
            "decoder",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted0_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted1_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted2_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted3_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted4_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted5_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted6_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted7_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted8_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "weighted9_3",
            0
          ],
          "destination": [
            "sum3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sum3",
            0
          ],
          "destination": [
            "foa3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "master_signal",
            0
          ],
          "destination": [
            "foa3",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "foa3",
            0
          ],
          "destination": [
            "decoder",
            3
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            0
          ],
          "destination": [
            "dac",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            0
          ],
          "destination": [
            "meter0",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            1
          ],
          "destination": [
            "dac",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            1
          ],
          "destination": [
            "meter1",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            2
          ],
          "destination": [
            "dac",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            2
          ],
          "destination": [
            "meter2",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            3
          ],
          "destination": [
            "dac",
            3
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            3
          ],
          "destination": [
            "meter3",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            4
          ],
          "destination": [
            "dac",
            4
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            4
          ],
          "destination": [
            "meter4",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            5
          ],
          "destination": [
            "dac",
            5
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            5
          ],
          "destination": [
            "meter5",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            6
          ],
          "destination": [
            "dac",
            6
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            6
          ],
          "destination": [
            "meter6",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            7
          ],
          "destination": [
            "dac",
            7
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            7
          ],
          "destination": [
            "meter7",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            8
          ],
          "destination": [
            "dac",
            8
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            8
          ],
          "destination": [
            "meter8",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            9
          ],
          "destination": [
            "dac",
            9
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            9
          ],
          "destination": [
            "meter9",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            10
          ],
          "destination": [
            "dac",
            10
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            10
          ],
          "destination": [
            "meter10",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            11
          ],
          "destination": [
            "dac",
            11
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "decoder",
            11
          ],
          "destination": [
            "meter11",
            0
          ]
        }
      }
    ]
  }
}
