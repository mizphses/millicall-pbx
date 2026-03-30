from __future__ import annotations

# Reusable TTS config fields — included in every node that can speak
_TTS_CONFIG = {
    "tts_provider": {
        "type": "select",
        "label": "TTSプロバイダ",
        "required": True,
        "default": "google",
        "options": ["google", "coefont"],
    },
    "google_tts_voice": {
        "type": "select",
        "label": "Google TTSボイス",
        "required": False,
        "default": "ja-JP-Chirp3-HD-Aoede",
        "options": [
            "ja-JP-Chirp3-HD-Aoede",
            "ja-JP-Chirp3-HD-Kore",
            "ja-JP-Chirp3-HD-Leda",
            "ja-JP-Chirp3-HD-Zephyr",
            "ja-JP-Chirp3-HD-Charon",
            "ja-JP-Chirp3-HD-Fenrir",
            "ja-JP-Chirp3-HD-Orus",
            "ja-JP-Chirp3-HD-Puck",
        ],
    },
    "coefont_voice_id": {
        "type": "string",
        "label": "CoeFont ボイスID",
        "required": False,
        "default": "",
    },
}

COMMON_NODES: dict[str, dict] = {
    "start": {
        "label": "開始",
        "category": "common",
        "color": "#4CAF50",
        "max_inputs": 0,
        "max_outputs": 1,
        "config_schema": {
            "ring_count": {
                "type": "number",
                "label": "応答前コール数",
                "required": False,
                "default": 0,
                "description": "応答前に鳴らすコール数 (0=即応答, 1コール≈5秒)",
            },
        },
    },
    "end": {
        "label": "終了",
        "category": "common",
        "color": "#F44336",
        "max_inputs": 1,
        "max_outputs": 0,
        "config_schema": {},
    },
    "hangup": {
        "label": "切断",
        "category": "common",
        "color": "#E91E63",
        "max_inputs": 1,
        "max_outputs": 0,
        "config_schema": {},
    },
    "play_audio": {
        "label": "音声再生",
        "category": "common",
        "color": "#2196F3",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "tts_text": {
                "type": "textarea",
                "label": "読み上げテキスト",
                "required": True,
                "default": "",
            },
            **_TTS_CONFIG,
            "file_path": {
                "type": "string",
                "label": "音声ファイルパス（TTS不使用時）",
                "required": False,
                "default": "",
            },
        },
    },
    "transfer": {
        "label": "転送",
        "category": "common",
        "color": "#9C27B0",
        "max_inputs": 1,
        "max_outputs": 0,
        "config_schema": {
            "destination": {
                "type": "string",
                "label": "転送先番号",
                "required": True,
                "default": "",
            },
            "transfer_type": {
                "type": "select",
                "label": "転送種別",
                "required": True,
                "default": "blind",
                "options": ["blind", "attended"],
            },
        },
    },
    "condition": {
        "label": "条件分岐",
        "category": "common",
        "color": "#FF9800",
        "max_inputs": 1,
        "max_outputs": 2,
        "config_schema": {
            "variable": {
                "type": "string",
                "label": "変数名",
                "required": True,
                "default": "",
            },
            "operator": {
                "type": "select",
                "label": "演算子",
                "required": True,
                "default": "eq",
                "options": ["eq", "neq", "gt", "lt", "gte", "lte", "contains"],
            },
            "value": {
                "type": "string",
                "label": "比較値",
                "required": True,
                "default": "",
            },
        },
    },
    "set_variable": {
        "label": "変数設定",
        "category": "common",
        "color": "#607D8B",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "variable": {
                "type": "string",
                "label": "変数名",
                "required": True,
                "default": "",
            },
            "value": {
                "type": "string",
                "label": "値（{{変数名}} でテンプレート展開可）",
                "required": True,
                "default": "",
            },
        },
    },
    "goto": {
        "label": "ジャンプ",
        "category": "common",
        "color": "#795548",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "target_node_id": {
                "type": "string",
                "label": "ジャンプ先ノードID",
                "required": True,
                "default": "",
            },
        },
    },
}

