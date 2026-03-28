"""
GitLab Push Webhook → Ollama Kod İncelemesi → Log Dosyası
Docker ortamı için — tüm ayarlar ortam değişkenlerinden okunur.
"""

import json
import os
import requests
from datetime import datetime
from flask import Flask, request, abort

app = Flask(__name__)

# --- AYARLAR (ortam değişkenlerinden) ---
GITLAB_URL     = os.environ.get("GITLAB_URL", "http://gitlab.sirket.local")
GITLAB_TOKEN   = os.environ.get("GITLAB_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
OLLAMA_URL     = os.environ.get("OLLAMA_URL", "http://ollama:11434/api/generate")
OLLAMA_MODEL   = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")
LOG_FILE       = os.environ.get("LOG_FILE", "/logs/kod_inceleme.log")
MAX_DIFF_CHARS = 8000
# ----------------------------------------

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log_yaz(icerik: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(icerik + "\n")


def diff_getir(project_id: int, commit_sha: str) -> str:
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/diff"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        parcalar = []
        for d in r.json():
            parcalar.append(f"### {d.get('new_path', d.get('old_path'))}\n{d.get('diff', '')}")
        return "\n".join(parcalar)[:MAX_DIFF_CHARS]
    except Exception as e:
        return f"[Diff alınamadı: {e}]"


def ollama_incele(diff: str, pusher: str, branch: str) -> str:
    prompt = f"""Sen bir kod inceleme uzmanısın. Aşağıdaki Git diff'ini incele ve kısa bir değerlendirme yap.

Dikkat et:
- Naming convention ihlalleri (Türkçe/İngilizce karışımı, camelCase vs snake_case tutarsızlığı)
- SOLID prensiplerine aykırılıklar
- Güvenlik açıkları (hardcoded şifre, SQL injection riski vb.)
- Gereksiz tekrar veya kötü pratikler
- Commit mesajının açıklayıcı olup olmadığı

Push yapan: {pusher}
Branch: {branch}

--- DIFF BAŞLANGICI ---
{diff}
--- DIFF SONU ---

Kısa ve net değerlendirmeni Türkçe yaz. Sorun yoksa "Kod standartlara uygun görünüyor." de."""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300,
        )
        r.raise_for_status()
        return r.json().get("response", "[Yanıt alınamadı]")
    except Exception as e:
        return f"[Ollama hatası: {e}]"


@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET:
        gelen_token = request.headers.get("X-Gitlab-Token", "")
        if gelen_token != WEBHOOK_SECRET:
            abort(403)

    payload = request.get_json(silent=True)
    if not payload:
        abort(400)

    event = request.headers.get("X-Gitlab-Event", "")
    if event != "Push Hook":
        return "OK", 200

    pusher     = payload.get("user_name", "bilinmiyor")
    branch     = payload.get("ref", "").replace("refs/heads/", "")
    project_id = payload.get("project", {}).get("id")
    repo_name  = payload.get("project", {}).get("name", "bilinmiyor")
    commits    = payload.get("commits", [])

    if not commits or not project_id:
        return "OK", 200

    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ayrac = "=" * 70

    for commit in commits:
        sha      = commit.get("id", "")
        mesaj    = commit.get("message", "").strip()
        dosyalar = commit.get("added", []) + commit.get("modified", []) + commit.get("removed", [])

        log_yaz(f"\n{ayrac}")
        log_yaz(f"Tarih     : {zaman}")
        log_yaz(f"Repo      : {repo_name}")
        log_yaz(f"Branch    : {branch}")
        log_yaz(f"Pusher    : {pusher}")
        log_yaz(f"Commit    : {sha[:8]} — {mesaj}")
        log_yaz(f"Değişenler: {', '.join(dosyalar) if dosyalar else '(yok)'}")
        log_yaz(ayrac)

        diff = diff_getir(project_id, sha)
        inceleme = ollama_incele(diff, pusher, branch)

        log_yaz("--- AI İNCELEME ---")
        log_yaz(inceleme)
        log_yaz(ayrac + "\n")

    return "OK", 200


if __name__ == "__main__":
    print(f"Webhook dinleyici başlatılıyor → http://0.0.0.0:5050/webhook")
    print(f"Log dosyası: {LOG_FILE}")
    print(f"Ollama: {OLLAMA_URL}")
    app.run(host="0.0.0.0", port=5050, debug=False)
