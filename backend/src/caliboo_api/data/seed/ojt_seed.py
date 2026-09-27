"""OJT画面のシードデータ。

旧`data/ojt_data.py`にハードコードされていた`DEPARTMENTS`/`_INITIAL_MESSAGES`/
`_KNOWLEDGE`の生データをDBシード用データとして移設したもの。
`db.bootstrap_db()`から初回投入時に参照される。
"""

# !NOTE: `color`を追加・変更する場合は、フロントエンドのダークモード対応で
#        この値を逆引きする`frontend/src/lib/deptColor.ts`の`HEX_TO_TONE`も
#        合わせて更新すること。更新されない場合、ダークモードでは
#        ニュートラル配色にフォールバックされる(エラーにはならない)。
DEPARTMENTS_SEED = [
    {"id": "dev", "name": "開発課", "icon": "ph ph-code", "color": "#d6ebff", "knowledge_count": 128},
    {
        "id": "qa",
        "name": "品質保証課",
        "icon": "ph ph-shield-check",
        "color": "#cdeede",
        "knowledge_count": 94,
    },
    {
        "id": "sales",
        "name": "営業課",
        "icon": "ph ph-handshake",
        "color": "#ffd9e6",
        "knowledge_count": 76,
    },
    {
        "id": "design",
        "name": "設計課",
        "icon": "ph ph-compass-tool",
        "color": "#e3ddff",
        "knowledge_count": 112,
    },
    {
        "id": "mfg",
        "name": "製造課",
        "icon": "ph ph-factory",
        "color": "#ffe9c7",
        "knowledge_count": 153,
    },
    {
        "id": "ga",
        "name": "総務課",
        "icon": "ph ph-briefcase",
        "color": "#f4f0ec",
        "knowledge_count": 61,
    },
]

INITIAL_MESSAGES_SEED = {
    dept["id"]: [
        {
            "role": "bot",
            "text": f"{dept['name']}のメンターだよ。ナレッジベースから何でも答えるね。",
        }
    ]
    for dept in DEPARTMENTS_SEED
}

KNOWLEDGE_SEED = {
    "dev": [
        {"title": "開発オンボーディング手順書", "description": "環境構築 / Git / レビュー文化"},
        {"title": "コーディング規約 2026", "description": "命名 / テスト / PRの粒度"},
        {"title": "よくあるつまずきFAQ", "description": "ビルド失敗 / 権限まわり"},
    ],
    "qa": [
        {"title": "品質保証プロセス標準", "description": "テスト計画 / レビュー観点"},
        {"title": "バグ起票ガイドライン", "description": "再現手順 / 重要度の付け方"},
    ],
    "sales": [
        {"title": "提案資料テンプレート集", "description": "業種別サンプル"},
        {"title": "商談ロールプレイ資料", "description": "よくある質疑応答"},
    ],
    "design": [
        {"title": "設計レビューチェックリスト", "description": "非機能要件の観点"},
        {"title": "過去の設計事例集", "description": "類似案件の参照用"},
    ],
    "mfg": [
        {"title": "製造ライン安全手順書", "description": "始業前点検 / 緊急停止"},
        {"title": "工程管理マニュアル", "description": "歩留まり改善の考え方"},
    ],
    "ga": [
        {"title": "社内規程・申請フロー", "description": "経費精算 / 各種届出"},
        {"title": "福利厚生ガイド", "description": "制度一覧と利用手順"},
    ],
}
