"""ホーム画面のシードデータ(ユーザーごと)。

`home_profile`はユーザー1人につき1行(不変条件: 全ユーザーがhome_profileを1行持つ。
home/study progressがprofileを必須としているため)。`login_id`をキーに、`db.bootstrap_db()`が`users`投入後の
ユーザー行と突き合わせてINSERTする。

!NOTE: `yuki`は元々の単一ユーザー前提だった頃のシード値(streak 12、基本情報技術者68%、
       強み3種)をそのまま引き継ぐ。`sora`・`sensei`は、ユーザー間でデータが分離される
       ことをテスト・手動確認できるよう別の値にしている。`haruka`(#17でAIの課題案の
       動作確認用に追加した新入社員)も、全ユーザーがhome_profileを1行持つという
       不変条件を満たすため他と別の値を投入する。
"""

HOME_PROFILES_SEED = {
    "yuki": {
        "certification_name": "基本情報技術者",
        "achievement_percent": 68,
        "user_streak_days": 12,
        "strength1_label": "課題発見力",
        "strength1_tone": "purple",
        "strength2_label": "継続力",
        "strength2_tone": "green",
        "strength3_label": "チーム連携",
        "strength3_tone": "pink",
    },
    "sora": {
        "certification_name": "基本情報技術者",
        "achievement_percent": 20,
        "user_streak_days": 3,
        "strength1_label": "傾聴力",
        "strength1_tone": "green",
        "strength2_label": "丁寧さ",
        "strength2_tone": "blue",
        "strength3_label": "好奇心",
        "strength3_tone": "orange",
    },
    "haruka": {
        "certification_name": "基本情報技術者",
        "achievement_percent": 5,
        "user_streak_days": 1,
        "strength1_label": "素直さ",
        "strength1_tone": "purple",
        "strength2_label": "行動力",
        "strength2_tone": "green",
        "strength3_label": "向上心",
        "strength3_tone": "orange",
    },
    "sensei": {
        "certification_name": "基本情報技術者",
        "achievement_percent": 100,
        "user_streak_days": 0,
        "strength1_label": "指導力",
        "strength1_tone": "purple",
        "strength2_label": "傾聴力",
        "strength2_tone": "green",
        "strength3_label": "柔軟性",
        "strength3_tone": "blue",
    },
}
