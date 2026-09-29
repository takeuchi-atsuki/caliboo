# Caliboo登録アカウント一覧

`list_users.py`はローカル開発サーバーの管理者APIから登録アカウントを読み取り、ID・ログインID・表示名・権限・有効状態・部署IDを表示します。ユーザー情報は変更しません。

> [!NOTE]
> ここでの「使用ユーザー」は登録アカウント一覧を指します。オンライン利用者や現在のセッション数は表示しません。`GET /api/users`が返すのは登録アカウントであり、接続状態ではないためです。

## 実行

開発サーバーを起動してから、管理者アカウントで実行します。パスワードは対話入力し、引数やファイルに保存しません。

```bash
python3 devel/poc_takeuchi/users/list_users.py --login-id sensei
```

公開開発シードを使うデモでは、対話入力を省略できます。

```bash
python3 devel/poc_takeuchi/users/list_users.py --demo
python3 devel/poc_takeuchi/users/list_users.py --demo --format json
```

接続先の既定値は`http://localhost:8000`です。`--base-url`で変更する場合も、ポート付きローカルHTTP URLだけを受け付けます。レスポンスの転送は許可せず、Cookieはメモリだけに保持して終了時にログアウトします。

認証失敗は`401`、一般ユーザーでの一覧取得は`403`と区別して表示し、終了コードは`1`です。サーバーの応答本文や入力したパスワードはエラーに表示しません。

## 検証

```bash
python3 -m unittest discover -s devel/poc_takeuchi/users -p 'test_*.py'
```
