# Caliboo マスコット 3D モデル

既存の `frontend/src/components/mascot/Mascot.tsx` の happy 表情を参考に、ミント色の顔・2つの耳・黒い目と白い光・ピンクの頬・笑顔を立体化した。

## 生成と検証

リポジトリのルートから実行する。Python 標準ライブラリ以外は不要。

```bash
python3 devel/poc_takeuchi/model/generate.py
python3 devel/poc_takeuchi/model/generate.py --verify-only
```

生成先はこのディレクトリと `frontend/src/assets/takeuchi/`。両方の `mascot.obj` と `mascot.mtl` を同じ内容にする。検証では書き出した OBJ/MTL を再読込し、すべての座標の有限性、三角形の頂点参照、退化面がないこと、使用マテリアルの存在を確認する。

!NOTE: OBJ は他の3Dツールでも直接読み込める形式とし、同じメッシュをフロントエンド配信用にも配置した。ビューアは描画時に OBJ/MTL を読み込むため、生成結果がそのまま表示される。

## 表示

```bash
cd frontend
npm run dev
```

ブラウザで `http://localhost:5173/takeuchi-model.html` を開く。ドラッグで回転、ホイールで拡大・縮小できる。ビューアは外部 CDN や追加パッケージを使わず、Canvas に OBJ の三角形を投影して描く。

## 配布用ビルド

`frontend` で `npm run build` を実行すると、通常のアプリに加えて `dist/takeuchi-model.html` とモデル資産を生成する。`npm run preview` の `/takeuchi-model.html` でも閲覧できる。OBJ/MTLはViteのURL importで参照し、開発用の `/src/` パスに依存しない。

## 形状の調整

顔と耳などは `generate.py` の `build()`、口は `Mesh.smile()`、色は `MATERIALS` で変更し、生成コマンドを再実行する。
