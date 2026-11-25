#!/usr/bin/env python3
"""Caliboo Q&A: isolated rehearsal with the recorded AI output, no paid API."""
import argparse
import contextlib
from datetime import date,timedelta
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent
BASE="http://127.0.0.1:8000"

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def demo_environment(repo,state):
    env=os.environ.copy()
    env["PYTHONPATH"]=os.pathsep.join([str(repo/"backend/src"),env.get("PYTHONPATH","")])
    env["CALIBOO_SQLITE_PATH"]=str(state/"qa-demo.db")
    env["CALIBOO_AI_PROVIDER"]="manual"
    env["CALIBOO_DEMO_SEED"]="false"
    env["CALIBOO_COOKIE_SECURE"]="false"
    env["NO_PROXY"]="127.0.0.1,localhost"
    # No outbound provider calls are wanted in this demonstration.
    for key in list(env):
        if "OPENAI_API_KEY" in key.upper():
            env.pop(key,None)
    return env

def prepare(repo,state):
    if state.exists():
        raise SystemExit("既存ディレクトリは使いません。--state に新しいパスを指定してください。")
    if not (repo/"backend/src/caliboo_api/main.py").is_file():
        raise SystemExit("--repo に Caliboo のリポジトリルートを指定してください")
    state.mkdir(parents=True,mode=0o700)
    env=demo_environment(repo,state)
    suffix=secrets.token_hex(3)
    credentials={role:{"loginId":f"demo-{role}-{suffix}","password":secrets.token_urlsafe(18)}
                 for role in ("instructor","member")}
    # Credentials are sent only to a child process on this same computer, via stdin.
    code="""
import json,os,sys
from caliboo_api.db import init_engine,bootstrap_db,session_scope
from caliboo_api.auth.password import hash_password
from caliboo_api.data.account_data import initialize_profile,now_iso
from caliboo_api.extension_models import AccountState
from caliboo_api.models import User
init_engine(os.environ['CALIBOO_SQLITE_PATH'])
bootstrap_db()
credentials=json.load(sys.stdin)
with session_scope() as session:
    for role,name in (('instructor','講師（デモ）'),('member','新入社員（デモ）')):
        c=credentials[role]
        u=User(login_id=c['loginId'],display_name=name,role='admin' if role=='instructor' else 'member',
               password_hash=hash_password(c['password']),created_at=now_iso())
        session.add(u);session.flush();initialize_profile(session,u.id)
        session.add(AccountState(user_id=u.id,active=True))
    session.commit()
"""
    subprocess.run([sys.executable,"-c",code],env=env,input=json.dumps(credentials),text=True,check=True)
    data={"repo":str(repo),"credentials":credentials}
    file=state/"local-session.json"
    fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print("隔離されたデモ専用DBと役割を作成しました。通常のDBは使いません。")
    print("ローカルだけで使うデモ認証情報：")
    for role,c in credentials.items():print(f"{role}: {c['loginId']} / {c['password']}")
    print("認証情報を共有・公開しないでください。次は serve です。")

def state_data(state):
    if not (state/"qa-demo.db").is_file() or not (state/"local-session.json").is_file():
        raise SystemExit("先に prepare を実行してください。")
    d=read_json(state/"local-session.json")
    return Path(d["repo"]),d["credentials"]

def serve(state):
    repo,_=state_data(state)
    for port in (8000,5173):
        try:
            with socket.create_connection(("127.0.0.1",port),timeout=.5):
                raise SystemExit(f"ポート {port} は使用中です。他のアプリを停止してからやり直してください。")
        except ConnectionRefusedError:pass
    npm=shutil.which("npm.cmd" if os.name=="nt" else "npm")
    if not npm:raise SystemExit("npm が見つかりません。Calibooの開発環境を使用してください。")
    env=demo_environment(repo,state)
    processes=[]
    try:
        processes.append(subprocess.Popen([sys.executable,"-m","uvicorn","caliboo_api.main:app","--host","127.0.0.1","--port","8000"],cwd=repo/"backend",env=env))
        processes.append(subprocess.Popen([npm,"run","dev","--","--host","127.0.0.1","--strictPort"],cwd=repo/"frontend",env=env))
        print("起動先: http://127.0.0.1:5173/  | 停止: Ctrl+C",flush=True)
        while all(p.poll() is None for p in processes):time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:
            with contextlib.suppress(subprocess.TimeoutExpired):p.wait(timeout=5)