IVR_NODES: dict[str, dict] = {
    "dtmf_input": {
        "label": "DTMF入力",
        "category": "ivr",
        "color": "#00BCD4",
        "max_inputs": 1,
        "max_outputs": 10,
        "config_schema": {
            "prompt_mode": {
                "type": "select",
                "label": "案内方式",
                "required": True,
                "default": "tts",
                "options": ["tts", "beep", "none"],
            },
            "prompt_text": {
                "type": "textarea",
                "label": "案内テキスト（TTS選択時）",
                "required": False,
                "default": "",
            },
            **_TTS_CONFIG,
            "max_digits": {
                "type": "number",
                "label": "最大桁数",
                "required": True,
                "default": 1,
            },
            "timeout": {
                "type": "number",
                "label": "タイムアウト(秒)",
                "required": True,
                "default": 5,
            },
            "variable": {
                "type": "string",
                "label": "保存先変数",
                "required": True,
                "default": "dtmf_result",
            },
        },
    },
    "menu": {
        "label": "メニュー",
        "category": "ivr",
        "color": "#3F51B5",
        "max_inputs": 1,
        "max_outputs": 10,
        "config_schema": {
            "prompt_mode": {
                "type": "select",
                "label": "案内方式",
                "required": True,
                "default": "tts",
                "options": ["tts", "beep", "none"],
            },
            "prompt_text": {
                "type": "textarea",
                "label": "案内テキスト（TTS選択時）",
                "required": True,
                "default": "ご用件を番号で選択してください。営業は1、サポートは2を押してください。",
            },
            **_TTS_CONFIG,
            "timeout": {
                "type": "number",
                "label": "タイムアウト(秒)",
                "required": True,
                "default": 5,
            },
            "max_retries": {
                "type": "number",
                "label": "最大リトライ回数",
                "required": True,
                "default": 3,
            },
            "invalid_text": {
                "type": "string",
                "label": "無効入力時メッセージ",
                "required": False,
                "default": "入力が正しくありません。もう一度お試しください。",
            },
        },
    },
    "time_condition": {
        "label": "時間条件",
        "category": "ivr",
        "color": "#FF5722",
        "max_inputs": 1,
        "max_outputs": 2,
        "config_schema": {
            "start_time": {
                "type": "string",
                "label": "開始時刻 (HH:MM)",
                "required": True,
                "default": "09:00",
            },
            "end_time": {
                "type": "string",
                "label": "終了時刻 (HH:MM)",
                "required": True,
                "default": "18:00",
            },
            "days_of_week": {
                "type": "multi_select",
                "label": "曜日",
                "required": False,
                "default": ["mon", "tue", "wed", "thu", "fri"],
                "options": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            },
        },
    },
    "voicemail": {
        "label": "ボイスメール",
        "category": "ivr",
        "color": "#8BC34A",
        "max_inputs": 1,
        "max_outputs": 0,
        "config_schema": {
            "mailbox": {
                "type": "string",
                "label": "メールボックス番号",
                "required": True,
                "default": "",
            },
            "greeting_text": {
                "type": "textarea",
                "label": "留守電ガイダンス（TTS）",
                "required": False,
                "default": "ただいま電話に出ることができません。メッセージをお残しください。",
            },
            **_TTS_CONFIG,
        },
    },
}

