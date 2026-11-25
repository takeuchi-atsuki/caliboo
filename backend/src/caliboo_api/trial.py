"""限定試用専用の起動入口。通常のローカル開発・共有DB起動とは独立する。"""

import base64
import hashlib
import hmac
import ipaddress
import os
import re
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from caliboo_api.auth.password import hash_password
from caliboo_api.data.account_data import initialize_profile, now_iso
from caliboo_api.db import bootstrap_db, get_engine, init_engine, session_scope
from caliboo_api.extension_models import AccountState
from caliboo_api.main import create_app
from caliboo_api.models import User

_TRIAL_MARKER = re.compile(r'<meta\s+name="caliboo-trial"\s+content="trial"\s*/?>')
# !NOTE: アプリの画面だけを許可し、未知APIパスやソース・成果物をHTMLにフォールバックしない。
_SPA_ROUTES = {
    "", "index.html", "login", "home", "password/reset", "password/change",
    "report", "ojt", "ojt/panel", "study", "study/chat", "assignments",
    "strengths", "strengths/poc", "admin/users", "admin/ojt",
    "admin/ojt-settings", "admin/agents",
}
_TRIAL_ACCOUNT_NAMES = (
    ("trial-instructor", "試用講師", "admin"),
    ("trial-member", "試用新人", "member"),
)
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class TrialConfigurationError(ValueError):
    """秘密値を含めない、試用専用の設定エラー。"""


def _require_isolation() -> None:
    # !NOTE: 既存DBや外部AIへの設定は上書きで隠さず、明示的に起動を中止する。
    for key, value in (
        ("CALIBOO_AI_PROVIDER", "manual"), ("CALIBOO_DEMO_SEED", "false"),
        ("CALIBOO_COOKIE_SECURE", "true"),
    ):
        if os.environ.get(key) != value:
            raise TrialConfigurationError(f"{key} must explicitly be set to {value}")
    for key in (
        "CALIBOO_DATABASE_URL", "CALIBOO_SQLITE_PATH", "OPENAI_API_KEY", "CALIBOO_AI_MODEL",
    ):
        if key in os.environ:
            raise TrialConfigurationError(f"{key} must be unset in trial mode")


def _secret(key: str, minimum: int, *, ascii_only: bool = False) -> str:
    value = os.environ.get(key, "")
    if (
        not minimum <= len(value) <= 128
        or not value.isprintable()
        or (ascii_only and not all(33 <= ord(char) <= 126 for char in value))
        or (value.startswith("<") and value.endswith(">"))
    ):
        raise TrialConfigurationError(f"{key} must contain a non-placeholder trial password")
    return value


def _read_origin() -> str:
    value = os.environ.get("CALIBOO_TRIAL_ORIGIN", "")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (
            not host
            or not re.fullmatch(r"https://[a-z0-9.\-:\[\]]+", value)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port in {0, 443}
        ):
            raise ValueError
        if ":" in host:
            canonical_host = f"[{ipaddress.IPv6Address(host).compressed}]"
        else:
            if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                   for label in host.split(".")):
                raise ValueError
            canonical_host = host
        canonical_port = f":{parsed.port}" if parsed.port is not None else ""
        if value != f"https://{canonical_host}{canonical_port}":
            raise ValueError
    except ValueError:
        raise TrialConfigurationError(
            "CALIBOO_TRIAL_ORIGIN must be a canonical HTTPS origin (without path or default port)"
        ) from None
    return value


def _proxy_networks(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    result = []
    for part in value.split(","):
        try:
            network = ipaddress.ip_network(part.strip())
        except ValueError:
            raise TrialConfigurationError(
                "CALIBOO_TRIAL_PROXY_IPS must identify trusted IPs/CIDRs"
            ) from None
        if network.prefixlen == 0:
            raise TrialConfigurationError(
                "CALIBOO_TRIAL_PROXY_IPS must not trust all network sources"
            )
        result.append(str(network) if "/" in part else str(network.network_address))
    return tuple(result)


@dataclass(frozen=True)
class TrialSettings:
    origin: str
    access_password: str = field(repr=False)
    instructor_password: str = field(repr=False)
    member_password: str = field(repr=False)
    proxy_ips: tuple[str, ...] = ()
    tls_certfile: Path | None = None
    tls_keyfile: Path | None = None
    port: int = 10000

    @classmethod
    def from_env(cls) -> "TrialSettings":
        _require_isolation()
        origin = _read_origin()
        access = _secret("CALIBOO_TRIAL_ACCESS_PASSWORD", 24, ascii_only=True)
        instructor = _secret("CALIBOO_TRIAL_INSTRUCTOR_PASSWORD", 16)
        member = _secret("CALIBOO_TRIAL_MEMBER_PASSWORD", 16)
        if len({access, instructor, member}) != 3:
            raise TrialConfigurationError(
                "Trial access/instructor/member passwords must be different"
            )

        proxy_ips = _proxy_networks(os.environ.get("CALIBOO_TRIAL_PROXY_IPS", ""))
        certificate = os.environ.get("CALIBOO_TRIAL_TLS_CERTFILE", "")
        key = os.environ.get("CALIBOO_TRIAL_TLS_KEYFILE", "")
        if proxy_ips:
            if certificate or key:
                raise TrialConfigurationError("Choose either trusted TLS proxy or direct TLS")
        elif not (
            certificate and key and Path(certificate).is_file() and Path(key).is_file()
        ):
            raise TrialConfigurationError(
                "Configure trusted TLS proxy IPs or direct TLS cert/key files"
            )
        try:
            port = int(os.environ.get("PORT", "10000"))
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise TrialConfigurationError("PORT must be a valid TCP port") from None
        return cls(
            origin=origin, access_password=access, instructor_password=instructor,
            member_password=member, proxy_ips=proxy_ips,
            tls_certfile=Path(certificate) if certificate else None,
            tls_keyfile=Path(key) if key else None, port=port,
        )


def _seed_trial_accounts(settings: TrialSettings) -> None:
    with session_scope() as session:
        for (login_id, display_name, role), password in zip(
            _TRIAL_ACCOUNT_NAMES, (settings.instructor_password, settings.member_password),
            strict=True,
        ):
            user = User(
                login_id=login_id, display_name=display_name, role=role,
                password_hash=hash_password(password), created_at=now_iso(),
            )
            session.add(user)
            session.flush()
            initialize_profile(session, user.id)
            session.add(AccountState(user_id=user.id, active=True))
        session.commit()


def _gate_digest(user_password: bytes) -> bytes:
    return hashlib.sha256(user_password).digest()


def _gate_authorized(header: str, expected: bytes) -> bool:
    scheme, sep, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not sep:
        return False
    try:
        supplied = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_gate_digest(supplied), expected)