def api_session(c):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def api(path,data=None):
        request=urllib.request.Request(BASE+path,
            data=None if data is None else json.dumps(data,ensure_ascii=False).encode("utf8"),
            headers={"Content-Type":"application/json"},method="GET" if data is None else "POST")
        with opener.open(request,timeout=20) as response:return json.load(response)
    api("/api/auth/login",c)
    return api

def seed(state,both):
    _,creds=state_data(state)
    member=api_session(creds["member"])
    if member("/api/report/history")["history"]:
        raise SystemExit("既に日報があります。新しい --state で開始してください。")
    p1=read_json(HERE/"01-report-20261124.json")["request"].copy()
    p2=read_json(HERE/"02-report-browser.json")["request"].copy()
    p1["date"]=str(date.today()-timedelta(days=1))
    p2["date"]=str(date.today())
    print("前日の日報:",member("/api/report",p1))
    if both: print("当日の日報:",member("/api/report",p2))
    else:
        print("ブラウザの「日報」で次の架空の当日分を入力し、提出してください：")
        for key in ("keep","problem","try","moodComment"):print(f"{key}: {p2[key]}")

def replay(state):
    _,creds=state_data(state)
    member=api_session(creds["member"]);admin=api_session(creds["instructor"])
    user=member("/api/auth/me")["id"]
    listing=admin("/api/development/jobs")
    if listing.get("provider")!="manual":
        raise SystemExit("このデモは manual provider のみ対応です。")
    jobs=[j for j in listing["jobs"] if j["kind"]=="strength" and j["userId"]==user and j["status"]=="pending"]
    if not jobs:raise SystemExit("解析待ちジョブがありません。日報2件を提出してください。")
    job=max(jobs,key=lambda j:j["id"])
    path=f"/api/development/jobs/{job['id']}"
    current=admin(path)["materials"]
    observed=read_json(HERE/"03-material-export.json")["materials"]
    # Only replay the exact recorded synthetic material; dates may differ for tomorrow's exercise.
    def source_without_date(m):
        return {x["id"]:{k:v for k,v in x.items() if k!="date"} for x in m["sources"]}
    if current["schemaVersion"]!=observed["schemaVersion"] or source_without_date(current)!=source_without_date(observed):
        raise SystemExit("材料の内容・IDが実演時と異なります。収録済みのAI結果をこのジョブには取り込みません。")
    payload=read_json(HERE/"04-ai-analysis-retry.json")
    print("収録済み Codex 実AI応答を取り込み（このコマンド自体は再推論しません）:",admin(path+"/strength-result",payload))
    result=member("/api/development/strengths")
    print("承認前の本人表示件数:",len(result["candidates"]),"講師確認待ち:",result.get("reviewPending"))
    print("講師画面 > 強み > 対象者 > 根拠を見る > 承認して表示。架空デモの承認だけ行ってください。")

def verify(state):
    _,creds=state_data(state)
    member=api_session(creds["member"]);admin=api_session(creds["instructor"])
    user=member("/api/auth/me")["id"]
    for title,client,path in (("本人",member,"/api/development/strengths"),
                             ("講師",admin,f"/api/development/strengths?userId={user}")):
        result=client(path)
        print(title,"候補:",[(x["kind"],x["label"],x["status"]) for x in result["candidates"]])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["prepare","serve","seed","replay","verify"])
    p.add_argument("--repo",type=Path,default=HERE.parent.parent)
    p.add_argument("--state",required=True,type=Path,help="新規のデモ専用ディレクトリを指定")
    p.add_argument("--both",action="store_true",help="seed 時に2日分をAPIで投入")
    a=p.parse_args();state=a.state.expanduser().resolve();repo=a.repo.expanduser().resolve()
    if a.action=="prepare":prepare(repo,state)
    elif a.action=="serve":serve(state)
    elif a.action=="seed":seed(state,a.both)
    elif a.action=="replay":replay(state)
    elif a.action=="verify":verify(state)