AI_WORKFLOW_NODES: dict[str, dict] = {
    "ai_conversation": {
        "label": "AI会話",
        "category": "ai_workflow",
        "color": "#673AB7",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "system_prompt": {
                "type": "textarea",
                "label": "システムプロンプト",
                "required": True,
                "default": "あなたは電話応対AIアシスタントです。丁寧な敬語で応対してください。",
            },
            "greeting_text": {
                "type": "string",
                "label": "挨拶テキスト",
                "required": True,
                "default": "お電話ありがとうございます。ご用件をどうぞ。",
            },
            "llm_provider": {
                "type": "select",
                "label": "LLMプロバイダ",
                "required": True,
                "default": "google",
                "options": ["google", "openai", "anthropic"],
            },
            "llm_model": {
                "type": "string",
                "label": "LLMモデル",
                "required": True,
                "default": "gemini-2.5-flash",
            },
            "max_turns": {
                "type": "number",
                "label": "最大ターン数",
                "required": True,
                "default": 10,
            },
            "extraction_mode": {
                "type": "select",
                "label": "情報聞き出しモード",
                "required": False,
                "default": "auto",
                "options": ["auto", "direct"],
                "description": "auto: 自然な会話の流れで聞き出す / direct: 最初から本題に入る",
            },
            **_TTS_CONFIG,
        },
    },
    "intent_detection": {
        "label": "意図検出",
        "category": "ai_workflow",
        "color": "#009688",
        "max_inputs": 1,
        "max_outputs": 10,
        "config_schema": {
            "intents": {
                "type": "key_value_list",
                "label": "意図一覧（キー: 意図ID、値: 説明）",
                "required": True,
                "default": [
                    {"key": "reservation", "value": "予約に関する問い合わせ"},
                    {"key": "support", "value": "サポートに関する問い合わせ"},
                    {"key": "other", "value": "その他"},
                ],
            },
            "llm_provider": {
                "type": "select",
                "label": "LLMプロバイダ",
                "required": True,
                "default": "google",
                "options": ["google", "openai", "anthropic"],
            },
            "llm_model": {
                "type": "string",
                "label": "LLMモデル",
                "required": True,
                "default": "gemini-2.5-flash",
            },
            "fallback_intent": {
                "type": "string",
                "label": "フォールバック意図ID",
                "required": True,
                "default": "other",
            },
        },
    },
    "collect_info": {
        "label": "情報収集",
        "category": "ai_workflow",
        "color": "#00ACC1",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "fields": {
                "type": "key_value_list",
                "label": "収集項目（キー: 変数名、値: 質問テキスト）",
                "required": True,
                "default": [
                    {"key": "name", "value": "お名前を教えてください"},
                    {"key": "phone", "value": "お電話番号を教えてください"},
                ],
            },
            "llm_provider": {
                "type": "select",
                "label": "LLMプロバイダ",
                "required": True,
                "default": "google",
                "options": ["google", "openai", "anthropic"],
            },
            "llm_model": {
                "type": "string",
                "label": "LLMモデル",
                "required": True,
                "default": "gemini-2.5-flash",
            },
            **_TTS_CONFIG,
            "confirmation": {
                "type": "boolean",
                "label": "入力内容の確認を取る",
                "required": False,
                "default": True,
            },
        },
    },
    "api_call": {
        "label": "API呼び出し",
        "category": "ai_workflow",
        "color": "#FF6F00",
        "max_inputs": 1,
        "max_outputs": 2,
        "config_schema": {
            "url": {
                "type": "string",
                "label": "URL（{{変数名}} でテンプレート展開可）",
                "required": True,
                "default": "",
            },
            "method": {
                "type": "select",
                "label": "メソッド",
                "required": True,
                "default": "POST",
                "options": ["GET", "POST", "PUT", "DELETE"],
            },
            "headers": {
                "type": "json",
                "label": "ヘッダー (JSON)",
                "required": False,
                "default": {},
            },
            "content_type": {
                "type": "select",
                "label": "ボディ形式",
                "required": False,
                "default": "json",
                "options": ["json", "form"],
                "description": "json: JSON / form: application/x-www-form-urlencoded",
            },
            "body_template": {
                "type": "textarea",
                "label": "ボディ（{{変数名}} 展開可）",
                "required": False,
                "default": "",
                "description": "JSON形式 または key=value&key=value 形式",
            },
            "result_variable": {
                "type": "string",
                "label": "結果保存先変数",
                "required": True,
                "default": "api_result",
            },
        },
    },
    "email_notify": {
        "label": "メール通知",
        "category": "ai_workflow",
        "color": "#E65100",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "to": {
                "type": "string",
                "label": "宛先メールアドレス",
                "required": True,
                "default": "",
            },
            "subject_template": {
                "type": "string",
                "label": "件名（{{変数名}} 展開可）",
                "required": True,
                "default": "",
            },
            "body_template": {
                "type": "textarea",
                "label": "本文（{{変数名}} 展開可）",
                "required": True,
                "default": "",
            },
        },
    },
    "human_escalation": {
        "label": "有人エスカレーション",
        "category": "ai_workflow",
        "color": "#D32F2F",
        "max_inputs": 1,
        "max_outputs": 0,
        "config_schema": {
            "destination": {
                "type": "string",
                "label": "転送先内線番号",
                "required": True,
                "default": "",
            },
            "announcement_text": {
                "type": "textarea",
                "label": "転送前案内（TTS）",
                "required": False,
                "default": "担当者におつなぎします。少々お待ちください。",
            },
            **_TTS_CONFIG,
            "summary_to_agent": {
                "type": "boolean",
                "label": "オペレーターに会話要約を伝える",
                "required": False,
                "default": True,
            },
        },
    },
}

SPECIAL_NODES: dict[str, dict] = {
    "call_workflow": {
        "label": "ワークフロー呼び出し",
        "category": "special",
        "color": "#263238",
        "max_inputs": 1,
        "max_outputs": 1,
        "config_schema": {
            "workflow_id": {
                "type": "number",
                "label": "呼び出し先ワークフローID",
                "required": True,
                "default": 0,
            },
        },
    },
}


def get_node_types_for_workflow_type(workflow_type: str = "workflow") -> dict[str, dict]:
    """Return all available node types (IVR + AI + special)."""
    nodes = {**COMMON_NODES}
    nodes.update(IVR_NODES)
    nodes.update(AI_WORKFLOW_NODES)
    nodes.update(SPECIAL_NODES)
    return nodes