def _validate_build(dist_dir: Path) -> Path:
    index = dist_dir / "index.html"
    if not (
        index.is_file() and (dist_dir / "assets").is_dir()
        and _TRIAL_MARKER.search(index.read_text(encoding="utf-8"))
    ):
        raise TrialConfigurationError(
            "Build frontend with npm run build -- --mode trial before startup"
        )
    return index


def _uncacheable(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def create_trial_app(settings: TrialSettings, dist_dir: Path) -> FastAPI:
    """試用限定の二段階アクセスと、プロセス専用のSQLiteを持つアプリ。"""
    index = _validate_build(dist_dir)

    @asynccontextmanager
    async def trial_lifespan(app: FastAPI):
        _require_isolation()
        # !NOTE: 永続領域や既存SQLiteには接続しない。プロセスの各起動で新規DBを作成する。
        with tempfile.TemporaryDirectory(prefix="caliboo-trial-") as directory:
            init_engine(str(Path(directory) / "trial.sqlite3"))
            try:
                bootstrap_db()
                _seed_trial_accounts(settings)
                app.state.trial_ready = True
                yield
            finally:
                app.state.trial_ready = False
                get_engine().dispose()

    app = create_app(trial_lifespan, include_docs=False)
    app.state.trial_ready = False
    gate_digest = _gate_digest(f"trial:{settings.access_password}".encode("ascii"))
    allowed_host = urlsplit(settings.origin).netloc

    @app.middleware("http")
    async def trial_gate(request: Request, call_next):
        if request.url.path == "/healthz" and request.method in {"GET", "HEAD"}:
            return _uncacheable(await call_next(request))
        # !NOTE: schemeは直接TLS接続または起動時に指定した信頼済みプロキシから得る。
        if request.url.scheme != "https" or request.headers.get("host", "").lower() != allowed_host:
            return _uncacheable(JSONResponse({"detail": "HTTPS origin required"}, 403))
        if not _gate_authorized(request.headers.get("authorization", ""), gate_digest):
            return _uncacheable(JSONResponse(
                {"detail": "trial access required"}, 401,
                headers={"WWW-Authenticate": 'Basic realm="Caliboo trial", charset="UTF-8"'},
            ))
        if request.method not in _SAFE_METHODS and request.headers.get("origin") != settings.origin:
            return _uncacheable(JSONResponse({"detail": "same-origin request required"}, 403))
        return _uncacheable(await call_next(request))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # 試用中の入力値（パスワード等）をエラーレスポンスへ含めない。
        return JSONResponse({"detail": "invalid request"}, status_code=422)

    @app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
    async def health() -> JSONResponse:
        if not app.state.trial_ready:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"})

    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="trial-assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if path not in _SPA_ROUTES and not re.fullmatch(r"assignments/(?:proposals/)?\d+", path):
            raise HTTPException(404, "not found")
        return FileResponse(index, media_type="text/html")

    return app


def main() -> None:
    try:
        settings = TrialSettings.from_env()
        dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        app = create_trial_app(settings, dist_dir)
    except TrialConfigurationError as exc:
        raise SystemExit(f"Trial startup refused: {exc}") from None
    except (OSError, RuntimeError, ValueError):
        # !NOTE: 外部ライブラリ等の例外詳細には設定値が含まれ得るため表示しない。
        raise SystemExit(
            "Trial startup refused: trial configuration or build unavailable"
        ) from None
    uvicorn.run(
        app,
        host="0.0.0.0" if settings.proxy_ips else "127.0.0.1",
        port=settings.port, workers=1, reload=False, lifespan="on",
        proxy_headers=bool(settings.proxy_ips),
        forwarded_allow_ips=list(settings.proxy_ips),
        ssl_certfile=str(settings.tls_certfile) if settings.tls_certfile else None,
        ssl_keyfile=str(settings.tls_keyfile) if settings.tls_keyfile else None,
        access_log=False, server_header=False,
    )


if __name__ == "__main__":
    main()
