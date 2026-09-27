"""開発用ユーザーアカウントのシードデータ。

!NOTE: パスワードは平文のまま定義しているが、開発環境専用のダミーアカウントである
       (`db.bootstrap_db()`投入時に`auth/password.py`の`hash_password()`でハッシュ化
       してから保存する。DBに平文パスワードが残ることは無い)。本番運用を想定した
       値ではなく、ユーザー追加・パスワード変更の手段は無い。
"""

USERS_SEED = [
    {
        "login_id": "yuki",
        "password": "caliboo-yuki",
        "display_name": "ユウキ",
        "role": "member",
    },
    {
        "login_id": "sora",
        "password": "caliboo-sora",
        "display_name": "ソラ",
        "role": "member",
    },
    {
        "login_id": "haruka",
        "password": "caliboo-haruka",
        "display_name": "ハルカ",
        "role": "member",
    },
    {
        "login_id": "sensei",
        "password": "caliboo-sensei",
        "display_name": "佐藤先生",
        "role": "admin",
    },
]
