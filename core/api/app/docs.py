"""Browsable documentation served by the API itself, for local runs and demos.

    /api/docs                      hub: links to everything below, and the markdown docs
    /api/docs/swagger              Swagger UI on contracts/openapi.yaml ("Try it out")
    /api/docs/redoc                ReDoc: the same contract, for reading
    /api/openapi.yaml              the contract file itself
    /api/docs/view/<section>/<p>   a markdown file rendered in the browser
    /api/docs/raw/<section>/<p>    a file as is (markdown, yaml, json, images...)

Sections: `repo` is the core repository (contracts/, docs/, every README and CLAUDE.md);
`workspace` is an optional folder of team notes (API_DOCS_WORKSPACE_DIR). Only whitelisted
file types are served, never outside those folders. Off unless API_DOCS_ENABLED=true:
production keeps it off. No Python dependency: the pages load Swagger UI, ReDoc and marked
from a CDN, like any static page.
"""

import html
import json
import mimetypes
import os
import re
from pathlib import Path

from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.urls import path

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "dist"}
SERVED = {
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".png",
    ".svg",
    ".jpg",
    ".jpeg",
    ".gif",
    ".dbml",
    ".sql",
    ".txt",
}
TITLES = {"repo": "Repo core/ (đi cùng code)", "workspace": "Tài liệu workspace (docs/)"}

CDN = {
    "swagger_css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css",
    "swagger_js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js",
    "redoc_js": "https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
    "marked_js": "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js",
    "md_css": "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css",
}

STYLE = """
:root { --bg:#fff; --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; --card:#f6f8fa; --link:#0969da; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#3d444d; --card:#151b23; --link:#4493f8; }
}
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
a { color: var(--link); text-decoration: none; } a:hover { text-decoration: underline; }
h1 { font-size: 26px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 28px 0 10px; }
.muted { color: var(--muted); }
.cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:12px; }
.card { display:block; border:1px solid var(--line); background:var(--card); border-radius:10px; padding:14px; }
.card b { display:block; font-size:16px; margin-bottom:4px; }
.files { columns: 2 320px; column-gap: 32px; padding-left: 18px; }
.files li { break-inside: avoid; margin: 2px 0; }
code, pre { background: var(--card); border:1px solid var(--line); border-radius:6px; }
code { padding: 1px 5px; } pre { padding: 12px; overflow:auto; }
form { display:grid; gap:8px; grid-template-columns: 1fr; max-width: 720px; }
input { font: inherit; padding: 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); }
button { font: inherit; padding: 8px 14px; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }
nav.top { padding: 10px 16px; border-bottom:1px solid var(--line); background:var(--card); }
"""

# Swagger UI and ReDoc style their own code blocks (light text on a dark box); the hub's
# `code, pre` rule would paint them light and hide the text. Their pages get only the nav bar.
VIEWER_STYLE = """
body { margin:0; background:#fff; }
nav.top { padding:10px 16px; border-bottom:1px solid #d1d9e0; background:#f6f8fa;
  font:15px/1.55 system-ui, sans-serif; }
nav.top a { color:#0969da; text-decoration:none; } nav.top a:hover { text-decoration:underline; }
"""


def _enabled() -> None:
    if not settings.API_DOCS["ENABLED"]:
        raise Http404("API docs are off (API_DOCS_ENABLED).")


def _roots() -> dict[str, Path]:
    roots = {"repo": Path(settings.API_DOCS["REPO_DIR"])}
    workspace = settings.API_DOCS["WORKSPACE_DIR"]
    if workspace and Path(workspace).is_dir():
        roots["workspace"] = Path(workspace)
    return roots


def _safe_file(section: str, rel: str) -> Path:
    root = _roots().get(section)
    if root is None:
        raise Http404("Unknown section.")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise Http404("No such file.")
    if (
        target.suffix.lower() not in SERVED
        or set(target.relative_to(root.resolve()).parts) & SKIP_DIRS
    ):
        raise Http404("This file type is not served.")
    if "environment" in target.name or target.name.startswith(".env"):
        raise Http404("Environment files may hold tokens; not served.")
    return target


