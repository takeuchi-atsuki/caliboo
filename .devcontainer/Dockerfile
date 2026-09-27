# ----------------------------------------
# Base image
# ----------------------------------------

FROM docker.io/library/python:3.12.13-slim

COPY --from=node /usr/local /usr/local

# ----------------------------------------
# TLSハンドシェイク遅延回避設定
# ----------------------------------------

COPY openssl-x25519.cnf /etc/ssl/openssl-x25519.cnf

ENV OPENSSL_CONF=/etc/ssl/openssl-x25519.cnf

# ----------------------------------------
# Claude Code の通信改善（WSL2 + MediaTek製Wi-Fiチップ)
# ----------------------------------------

RUN apt-get update \
&&  apt-get install -y ethtool

# ----------------------------------------
# Node.js 実行に必要な共有ライブラリ
# ----------------------------------------
# !NOTE: ベースイメージがpython:3.12-slimのため、COPY --from=nodeで
#        持ち込んだNode.jsバイナリの依存ライブラリ(libatomic1)が
#        含まれておらず、libatomic.so.1不足でnode/npmが起動できない。

RUN apt-get update \
&&  apt-get install -y libatomic1

# ----------------------------------------
# Python
# ----------------------------------------

COPY requirements.txt /tmp/

RUN --mount=type=cache,target=/root/.cache/pip,id=pip-py312,sharing=locked \
    python3 -m pip install --progress-bar off --upgrade pip \
&&  python3 -m pip install --root-user-action=ignore -r /tmp/requirements.txt \
&&  python3 -m pip install --root-user-action=ignore build
