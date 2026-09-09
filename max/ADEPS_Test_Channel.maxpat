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
      70,
      70,
      1150,
      865
    ],
    "openinpresentation": 1,
    "default_fontname": "Arial",
    "default_fontsize": 12,
    "bgcolor": [
      0.09,
      0.11,
      0.14,
      1
    ],
    "editing_bgcolor": [
      0.13,
      0.15,
      0.18,
      1
    ],
    "boxes": [
      {
        "box": {
          "id": "title",
          "maxclass": "comment",
          "patching_rect": [
            30,
            20,
            1090,
            40
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 28,
          "text": "ADEPS-test / 12-channel manual output test",
          "presentation": 1,
          "presentation_rect": [
            30,
            20,
            1090,
            40
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "subtitle",
          "maxclass": "comment",
          "patching_rect": [
            30,
            70,
            1090,
            35
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Local channel identification bridge. This patch does not implement AED, calibration, AFC processing or measurement.",
          "presentation": 1,
          "presentation_rect": [
            30,
            70,
            1090,
            35
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "route_note",
          "maxclass": "comment",
          "patching_rect": [
            30,
            115,
            1090,
            40
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Max logical outputs 1-12. Map these to physical outputs for your equipment and verify the channel order before enabling audio.",
          "presentation": 1,
          "presentation_rect": [
            30,
            115,
            1090,
            40
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "start_label",
          "maxclass": "comment",
          "patching_rect": [
            30,
            190,
            440,
            28
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 18,
          "text": "1   START / STOP CONTROL BRIDGE",
          "presentation": 1,
          "presentation_rect": [
            30,
            190,
            440,
            28
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "start",
          "maxclass": "button",
          "patching_rect": [
            30,
            230,
            32,
            32
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            30,
            230,
            32,
            32
          ],
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "start_text",
          "maxclass": "comment",
          "patching_rect": [
            77,
            230,
            450,
            32
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "START bridge: localhost UDP 8872 -> replies 8873",
          "presentation": 1,
          "presentation_rect": [
            77,
            230,
            450,
            32
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "stopbridge",
          "maxclass": "button",
          "patching_rect": [
            30,
            282,
            32,
            32
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            30,
            282,
            32,
            32
          ],
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "stopbridge_text",
          "maxclass": "comment",
          "patching_rect": [
            77,
            282,
            450,
            32
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "STOP bridge and mute this patch",
          "presentation": 1,
          "presentation_rect": [
            77,
            282,
            450,
            32
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "bridge_status",
          "maxclass": "message",
          "patching_rect": [
            30,
            335,
            580,
            44
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "Bridge stopped - press START",
          "presentation": 1,
          "presentation_rect": [
            30,
            335,
            580,
            44
          ]
        }
      },
      {
        "box": {
          "id": "bridge_note",
          "maxclass": "comment",
          "patching_rect": [
            30,
            390,
            580,
            54
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "A pong or ack confirms control processing only. It does not prove DSP, audio interface, Dante subscription or speaker output.",
          "presentation": 1,
          "presentation_rect": [
            30,
            390,
            580,
            54
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "audio_label",
          "maxclass": "comment",
          "patching_rect": [
            660,
            190,
            430,
            28
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 18,
          "text": "2   LOCAL AUDIO CONTROLS",
          "presentation": 1,
          "presentation_rect": [
            660,
            190,
            430,
            28
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "dsp",
          "maxclass": "ezdac~",
          "patching_rect": [
            660,
            234,
            45,
            45
          ],
          "numinlets": 2,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            660,
            234,
            45,
            45
          ],
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "dsp_label",
          "maxclass": "comment",
          "patching_rect": [
            724,
            230,
            380,
            52
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Manual DSP switch (shared by Max patches)\nNo automatic DSP start is wired.",
          "presentation": 1,
          "presentation_rect": [
            724,
            230,
            380,
            52
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "channel",
          "maxclass": "number",
          "patching_rect": [
            660,
            312,
            80,
            28
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            660,
            312,
            80,
            28
          ],
          "minimum": 0,
          "maximum": 12,
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "channel_label",
          "maxclass": "comment",
          "patching_rect": [
            760,
            306,
            345,
            52
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Output channel: 0 = all closed, 1-12 = selected\nEach selection resets the local level to zero.",
          "presentation": 1,
          "presentation_rect": [
            760,
            306,
            345,
            52
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "level",
          "maxclass": "flonum",
          "patching_rect": [
            660,
            396,
            100,
            28
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            660,
            396,
            100,
            28
          ],
          "minimum": 0.0,
          "maximum": 0.03,
          "format": 6,
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "level_label",
          "maxclass": "comment",
          "patching_rect": [
            780,
            390,
            325,
            52
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Manual amplitude: 0.000 to 0.030\nThe browser cannot raise this value.",
          "presentation": 1,
          "presentation_rect": [
            780,
            390,
            325,
            52
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "mute",
          "maxclass": "button",
          "patching_rect": [
            660,
            478,
            46,
            46
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            660,
            478,
            46,
            46
          ],
          "parameter_enable": 0
        }
      },
      {
        "box": {
          "id": "mute_label",
          "maxclass": "comment",
          "patching_rect": [
            726,
            478,
            380,
            48
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 15,
          "text": "STOP TEST / MUTE\nCloses every output and resets gain to zero.",
          "presentation": 1,
          "presentation_rect": [
            726,
            478,
            380,
            48
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "meter",
          "maxclass": "meter~",
          "patching_rect": [
            30,
            492,
            510,
            28
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "presentation": 1,
          "presentation_rect": [
            30,
            492,
            510,
            28
          ],
          "outlettype": [
            "float"
          ]
        }
      },
      {
        "box": {
          "id": "meterlabel",
          "maxclass": "comment",
          "patching_rect": [
            30,
            535,
            570,
            45
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "Generated-signal meter, before channel routing. This is not microphone measurement or acoustic SPL.",
          "presentation": 1,
          "presentation_rect": [
            30,
            535,
            570,
            45
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "order",
          "maxclass": "comment",
          "patching_rect": [
            30,
            605,
            1070,
            62
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 15,
          "text": "Use: choose the audio device and verify its 12 output mappings -> start bridge -> select one channel -> enable DSP manually -> raise level slowly -> STOP TEST.",
          "presentation": 1,
          "presentation_rect": [
            30,
            605,
            1070,
            62
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "limits",
          "maxclass": "comment",
          "patching_rect": [
            30,
            688,
            1070,
            68
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "White-noise identification only. Keep amplifier gain low. No automatic sweep, no microphone input, no room correction and no Dante configuration. Coordinate with the venue operator before using speakers.",
          "presentation": 1,
          "presentation_rect": [
            30,
            688,
            1070,
            68
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "initial",
          "maxclass": "comment",
          "patching_rect": [
            30,
            780,
            1070,
            48
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 13,
          "text": "On load: gain 0, channel 0, bridge stopped. Existing global DSP state is not changed. Close other test generators before enabling this one.",
          "presentation": 1,
          "presentation_rect": [
            30,
            780,
            1070,
            48
          ],
          "textcolor": [
            0.88,
            0.9,
            0.92,
            1
          ]
        }
      },
      {
        "box": {
          "id": "start_trigger",
          "maxclass": "newobj",
          "patching_rect": [
            40,
            880,
            75,
            22
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "start_message",
          "maxclass": "message",
          "patching_rect": [
            40,
            930,
            100,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "script start"
        }
      },
      {
        "box": {
          "id": "stop_trigger",
          "maxclass": "newobj",
          "patching_rect": [
            260,
            880,
            75,
            22
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "t b b"
        }
      },
      {
        "box": {
          "id": "stop_message",
          "maxclass": "message",
          "patching_rect": [
            260,
            930,
            100,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "script stop"
        }
      },
      {
        "box": {
          "id": "zero_channel",
          "maxclass": "message",
          "patching_rect": [
            450,
            900,
            40,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "0"
        }
      },
      {
        "box": {
          "id": "initial_mute",
          "maxclass": "newobj",
          "patching_rect": [
            450,
            850,
            120,
            22
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "loadmess 0"
        }
      },
      {
        "box": {
          "id": "node",
          "maxclass": "newobj",
          "patching_rect": [
            30,
            1000,
            390,
            22
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "node.script bridge.js @autostart 0 @watch 0"
        }
      },
      {
        "box": {
          "id": "route",
          "maxclass": "newobj",
          "patching_rect": [
            30,
            1050,
            260,
            22
          ],
          "numinlets": 1,
          "numoutlets": 4,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "route channel mute status"
        }
      },
      {
        "box": {
          "id": "log",
          "maxclass": "newobj",
          "patching_rect": [
            420,
            1050,
            200,
            22
          ],
          "numinlets": 1,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "print ADEPS_TEST_BRIDGE"
        }
      },
      {
        "box": {
          "id": "status_set",
          "maxclass": "newobj",
          "patching_rect": [
            310,
            1110,
            150,
            22
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "prepend set"
        }
      },
      {
        "box": {
          "id": "select_trigger",
          "maxclass": "newobj",
          "patching_rect": [
            680,
            880,
            85,
            22
          ],
          "numinlets": 1,
          "numoutlets": 3,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "t i b b"
        }
      },
      {
        "box": {
          "id": "immediate_zero",
          "maxclass": "message",
          "patching_rect": [
            920,
            930,
            60,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "0. 0"
        }
      },
      {
        "box": {
          "id": "level_ui_zero",
          "maxclass": "message",
          "patching_rect": [
            1010,
            930,
            75,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "set 0."
        }
      },
      {
        "box": {
          "id": "channel_clip",
          "maxclass": "newobj",
          "patching_rect": [
            680,
            990,
            120,
            22
          ],
          "numinlets": 3,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "clip 0 12"
        }
      },
      {
        "box": {
          "id": "level_clip",
          "maxclass": "newobj",
          "patching_rect": [
            890,
            1050,
            140,
            22
          ],
          "numinlets": 3,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "clip 0. 0.03"
        }
      },
      {
        "box": {
          "id": "level_ramp",
          "maxclass": "newobj",
          "patching_rect": [
            890,
            1100,
            140,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "pack 0. 150"
        }
      },
      {
        "box": {
          "id": "gain_signal",
          "maxclass": "newobj",
          "patching_rect": [
            890,
            1150,
            120,
            22
          ],
          "numinlets": 2,
          "numoutlets": 2,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "line~ 0."
        }
      },
      {
        "box": {
          "id": "noise",
          "maxclass": "newobj",
          "patching_rect": [
            680,
            1140,
            90,
            22
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "noise~"
        }
      },
      {
        "box": {
          "id": "amplitude",
          "maxclass": "newobj",
          "patching_rect": [
            680,
            1200,
            90,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "*~ 0."
        }
      },
      {
        "box": {
          "id": "gate",
          "maxclass": "newobj",
          "patching_rect": [
            680,
            1260,
            170,
            22
          ],
          "numinlets": 2,
          "numoutlets": 12,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "gate~ 12 0"
        }
      },
      {
        "box": {
          "id": "dac",
          "maxclass": "newobj",
          "patching_rect": [
            300,
            1360,
            620,
            22
          ],
          "numinlets": 12,
          "numoutlets": 0,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "dac~ 1 2 3 4 5 6 7 8 9 10 11 12"
        }
      },
      {
        "box": {
          "id": "zero_gate",
          "maxclass": "message",
          "patching_rect": [
            800,
            930,
            40,
            22
          ],
          "numinlets": 2,
          "numoutlets": 1,
          "fontname": "Arial",
          "fontsize": 12,
          "text": "0"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": [
            "start",
            0
          ],
          "destination": [
            "start_trigger",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "start_trigger",
            1
          ],
          "destination": [
            "zero_channel",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "start_trigger",
            0
          ],
          "destination": [
            "start_message",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "start_message",
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
            "stopbridge",
            0
          ],
          "destination": [
            "stop_trigger",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_trigger",
            1
          ],
          "destination": [
            "zero_channel",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_trigger",
            0
          ],
          "destination": [
            "stop_message",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "stop_message",
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
            "mute",
            0
          ],
          "destination": [
            "zero_channel",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "initial_mute",
            0
          ],
          "destination": [
            "channel",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero_channel",
            0
          ],
          "destination": [
            "channel",
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
            "node",
            1
          ],
          "destination": [
            "log",
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
            "channel",
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
            "zero_channel",
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
            "status_set",
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
            "log",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "status_set",
            0
          ],
          "destination": [
            "bridge_status",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "channel",
            0
          ],
          "destination": [
            "select_trigger",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "select_trigger",
            2
          ],
          "destination": [
            "zero_gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "zero_gate",
            0
          ],
          "destination": [
            "gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "select_trigger",
            1
          ],
          "destination": [
            "immediate_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "select_trigger",
            1
          ],
          "destination": [
            "level_ui_zero",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "level_ui_zero",
            0
          ],
          "destination": [
            "level",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "immediate_zero",
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
            "select_trigger",
            0
          ],
          "destination": [
            "channel_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "channel_clip",
            0
          ],
          "destination": [
            "gate",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "level",
            0
          ],
          "destination": [
            "level_clip",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "level_clip",
            0
          ],
          "destination": [
            "level_ramp",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "level_ramp",
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
            "noise",
            0
          ],
          "destination": [
            "amplitude",
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
            "amplitude",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "amplitude",
            0
          ],
          "destination": [
            "gate",
            1
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "amplitude",
            0
          ],
          "destination": [
            "meter",
            0
          ]
        }
      },
      {
        "patchline": {
          "source": [
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
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
            "gate",
            11
          ],
          "destination": [
            "dac",
            11
          ]
        }
      }
    ],
    "autosave": 0,
    "dependency_cache": [
      {
        "name": "bridge.js",
        "type": "TEXT",
        "implicit": 1
      },
      {
        "name": "control-server.js",
        "type": "TEXT",
        "implicit": 1
      },
      {
        "name": "osc-codec.js",
        "type": "TEXT",
        "implicit": 1
      }
    ]
  }
}