def _markdown_files(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            if name.lower().endswith(".md"):
                found.append(Path(current, name).relative_to(root).as_posix())
    return found


def _page(title: str, body: str, head: str = "", style: str = STYLE) -> HttpResponse:
    return HttpResponse(
        f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>{style}</style>{head}</head>
<body>{body}</body></html>"""
    )


def hub(request: HttpRequest) -> HttpResponse:
    _enabled()
    sections = []
    for key, root in _roots().items():
        items = "".join(
            f'<li><a href="/api/docs/view/{key}/{html.escape(p)}">{html.escape(p)}</a></li>'
            for p in _markdown_files(root)
        )
        sections.append(f"<h2>{html.escape(TITLES[key])}</h2><ul class='files'>{items}</ul>")
    if "workspace" not in _roots():
        sections.append(
            "<p class='muted'>Không thấy thư mục docs/ của workspace. Chạy bằng "
            "<code>python scripts/dev.py up</code> để nó được gắn vào (biến "
            "<code>WORKSPACE_DOCS_DIR</code>).</p>"
        )
    body = f"""<main>
<h1>Booking Core API: tài liệu</h1>
<p class="muted">Mọi thứ đọc từ repo đang chạy: contract <code>contracts/openapi.yaml</code> và các file markdown.
Chỉ bật ở môi trường local (<code>API_DOCS_ENABLED=true</code>).</p>

<h2>API</h2>
<div class="cards">
  <a class="card" href="/api/docs/swagger"><b>Swagger UI</b>Xem và gọi thử từng API (Try it out)</a>
  <a class="card" href="/api/docs/redoc"><b>ReDoc</b>Đọc toàn bộ contract, 3 cột, có tìm kiếm</a>
  <a class="card" href="/api/openapi.yaml"><b>openapi.yaml</b>File contract gốc, import vào Postman được</a>
  <a class="card" href="/api/healthz"><b>/api/healthz</b>API và database còn sống không</a>
</div>

<h2>Đăng nhập để gọi thử API</h2>
<p>Đăng nhập bằng <code>POST /api/v1/auth/login</code>, chọn công ty, rồi mở Swagger: mọi request tự mang
token và <code>X-Tenant-Id</code>. Tài khoản demo: <code>python scripts/dev.py seed</code> in ra email và mật khẩu.
Lưu trong trình duyệt này (token sống 15 phút; hết hạn thì đăng nhập lại).</p>
<form id="login">
  <input id="email" type="email" placeholder="email, ví dụ demo-abc123-owner@demo.test" autocomplete="username">
  <input id="password" type="password" placeholder="mật khẩu" autocomplete="current-password">
  <div><button type="submit">Đăng nhập</button> <span id="loginMsg" class="muted"></span></div>
</form>
<form id="pick" style="margin-top:12px">
  <select id="tenantSelect" style="font:inherit;padding:8px;border-radius:6px"></select>
  <div><button type="submit">Dùng công ty này và mở Swagger</button></div>
</form>
<details style="margin-top:12px"><summary class="muted">Hoặc dán token và tenantId (dev token, token khách)</summary>
<form id="auth" style="margin-top:8px">
  <input id="tenant" placeholder="tenantId (X-Tenant-Id)">
  <input id="token" placeholder="token (JWT, không cần chữ Bearer)">
  <div><button type="submit">Lưu và mở Swagger</button></div>
</form></details>

{"".join(sections)}
</main>
<script>
const $ = (id) => document.getElementById(id);
const store = (k, v) => {{ try {{ localStorage.setItem(k, v); }} catch (e) {{}} }};
const load = (k) => {{ try {{ return localStorage.getItem(k) || ""; }} catch (e) {{ return ""; }} }};
$("tenant").value = load("bc.tenant");
$("token").value = load("bc.token");
$("pick").style.display = "none";

async function showTenants(token) {{
  const r = await fetch("/api/v1/me/tenants", {{ headers: {{ Authorization: "Bearer " + token }} }});
  const list = r.ok ? (await r.json()).data : [];
  const sel = $("tenantSelect");
  sel.innerHTML = "";
  for (const t of list) {{
    const o = document.createElement("option");
    o.value = t.tenantId;
    o.textContent = `${{t.name}} (${{t.slug}}), ${{t.status}}`;
    if (t.tenantId === load("bc.tenant")) o.selected = true;
    sel.appendChild(o);
  }}
  $("pick").style.display = list.length ? "" : "none";
  $("loginMsg").textContent = list.length ? `Đã đăng nhập. Chọn công ty (${{list.length}}).` : "Đã đăng nhập, nhưng chưa thuộc công ty nào.";
}}

$("login").addEventListener("submit", async (e) => {{
  e.preventDefault();
  $("loginMsg").textContent = "Đang đăng nhập…";
  const r = await fetch("/api/v1/auth/login", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ email: $("email").value.trim(), password: $("password").value }}),
  }});
  const body = await r.json();
  if (!r.ok) {{ $("loginMsg").textContent = body.detail || body.title || "Đăng nhập thất bại"; return; }}
  store("bc.token", body.accessToken);
  store("bc.refresh", body.refreshToken || "");
  $("password").value = "";
  await showTenants(body.accessToken);
}});

