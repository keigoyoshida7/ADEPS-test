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
      60,
      60,
      1140,
      970
    ],
    "openinpresentation": 1,
    "default_fontname": "Yu Mincho",
    "default_fontsize": 12,
    "bgcolor": [
      0.025,
      0.025,
      0.025,
      1
    ],
    "editing_bgcolor": [
      0.08,
      0.08,
      0.08,
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
            15,
            1090,
            38
          ],
          "fontname": "Yu Mincho",
          "fontsize": 25,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "ADEPS-test / 音を用意する・収録する・比較する",
          "presentation": 1,
          "presentation_rect": [
            25,
            15,
            1090,
            38
          ]
        }
      },
      {
        "box": {
          "id": "intro",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            58,
            1080,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "Max 9 standard objects / 音声はWAVで手動受け渡し。Webへの音声送信・リアルタイム推論は行いません。",
          "presentation": 1,
          "presentation_rect": [
            25,
            58,
            1080,
            35
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
            98,
            250,
            30
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
          "text": "STOP ALL / MUTE",
          "presentation": 1,
          "presentation_rect": [
            25,
            98,
            250,
            30
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
            1020,
            96,
            40,
            40
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            1020,
            96,
            40,
            40
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
            800,
            101,
            210,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "DSPはここで手動操作 →",
          "presentation": 1,
          "presentation_rect": [
            800,
            101,
            210,
            35
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
            30,
            1020,
            170,
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
            210,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loadmess 0"
        }
      },
      {
        "box": {
          "id": "source_title",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            147,
            1060,
            30
          ],
          "fontname": "Yu Mincho",
          "fontsize": 18,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "01  元音源 / マイクなしの検証にも使用",
          "presentation": 1,
          "presentation_rect": [
            25,
            147,
            1060,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_mode",
          "maxclass": "umenu",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            188,
            215,
            28
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "items": [
            "OFF",
            ",",
            "Mono WAV",
            ",",
            "Pink noise",
            ",",
            "Log sweep 20Hz–20kHz",
            ",",
            "Short pink burst 100ms"
          ],
          "presentation": 1,
          "presentation_rect": [
            25,
            188,
            215,
            28
          ]
        }
      },
      {
        "box": {
          "id": "source_open",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            255,
            188,
            170,
            30
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
          "text": "Mono WAVを開く",
          "presentation": 1,
          "presentation_rect": [
            255,
            188,
            170,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_run",
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            455,
            189,
            27,
            27
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            455,
            189,
            27,
            27
          ]
        }
      },
      {
        "box": {
          "id": "source_run_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            490,
            191,
            140,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "SOURCE RUN",
          "presentation": 1,
          "presentation_rect": [
            490,
            191,
            140,
            35
          ]
        }
      },
      {
        "box": {
          "id": "source_trigger",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            640,
            188,
            210,
            30
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
          "text": "Sweep / burstを1回",
          "presentation": 1,
          "presentation_rect": [
            640,
            188,
            210,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            225,
            1070,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "Mono WAV＝声・音楽。Sweep＝8秒、burst＝100ms。生成音はRUNを入れた後にトリガー。選択変更で停止します。",
          "presentation": 1,
          "presentation_rect": [
            25,
            225,
            1070,
            35
          ]
        }
      },
      {
        "box": {
          "id": "source_select",
          "maxclass": "newobj",
          "numinlets": 5,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "selector~ 4 0"
        }
      },
      {
        "box": {
          "id": "source_file",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            570,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sfplay~ 1"
        }
      },
      {
        "box": {
          "id": "pink",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pink~"
        }
      },
      {
        "box": {
          "id": "source_clip",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip~ -1. 1."
        }
      },
      {
        "box": {
          "id": "source_run_ramp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1020,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 20"
        }
      },
      {
        "box": {
          "id": "source_run_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "source_gated",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "mode_change",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            390,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i b"
        }
      },
      {
        "box": {
          "id": "source_stop",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "mono_selected",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "== 1"
        }
      },
      {
        "box": {
          "id": "file_start_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "file_end_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1085,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "file_open_message",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "open"
        }
      },
      {
        "box": {
          "id": "source_run_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            210,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i i"
        }
      },
      {
        "box": {
          "id": "source_arm_eof",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            390,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sel 1"
        }
      },
      {
        "box": {
          "id": "source_eof_once",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "onebang 0"
        }
      },
      {
        "box": {
          "id": "source_open_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            750,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "sweep_phase",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            930,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "sweep_hz",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1150,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "expr~ 20. * exp(6.907755278982137 * $v1)"
        }
      },
      {
        "box": {
          "id": "sweep_osc",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "cycle~ 20."
        }
      },
      {
        "box": {
          "id": "sweep_env",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            210,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "sweep_audio",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "burst_env",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            570,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "burst_audio",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "test_trigger",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            930,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b b"
        }
      },
      {
        "box": {
          "id": "sweep_ramp",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1215,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0., 1. 8000"
        }
      },
      {
        "box": {
          "id": "sweep_envelope",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0., 1. 20 1. 7960 0. 20"
        }
      },
      {
        "box": {
          "id": "burst_envelope",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0., 1. 10 1. 80 0. 10"
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
            270,
            420,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "会場へ出す時だけ：論理出力 0=閉 / 1–12",
          "presentation": 1,
          "presentation_rect": [
            25,
            270,
            420,
            35
          ]
        }
      },
      {
        "box": {
          "id": "output_channel",
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            450,
            269,
            60,
            28
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "minimum": 0,
          "maximum": 12,
          "presentation": 1,
          "presentation_rect": [
            450,
            269,
            60,
            28
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
            550,
            273,
            230,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "OUTPUT GAIN 0–0.030",
          "presentation": 1,
          "presentation_rect": [
            550,
            273,
            230,
            35
          ]
        }
      },
      {
        "box": {
          "id": "output_gain",
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            790,
            269,
            85,
            28
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "minimum": 0,
          "maximum": 0.03,
          "format": 6,
          "presentation": 1,
          "presentation_rect": [
            790,
            269,
            85,
            28
          ]
        }
      },
      {
        "box": {
          "id": "output_gain_clip",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip 0. 0.03"
        }
      },
      {
        "box": {
          "id": "output_gain_ramp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 100"
        }
      },
      {
        "box": {
          "id": "output_gain_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            750,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "output_hint",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            309,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "論理出力はDante番号ではありません。Audio Statusで対応確認。マイクなしで保存するだけなら出力0・GAIN 0で使えます。",
          "presentation": 1,
          "presentation_rect": [
            25,
            309,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "output_channel_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            930,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i b"
        }
      },
      {
        "box": {
          "id": "output_gain_zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1280,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0."
        }
      },
      {
        "box": {
          "id": "output_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 12,
          "patching_rect": [
            30,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate~ 12 0"
        }
      },
      {
        "box": {
          "id": "output_amp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "output_dac",
          "maxclass": "newobj",
          "numinlets": 12,
          "numoutlets": 0,
          "patching_rect": [
            390,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "dac~ 1 2 3 4 5 6 7 8 9 10 11 12"
        }
      },
      {
        "box": {
          "id": "record_title",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            367,
            1060,
            30
          ],
          "fontname": "Yu Mincho",
          "fontsize": 18,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "02  WAVを保存 / 保存先を選び、録音 → SOURCE RUN → 停止",
          "presentation": 1,
          "presentation_rect": [
            25,
            367,
            1060,
            30
          ]
        }
      },
      {
        "box": {
          "id": "samptype_init",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "loadmess samptype int24"
        }
      },
      {
        "box": {
          "id": "source_capture_choose",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            411,
            230,
            30
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
          "text": "元音源 / mono 保存先…",
          "presentation": 1,
          "presentation_rect": [
            25,
            411,
            230,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_start",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            275,
            411,
            150,
            30
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
          "text": "録音 START",
          "presentation": 1,
          "presentation_rect": [
            275,
            411,
            150,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_stop",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            440,
            411,
            150,
            30
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
          "text": "停止 / CLOSE",
          "presentation": 1,
          "presentation_rect": [
            440,
            411,
            150,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_elapsed",
          "maxclass": "number~",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            875,
            411,
            100,
            30
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 2,
          "presentation": 1,
          "presentation_rect": [
            875,
            411,
            100,
            30
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_time_label",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            987,
            414,
            100,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "経過 ms",
          "presentation": 1,
          "presentation_rect": [
            987,
            414,
            100,
            35
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_path",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            25,
            447,
            1050,
            25
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "保存先未選択 / .wav を指定",
          "presentation": 1,
          "presentation_rect": [
            25,
            447,
            1050,
            25
          ]
        }
      },
      {
        "box": {
          "id": "source_capture_dialog",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            750,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "savedialog WAVE"
        }
      },
      {
        "box": {
          "id": "source_capture_path_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            930,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b s s"
        }
      },
      {
        "box": {
          "id": "source_capture_show_path",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1345,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend set"
        }
      },
      {
        "box": {
          "id": "source_capture_wave",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "append wave"
        }
      },
      {
        "box": {
          "id": "source_capture_open",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend open"
        }
      },
      {
        "box": {
          "id": "source_capture_recorder",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sfrecord~ 1"
        }
      },
      {
        "box": {
          "id": "source_capture_one",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "1"
        }
      },
      {
        "box": {
          "id": "source_capture_zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "source_capture_ready",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "1"
        }
      },
      {
        "box": {
          "id": "source_capture_ready_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1410,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "source_capture_choose_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "array_capture_choose",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            495,
            230,
            30
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
          "text": "マイク / raw 19ch 保存先…",
          "presentation": 1,
          "presentation_rect": [
            25,
            495,
            230,
            30
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_start",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            275,
            495,
            150,
            30
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
          "text": "録音 START",
          "presentation": 1,
          "presentation_rect": [
            275,
            495,
            150,
            30
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_stop",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            440,
            495,
            150,
            30
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
          "text": "停止 / CLOSE",
          "presentation": 1,
          "presentation_rect": [
            440,
            495,
            150,
            30
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_elapsed",
          "maxclass": "number~",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            875,
            495,
            100,
            30
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "mode": 2,
          "presentation": 1,
          "presentation_rect": [
            875,
            495,
            100,
            30
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_time_label",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            987,
            498,
            100,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "経過 ms",
          "presentation": 1,
          "presentation_rect": [
            987,
            498,
            100,
            35
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_path",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            25,
            531,
            1050,
            25
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "保存先未選択 / .wav を指定",
          "presentation": 1,
          "presentation_rect": [
            25,
            531,
            1050,
            25
          ]
        }
      },
      {
        "box": {
          "id": "array_capture_dialog",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            210,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "savedialog WAVE"
        }
      },
      {
        "box": {
          "id": "array_capture_path_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            390,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b s s"
        }
      },
      {
        "box": {
          "id": "array_capture_show_path",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend set"
        }
      },
      {
        "box": {
          "id": "array_capture_wave",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "append wave"
        }
      },
      {
        "box": {
          "id": "array_capture_open",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "prepend open"
        }
      },
      {
        "box": {
          "id": "array_capture_recorder",
          "maxclass": "newobj",
          "numinlets": 19,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1475,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sfrecord~ 19"
        }
      },
      {
        "box": {
          "id": "array_capture_one",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "1"
        }
      },
      {
        "box": {
          "id": "array_capture_zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "array_capture_ready",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "1"
        }
      },
      {
        "box": {
          "id": "array_capture_ready_gate",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "array_capture_choose_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            750,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "array_adc",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 19,
          "patching_rect": [
            930,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "adc~ 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19"
        }
      },
      {
        "box": {
          "id": "both_record",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            625,
            411,
            225,
            30
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
          "text": "両方の録音 START",
          "presentation": 1,
          "presentation_rect": [
            625,
            411,
            225,
            30
          ]
        }
      },
      {
        "box": {
          "id": "both_record_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            1110,
            1540,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "record_hint",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            575,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "保存はPCM24bit・現在のDSPサンプルレート。停止後は毎回保存先を選び直す。raw入力1–19は音声ドライバで現地照合。",
          "presentation": 1,
          "presentation_rect": [
            25,
            575,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "clock_hint",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            611,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "19ch内は同じ録音処理。再生機器とUSBマイクの共通クロックは保証しません。元mono音源は実空間のFOA正解ではありません。",
          "presentation": 1,
          "presentation_rect": [
            25,
            611,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "ab_title",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            660,
            1080,
            30
          ],
          "fontname": "Yu Mincho",
          "fontsize": 18,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "03  オフライン比較 / Webで書き出した同じテストのFOA 4ch WAV",
          "presentation": 1,
          "presentation_rect": [
            25,
            660,
            1080,
            30
          ]
        }
      },
      {
        "box": {
          "id": "linear_open",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            25,
            705,
            210,
            30
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
          "text": "OFF / Linear WAV…",
          "presentation": 1,
          "presentation_rect": [
            25,
            705,
            210,
            30
          ]
        }
      },
      {
        "box": {
          "id": "enhanced_open",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            250,
            705,
            230,
            30
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
          "text": "ON / Enhanced WAV…",
          "presentation": 1,
          "presentation_rect": [
            250,
            705,
            230,
            30
          ]
        }
      },
      {
        "box": {
          "id": "ab_start",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            495,
            705,
            190,
            30
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
          "text": "A+B 同時 START",
          "presentation": 1,
          "presentation_rect": [
            495,
            705,
            190,
            30
          ]
        }
      },
      {
        "box": {
          "id": "ab_stop",
          "maxclass": "textbutton",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            700,
            705,
            160,
            30
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
          "text": "A+B STOP",
          "presentation": 1,
          "presentation_rect": [
            700,
            705,
            160,
            30
          ]
        }
      },
      {
        "box": {
          "id": "ab_mix",
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [
            895,
            705,
            28,
            28
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            895,
            705,
            28,
            28
          ]
        }
      },
      {
        "box": {
          "id": "ab_mix_label",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            933,
            708,
            170,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "ON = Enhanced",
          "presentation": 1,
          "presentation_rect": [
            933,
            708,
            170,
            35
          ]
        }
      },
      {
        "box": {
          "id": "ab_gain_label",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            755,
            265,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "FOA BUS GAIN 0–0.030",
          "presentation": 1,
          "presentation_rect": [
            25,
            755,
            265,
            35
          ]
        }
      },
      {
        "box": {
          "id": "ab_gain",
          "maxclass": "flonum",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            290,
            752,
            85,
            28
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "minimum": 0,
          "maximum": 0.03,
          "format": 6,
          "presentation": 1,
          "presentation_rect": [
            290,
            752,
            85,
            28
          ]
        }
      },
      {
        "box": {
          "id": "ab_gain_clip",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip 0. 0.03"
        }
      },
      {
        "box": {
          "id": "ab_gain_ramp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 100"
        }
      },
      {
        "box": {
          "id": "ab_gain_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            390,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "ab_warning",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            410,
            755,
            685,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "FOA = ACN/SN3D / W,Y,Z,X。4本をスピーカーへ直結しないでください。",
          "presentation": 1,
          "presentation_rect": [
            410,
            755,
            685,
            35
          ]
        }
      },
      {
        "box": {
          "id": "ab_bus_note",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            797,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "receive~ adeps-experiment.W / .Y / .Z / .X → 同じ外部FOAデコーダー → スピーカー。bus以外へのFOA出力はありません。",
          "presentation": 1,
          "presentation_rect": [
            25,
            797,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "ab_hint",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            837,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "同じ長さ・レート・時刻原点・共通gainで書き出したペアを使用。切替は20ms crossfade、同じ輸送位置を維持します。",
          "presentation": 1,
          "presentation_rect": [
            25,
            837,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "limits",
          "maxclass": "comment",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            25,
            879,
            1060,
            35
          ],
          "fontname": "Yu Mincho",
          "fontsize": 13,
          "textcolor": [
            0.9,
            0.9,
            0.9,
            1
          ],
          "text": "新規ファイルを開くと比較を停止しGAIN 0。DSPは他パッチと共有。ここに公式ADEPSモデルや自動校正は含まれません。",
          "presentation": 1,
          "presentation_rect": [
            25,
            879,
            1060,
            35
          ]
        }
      },
      {
        "box": {
          "id": "linear_player",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 5,
          "patching_rect": [
            570,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sfplay~ 4"
        }
      },
      {
        "box": {
          "id": "enhanced_player",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 5,
          "patching_rect": [
            750,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "sfplay~ 4"
        }
      },
      {
        "box": {
          "id": "ab_play_one",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "1"
        }
      },
      {
        "box": {
          "id": "ab_play_zero",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1605,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "ab_start_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            30,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "ab_play_pair",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            210,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i i"
        }
      },
      {
        "box": {
          "id": "ab_stop_pair",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            390,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t i i"
        }
      },
      {
        "box": {
          "id": "ab_eof_once",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "onebang 1"
        }
      },
      {
        "box": {
          "id": "ab_arm_eof",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [
            750,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "linear_open_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            930,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b b"
        }
      },
      {
        "box": {
          "id": "linear_open_msg",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1670,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "open"
        }
      },
      {
        "box": {
          "id": "enhanced_open_order",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [
            30,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "t b b b"
        }
      },
      {
        "box": {
          "id": "enhanced_open_msg",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "open"
        }
      },
      {
        "box": {
          "id": "ab_reset_gain",
          "maxclass": "message",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "0."
        }
      },
      {
        "box": {
          "id": "ab_mix_clip",
          "maxclass": "newobj",
          "numinlets": 3,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "clip 0 1"
        }
      },
      {
        "box": {
          "id": "ab_mix_ramp",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "pack 0. 20"
        }
      },
      {
        "box": {
          "id": "ab_mix_signal",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [
            930,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "ab_linear_weight",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1735,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "!-~ 1."
        }
      },
      {
        "box": {
          "id": "ab_a_W",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_b_W",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_sum_W",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~"
        }
      },
      {
        "box": {
          "id": "ab_gain_W",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_send_W",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            750,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "send~ adeps-experiment.W"
        }
      },
      {
        "box": {
          "id": "ab_a_Y",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_b_Y",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1800,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_sum_Y",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            30,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~"
        }
      },
      {
        "box": {
          "id": "ab_gain_Y",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_send_Y",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            390,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "send~ adeps-experiment.Y"
        }
      },
      {
        "box": {
          "id": "ab_a_Z",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_b_Z",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_sum_Z",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            930,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~"
        }
      },
      {
        "box": {
          "id": "ab_gain_Z",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            1110,
            1865,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_send_Z",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            30,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "send~ adeps-experiment.Z"
        }
      },
      {
        "box": {
          "id": "ab_a_X",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            210,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_b_X",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            390,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_sum_X",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            570,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "+~"
        }
      },
      {
        "box": {
          "id": "ab_gain_X",
          "maxclass": "newobj",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [
            750,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "ab_send_X",
          "maxclass": "newobj",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [
            930,
            1930,
            170,
            24
          ],
          "fontname": "Yu Mincho",
          "fontsize": 12,
          "text": "send~ adeps-experiment.X"
        }
      }
    ],
    "lines": [
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
            "source_mode",
            0
          ],
          "destination": [
            "mode_change",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "mode_change",
            1
          ],
          "destination": [
            "source_stop",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "mode_change",
            0
          ],
          "destination": [
            "source_select",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "mode_change",
            0
          ],
          "destination": [
            "mono_selected",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "mono_selected",
            0
          ],
          "destination": [
            "file_start_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "mono_selected",
            0
          ],
          "destination": [
            "file_end_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run",
            0
          ],
          "destination": [
            "source_run_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run_ramp",
            0
          ],
          "destination": [
            "source_run_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run",
            0
          ],
          "destination": [
            "source_run_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run_order",
            1
          ],
          "destination": [
            "source_arm_eof",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_arm_eof",
            0
          ],
          "destination": [
            "source_eof_once",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run_order",
            0
          ],
          "destination": [
            "file_start_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "file_start_gate",
            0
          ],
          "destination": [
            "source_file",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_file",
            1
          ],
          "destination": [
            "file_end_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "file_end_gate",
            0
          ],
          "destination": [
            "source_eof_once",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_eof_once",
            0
          ],
          "destination": [
            "source_stop",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_stop",
            0
          ],
          "destination": [
            "source_run",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_stop",
            0
          ],
          "destination": [
            "source_file",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_open",
            0
          ],
          "destination": [
            "source_open_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_open_order",
            1
          ],
          "destination": [
            "source_stop",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_open_order",
            0
          ],
          "destination": [
            "file_open_message",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "file_open_message",
            0
          ],
          "destination": [
            "source_file",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_file",
            0
          ],
          "destination": [
            "source_select",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "pink",
            0
          ],
          "destination": [
            "source_select",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_select",
            0
          ],
          "destination": [
            "source_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_clip",
            0
          ],
          "destination": [
            "source_gated",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_run_signal",
            0
          ],
          "destination": [
            "source_gated",
            1
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
            "source_run",
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
            "source_file",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_trigger",
            0
          ],
          "destination": [
            "test_trigger",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "test_trigger",
            2
          ],
          "destination": [
            "sweep_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "test_trigger",
            1
          ],
          "destination": [
            "sweep_envelope",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "test_trigger",
            0
          ],
          "destination": [
            "burst_envelope",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_ramp",
            0
          ],
          "destination": [
            "sweep_phase",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_phase",
            0
          ],
          "destination": [
            "sweep_hz",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_hz",
            0
          ],
          "destination": [
            "sweep_osc",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_envelope",
            0
          ],
          "destination": [
            "sweep_env",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_osc",
            0
          ],
          "destination": [
            "sweep_audio",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_env",
            0
          ],
          "destination": [
            "sweep_audio",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "burst_envelope",
            0
          ],
          "destination": [
            "burst_env",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "pink",
            0
          ],
          "destination": [
            "burst_audio",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "burst_env",
            0
          ],
          "destination": [
            "burst_audio",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "sweep_audio",
            0
          ],
          "destination": [
            "source_select",
            3
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "burst_audio",
            0
          ],
          "destination": [
            "source_select",
            4
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
            "sweep_env",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_stop",
            0
          ],
          "destination": [
            "sweep_env",
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
            "burst_env",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_stop",
            0
          ],
          "destination": [
            "burst_env",
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
            "sweep_phase",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_stop",
            0
          ],
          "destination": [
            "sweep_phase",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain",
            0
          ],
          "destination": [
            "output_gain_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain_clip",
            0
          ],
          "destination": [
            "output_gain_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain_ramp",
            0
          ],
          "destination": [
            "output_gain_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_gated",
            0
          ],
          "destination": [
            "output_amp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain_signal",
            0
          ],
          "destination": [
            "output_amp",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_amp",
            0
          ],
          "destination": [
            "output_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_channel",
            0
          ],
          "destination": [
            "output_channel_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_channel_order",
            1
          ],
          "destination": [
            "output_gain_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain_zero",
            0
          ],
          "destination": [
            "output_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gain_zero",
            0
          ],
          "destination": [
            "output_gain_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_channel_order",
            0
          ],
          "destination": [
            "output_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            0
          ],
          "destination": [
            "output_dac",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            1
          ],
          "destination": [
            "output_dac",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            2
          ],
          "destination": [
            "output_dac",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            3
          ],
          "destination": [
            "output_dac",
            3
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            4
          ],
          "destination": [
            "output_dac",
            4
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            5
          ],
          "destination": [
            "output_dac",
            5
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            6
          ],
          "destination": [
            "output_dac",
            6
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            7
          ],
          "destination": [
            "output_dac",
            7
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            8
          ],
          "destination": [
            "output_dac",
            8
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            9
          ],
          "destination": [
            "output_dac",
            9
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            10
          ],
          "destination": [
            "output_dac",
            10
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "output_gate",
            11
          ],
          "destination": [
            "output_dac",
            11
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
            "output_channel",
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
            "output_gain",
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
            "output_gain_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_choose",
            0
          ],
          "destination": [
            "source_capture_choose_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_choose_order",
            1
          ],
          "destination": [
            "source_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_choose_order",
            0
          ],
          "destination": [
            "source_capture_dialog",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_dialog",
            0
          ],
          "destination": [
            "source_capture_path_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_path_order",
            2
          ],
          "destination": [
            "source_capture_show_path",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_show_path",
            0
          ],
          "destination": [
            "source_capture_path",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_path_order",
            1
          ],
          "destination": [
            "source_capture_wave",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_wave",
            0
          ],
          "destination": [
            "source_capture_open",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_open",
            0
          ],
          "destination": [
            "source_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_path_order",
            0
          ],
          "destination": [
            "source_capture_ready",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_ready",
            0
          ],
          "destination": [
            "source_capture_ready_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_start",
            0
          ],
          "destination": [
            "source_capture_one",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_one",
            0
          ],
          "destination": [
            "source_capture_ready_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_ready_gate",
            0
          ],
          "destination": [
            "source_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_stop",
            0
          ],
          "destination": [
            "source_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_zero",
            0
          ],
          "destination": [
            "source_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_zero",
            0
          ],
          "destination": [
            "source_capture_ready_gate",
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
            "source_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "samptype_init",
            0
          ],
          "destination": [
            "source_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_capture_recorder",
            0
          ],
          "destination": [
            "source_capture_elapsed",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_choose",
            0
          ],
          "destination": [
            "array_capture_choose_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_choose_order",
            1
          ],
          "destination": [
            "array_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_choose_order",
            0
          ],
          "destination": [
            "array_capture_dialog",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_dialog",
            0
          ],
          "destination": [
            "array_capture_path_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_path_order",
            2
          ],
          "destination": [
            "array_capture_show_path",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_show_path",
            0
          ],
          "destination": [
            "array_capture_path",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_path_order",
            1
          ],
          "destination": [
            "array_capture_wave",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_wave",
            0
          ],
          "destination": [
            "array_capture_open",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_open",
            0
          ],
          "destination": [
            "array_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_path_order",
            0
          ],
          "destination": [
            "array_capture_ready",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_ready",
            0
          ],
          "destination": [
            "array_capture_ready_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_start",
            0
          ],
          "destination": [
            "array_capture_one",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_one",
            0
          ],
          "destination": [
            "array_capture_ready_gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_ready_gate",
            0
          ],
          "destination": [
            "array_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_stop",
            0
          ],
          "destination": [
            "array_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_zero",
            0
          ],
          "destination": [
            "array_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_zero",
            0
          ],
          "destination": [
            "array_capture_ready_gate",
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
            "array_capture_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "samptype_init",
            0
          ],
          "destination": [
            "array_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_capture_recorder",
            0
          ],
          "destination": [
            "array_capture_elapsed",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "source_gated",
            0
          ],
          "destination": [
            "source_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            0
          ],
          "destination": [
            "array_capture_recorder",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            1
          ],
          "destination": [
            "array_capture_recorder",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            2
          ],
          "destination": [
            "array_capture_recorder",
            2
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            3
          ],
          "destination": [
            "array_capture_recorder",
            3
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            4
          ],
          "destination": [
            "array_capture_recorder",
            4
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            5
          ],
          "destination": [
            "array_capture_recorder",
            5
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            6
          ],
          "destination": [
            "array_capture_recorder",
            6
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            7
          ],
          "destination": [
            "array_capture_recorder",
            7
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            8
          ],
          "destination": [
            "array_capture_recorder",
            8
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            9
          ],
          "destination": [
            "array_capture_recorder",
            9
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            10
          ],
          "destination": [
            "array_capture_recorder",
            10
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            11
          ],
          "destination": [
            "array_capture_recorder",
            11
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            12
          ],
          "destination": [
            "array_capture_recorder",
            12
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            13
          ],
          "destination": [
            "array_capture_recorder",
            13
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            14
          ],
          "destination": [
            "array_capture_recorder",
            14
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            15
          ],
          "destination": [
            "array_capture_recorder",
            15
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            16
          ],
          "destination": [
            "array_capture_recorder",
            16
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            17
          ],
          "destination": [
            "array_capture_recorder",
            17
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "array_adc",
            18
          ],
          "destination": [
            "array_capture_recorder",
            18
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "both_record",
            0
          ],
          "destination": [
            "both_record_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "both_record_order",
            1
          ],
          "destination": [
            "array_capture_one",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "both_record_order",
            0
          ],
          "destination": [
            "source_capture_one",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain",
            0
          ],
          "destination": [
            "ab_gain_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_clip",
            0
          ],
          "destination": [
            "ab_gain_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_ramp",
            0
          ],
          "destination": [
            "ab_gain_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_start",
            0
          ],
          "destination": [
            "ab_start_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_start_order",
            1
          ],
          "destination": [
            "ab_play_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_play_one",
            0
          ],
          "destination": [
            "ab_play_pair",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_play_pair",
            1
          ],
          "destination": [
            "linear_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_play_pair",
            0
          ],
          "destination": [
            "enhanced_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_stop",
            0
          ],
          "destination": [
            "ab_play_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_play_zero",
            0
          ],
          "destination": [
            "ab_stop_pair",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_stop_pair",
            1
          ],
          "destination": [
            "linear_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_stop_pair",
            0
          ],
          "destination": [
            "enhanced_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_player",
            4
          ],
          "destination": [
            "ab_eof_once",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_player",
            4
          ],
          "destination": [
            "ab_eof_once",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_eof_once",
            0
          ],
          "destination": [
            "ab_play_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_start_order",
            0
          ],
          "destination": [
            "ab_arm_eof",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_arm_eof",
            1
          ],
          "destination": [
            "ab_eof_once",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_arm_eof",
            0
          ],
          "destination": [
            "ab_play_one",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_open",
            0
          ],
          "destination": [
            "linear_open_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_open_order",
            2
          ],
          "destination": [
            "ab_play_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_open_order",
            1
          ],
          "destination": [
            "ab_reset_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_open_order",
            0
          ],
          "destination": [
            "linear_open_msg",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_open_msg",
            0
          ],
          "destination": [
            "linear_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_open",
            0
          ],
          "destination": [
            "enhanced_open_order",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_open_order",
            2
          ],
          "destination": [
            "ab_play_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_open_order",
            1
          ],
          "destination": [
            "ab_reset_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_open_order",
            0
          ],
          "destination": [
            "enhanced_open_msg",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_open_msg",
            0
          ],
          "destination": [
            "enhanced_player",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_reset_gain",
            0
          ],
          "destination": [
            "ab_gain",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_reset_gain",
            0
          ],
          "destination": [
            "ab_gain_signal",
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
            "ab_play_zero",
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
            "ab_reset_gain",
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
            "ab_mix",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix",
            0
          ],
          "destination": [
            "ab_mix_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_clip",
            0
          ],
          "destination": [
            "ab_mix_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_ramp",
            0
          ],
          "destination": [
            "ab_mix_signal",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_signal",
            0
          ],
          "destination": [
            "ab_linear_weight",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_player",
            0
          ],
          "destination": [
            "ab_a_W",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_player",
            0
          ],
          "destination": [
            "ab_b_W",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_linear_weight",
            0
          ],
          "destination": [
            "ab_a_W",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_signal",
            0
          ],
          "destination": [
            "ab_b_W",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_a_W",
            0
          ],
          "destination": [
            "ab_sum_W",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_b_W",
            0
          ],
          "destination": [
            "ab_sum_W",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_sum_W",
            0
          ],
          "destination": [
            "ab_gain_W",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_signal",
            0
          ],
          "destination": [
            "ab_gain_W",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_W",
            0
          ],
          "destination": [
            "ab_send_W",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_player",
            1
          ],
          "destination": [
            "ab_a_Y",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_player",
            1
          ],
          "destination": [
            "ab_b_Y",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_linear_weight",
            0
          ],
          "destination": [
            "ab_a_Y",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_signal",
            0
          ],
          "destination": [
            "ab_b_Y",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_a_Y",
            0
          ],
          "destination": [
            "ab_sum_Y",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_b_Y",
            0
          ],
          "destination": [
            "ab_sum_Y",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_sum_Y",
            0
          ],
          "destination": [
            "ab_gain_Y",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_signal",
            0
          ],
          "destination": [
            "ab_gain_Y",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_Y",
            0
          ],
          "destination": [
            "ab_send_Y",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_player",
            2
          ],
          "destination": [
            "ab_a_Z",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_player",
            2
          ],
          "destination": [
            "ab_b_Z",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_linear_weight",
            0
          ],
          "destination": [
            "ab_a_Z",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_signal",
            0
          ],
          "destination": [
            "ab_b_Z",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_a_Z",
            0
          ],
          "destination": [
            "ab_sum_Z",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_b_Z",
            0
          ],
          "destination": [
            "ab_sum_Z",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_sum_Z",
            0
          ],
          "destination": [
            "ab_gain_Z",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_signal",
            0
          ],
          "destination": [
            "ab_gain_Z",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_Z",
            0
          ],
          "destination": [
            "ab_send_Z",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "linear_player",
            3
          ],
          "destination": [
            "ab_a_X",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "enhanced_player",
            3
          ],
          "destination": [
            "ab_b_X",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_linear_weight",
            0
          ],
          "destination": [
            "ab_a_X",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_mix_signal",
            0
          ],
          "destination": [
            "ab_b_X",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_a_X",
            0
          ],
          "destination": [
            "ab_sum_X",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_b_X",
            0
          ],
          "destination": [
            "ab_sum_X",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_sum_X",
            0
          ],
          "destination": [
            "ab_gain_X",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_signal",
            0
          ],
          "destination": [
            "ab_gain_X",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "ab_gain_X",
            0
          ],
          "destination": [
            "ab_send_X",
            0
          ]
        }
      }
    ]
  }
}