$("pick").addEventListener("submit", (e) => {{
  e.preventDefault();
  store("bc.tenant", $("tenantSelect").value);
  location.href = "/api/docs/swagger";
}});

$("auth").addEventListener("submit", (e) => {{
  e.preventDefault();
  store("bc.tenant", $("tenant").value.trim());
  store("bc.token", $("token").value.trim().replace(/^Bearer\\s+/i, ""));
  location.href = "/api/docs/swagger";
}});
</script>"""
    return _page("Booking Core docs", body)


def swagger(request: HttpRequest) -> HttpResponse:
    _enabled()
    body = f"""<nav class="top"><a href="/api/docs">← Tài liệu</a></nav>
<div id="ui"></div>
<script src="{CDN["swagger_js"]}"></script>
<script>
let tenant = "", token = "";
try {{
  tenant = localStorage.getItem("bc.tenant") || "";
  token = localStorage.getItem("bc.token") || "";
  // Swagger's own saved auth from an earlier version of this page could be malformed and
  // leave every operation spinning; the token lives in bc.token instead.
  localStorage.removeItem("authorized");
}} catch (e) {{}}
// No parameterMacro: with an OpenAPI 3.1 spec it breaks Swagger UI 5 ("Invalid value used as
// weak map key"), leaving every operation with path or query parameters spinning. Instead
// the page loads a copy of the contract where X-Tenant-Id and Idempotency-Key are optional,
// and fills them (and the token) on the way out. Values typed in the form win.
SwaggerUIBundle({{
  url: "/api/docs/openapi.swagger.yaml",
  dom_id: "#ui",
  deepLinking: true,
  displayRequestDuration: true,
  filter: true,
  docExpansion: "list",
  requestInterceptor: (req) => {{
    const h = req.headers;
    // "Try it out" pre-fills the box with the contract's example UUID: treat that as empty.
    if (tenant && (!h["X-Tenant-Id"] || h["X-Tenant-Id"] === {json.dumps(_uuid_example())}))
      h["X-Tenant-Id"] = tenant;
    if (token && !h["Authorization"]) h["Authorization"] = "Bearer " + token;
    const path = new URL(req.url, location.href).pathname;
    if (req.method === "POST" && path.endsWith("/api/v1/bookings") && !h["Idempotency-Key"])
      h["Idempotency-Key"] = crypto.randomUUID();
    return req;
  }},
}});
</script>"""
    return _page(
        "Booking Core API (Swagger)",
        body,
        f'<link rel="stylesheet" href="{CDN["swagger_css"]}">',
        style=VIEWER_STYLE,
    )


def redoc(request: HttpRequest) -> HttpResponse:
    _enabled()
    body = f"""<nav class="top"><a href="/api/docs">← Tài liệu</a></nav>
<div id="redoc"></div>
<script src="{CDN["redoc_js"]}"></script>
<script>Redoc.init("/api/openapi.yaml", {{ hideDownloadButton: false, expandResponses: "200,201" }}, document.getElementById("redoc"));</script>"""
    return _page("Booking Core API (ReDoc)", body, style=VIEWER_STYLE)


def contract(request: HttpRequest) -> FileResponse:
    _enabled()
    target = _safe_file("repo", "contracts/openapi.yaml")
    return FileResponse(open(target, "rb"), content_type="application/yaml; charset=utf-8")


def _uuid_example() -> str:
    """The example of components.schemas.Uuid, which Swagger puts in empty UUID boxes."""
    text = _safe_file("repo", "contracts/openapi.yaml").read_text("utf-8")
    found = re.search(
        r"\n    Uuid:\n(?:      .*\n)*?      example: \"([^\"]+)\"", text.replace("\r\n", "\n")
    )
    return found.group(1) if found else ""


# Headers the Swagger page fills by itself; required in the contract, optional in its copy.
_AUTO_FILLED = ("TenantId", "IdempotencyKey")


def swagger_contract(request: HttpRequest) -> HttpResponse:
    """The contract for the Swagger page only: X-Tenant-Id and Idempotency-Key not required,
    so an empty box does not block "Execute" (the page adds them). Text edit of the two
    component blocks, so the rest of the file is served byte for byte."""
    _enabled()
    text = _safe_file("repo", "contracts/openapi.yaml").read_text("utf-8").replace("\r\n", "\n")
    for name in _AUTO_FILLED:
        text = re.sub(
            rf"(\n    {name}:\n(?:      .*\n)*?)      required: true\n",
            r"\1      required: false\n",
            text,
            count=1,
        )
    # Without an example, "Try it out" leaves UUID boxes empty instead of filling optional
    # filters (subjectId, siteId...) with a made-up id that matches nothing.
    text = re.sub(r"(\n    Uuid:\n(?:      .*\n)*?)      example: .*\n", r"\1", text, count=1)
    return HttpResponse(text, content_type="application/yaml; charset=utf-8")


def raw(request: HttpRequest, section: str, rel: str) -> FileResponse:
    _enabled()
    target = _safe_file(section, rel)
    kind = mimetypes.guess_type(target.name)[0] or "text/plain"
    if kind.startswith("text/") or target.suffix in {".md", ".yaml", ".yml", ".dbml", ".sql"}:
        kind = f"{'text/markdown' if target.suffix == '.md' else 'text/plain'}; charset=utf-8"
    return FileResponse(open(target, "rb"), content_type=kind)


def view(request: HttpRequest, section: str, rel: str) -> HttpResponse:
    _enabled()
    target = _safe_file(section, rel)
    if target.suffix.lower() != ".md":
        return HttpResponseRedirect(f"/api/docs/raw/{section}/{rel}")
    body = f"""<nav class="top"><a href="/api/docs">← Tài liệu</a> · <span class="muted">{html.escape(section)}/{html.escape(rel)}</span>
 · <a href="/api/docs/raw/{section}/{html.escape(rel)}">raw</a></nav>
<main><article class="markdown-body" id="doc">Đang tải…</article></main>
<script src="{CDN["marked_js"]}"></script>
<script>
const section = {json.dumps(section)}, rel = {json.dumps(rel)};
const dir = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/") + 1) : "";
function resolve(href) {{
  const parts = (dir + href).split("/"), out = [];
  for (const p of parts) {{ if (p === "..") out.pop(); else if (p !== ".") out.push(p); }}
  return out.join("/");
}}
const slug = (t) => t.toLowerCase().trim().replace(/[^\\p{{L}}\\p{{N}}\\s-]/gu, "").replace(/\\s/g, "-");
fetch(`/api/docs/raw/${{section}}/${{rel}}`).then(r => r.text()).then(md => {{
  const doc = document.getElementById("doc");
  doc.innerHTML = marked.parse(md);
  doc.querySelectorAll("h1,h2,h3,h4").forEach(h => {{ if (!h.id) h.id = slug(h.textContent); }});
  doc.querySelectorAll("a[href]").forEach(a => {{
    const href = a.getAttribute("href");
    if (/^(https?:|mailto:|#)/.test(href)) return;
    const [p, hash] = href.split("#");
    const target = resolve(p);
    if (target.startsWith("..")) return;
    a.href = (p.endsWith(".md") ? "/api/docs/view/" : "/api/docs/raw/") + section + "/" + target + (hash ? "#" + hash : "");
  }});
  doc.querySelectorAll("img[src]").forEach(img => {{
    const src = img.getAttribute("src");
    if (!/^(https?:|data:)/.test(src)) img.src = "/api/docs/raw/" + section + "/" + resolve(src);
  }});
  if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
}});
</script>"""
    head = (
        f'<link rel="stylesheet" href="{CDN["md_css"]}">'
        "<style>.markdown-body{background:transparent;font-size:15px}</style>"
    )
    return _page(target.name, body, head)


def to_hub(request: HttpRequest) -> HttpResponseRedirect:
    return HttpResponseRedirect("/api/docs")


urlpatterns = [
    path("api/docs", hub),
    path("api/docs/", to_hub),
    path("api/v1/docs", to_hub),
    path("api/docs/swagger", swagger),
    path("api/docs/redoc", redoc),
    path("api/openapi.yaml", contract),
    path("api/docs/openapi.swagger.yaml", swagger_contract),
    path("api/docs/view/<slug:section>/<path:rel>", view),
    path("api/docs/raw/<slug:section>/<path:rel>", raw),
]
