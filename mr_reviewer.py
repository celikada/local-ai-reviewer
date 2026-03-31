"""
GitLab MR Otomatik Kod İnceleme Ajanı
Çalıştırmak için: python3 mr_reviewer.py
Model değiştirmek için: export OLLAMA_MODEL="qwen2.5-coder:32b"
"""

import os
import json
import time
import requests
from datetime import datetime

# --- AYARLAR ---
GITLAB_URL      = "https://gitlab.iotech.local"
GITLAB_TOKEN    = os.environ.get("GITLAB_TOKEN", "")
OLLAMA_URL      = "http://localhost:11434/api/generate"
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")  # ← model buradan değişir
POLL_INTERVAL   = 600          # saniye (10 dakika)
MAX_DIFF_CHARS  = 8000
HEDEF_NAMESPACE = "mmatss"     # sadece bu namespace'i incele, "" ise hepsini incele
STATE_FILE      = "/home/celikada/Projeler/localAI/mr_reviewed.json"
LOG_FILE        = "/home/celikada/Projeler/localAI/mr_inceleme.log"
AI_IMZA         = "AI kod inceleme ajanı tarafından otomatik oluşturulmuştur"  # yorum imzası
# ----------------

HEADERS = {
    "PRIVATE-TOKEN": GITLAB_TOKEN,
    "Content-Type": "application/json",
}

# Başlangıçta mevcut kullanıcı adını al (yorum kontrol için)
BOT_KULLANICI = ""


def log(mesaj: str):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    satir = f"[{zaman}] {mesaj}"
    print(satir)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


def bot_kullanici_getir() -> str:
    """Token sahibinin kullanıcı adını getir."""
    try:
        r = requests.get(f"{GITLAB_URL}/api/v4/user", headers=HEADERS, verify=False, timeout=10)
        r.raise_for_status()
        return r.json().get("username", "")
    except Exception as e:
        log(f"Kullanıcı bilgisi alınamadı: {e}")
        return ""


def state_oku() -> set:
    """Daha önce incelenen MR ID'lerini dosyadan oku."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def state_kaydet(incelenenler: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(incelenenler), f)


def mr_zaten_yorumlanmis_mi(project_id: int, mr_iid: int) -> bool:
    """GitLab'daki yorumlara bakarak bot daha önce yorum yazmış mı kontrol et."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    try:
        r = requests.get(url, headers=HEADERS, params={"per_page": 100}, verify=False, timeout=30)
        r.raise_for_status()
        for yorum in r.json():
            yazar = yorum.get("author", {}).get("username", "")
            icerik = yorum.get("body", "")
            # Bot'un yazdığı yorum mu? (kullanıcı adı veya imza ile kontrol)
            if yazar == BOT_KULLANICI and AI_IMZA in icerik:
                return True
        return False
    except Exception as e:
        log(f"Yorum kontrolü başarısız (proje {project_id}, MR {mr_iid}): {e}")
        return False


def mr_listesi_getir() -> list:
    """Tüm projelerdeki açık MR'ları getir."""
    url = f"{GITLAB_URL}/api/v4/merge_requests"
    params = {"scope": "all", "state": "opened", "per_page": 100}
    try:
        r = requests.get(url, headers=HEADERS, params=params, verify=False, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"MR listesi alınamadı: {e}")
        return []


def mr_diff_getir(project_id: int, mr_iid: int) -> str:
    """MR'ın diff'ini getir."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=30)
        r.raise_for_status()
        degisiklikler = r.json().get("changes", [])
        parcalar = []
        for d in degisiklikler:
            parcalar.append(f"### {d.get('new_path', d.get('old_path'))}\n{d.get('diff', '')}")
        return "\n".join(parcalar)[:MAX_DIFF_CHARS]
    except Exception as e:
        return f"[Diff alınamadı: {e}]"


def ollama_incele(diff: str, mr_baslik: str, yazar: str, kaynak_branch: str, hedef_branch: str) -> str:
    prompt = f"""Sen bir kıdemli yazılım mühendisisin ve kod inceleme yapıyorsun.
Aşağıdaki Merge Request'i incele ve yapıcı bir değerlendirme yap.

MR Başlığı: {mr_baslik}
Yazar: {yazar}
Kaynak Branch: {kaynak_branch} → Hedef Branch: {hedef_branch}

Şunlara dikkat et:
- Naming convention ihlalleri (Türkçe/İngilizce karışımı, tutarsız isimlendirme)
- SOLID prensiplerine aykırılıklar
- Güvenlik açıkları (hardcoded şifre, SQL injection, XSS vb.)
- Hata yönetimi eksiklikleri
- Gereksiz tekrar veya kötü pratikler
- Branch ve commit mesajlarının açıklayıcı olup olmadığı
- Mantıksal hatalar veya edge case'ler

--- DIFF BAŞLANGICI ---
{diff}
--- DIFF SONU ---

Değerlendirmeni şu formatta Türkçe yaz:

## Genel Değerlendirme
(1-2 cümle özet)

## Sorunlar
(varsa maddeler halinde, yoksa "Belirgin sorun tespit edilmedi.")

## Öneriler
(varsa maddeler halinde, yoksa "Ek öneri yok.")

---
*Bu yorum AI kod inceleme ajanı tarafından otomatik oluşturulmuştur. Model: {OLLAMA_MODEL}*"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=600,
        )
        r.raise_for_status()
        return r.json().get("response", "[Yanıt alınamadı]")
    except Exception as e:
        return f"[Ollama hatası: {e}]"


def mr_yorum_yaz(project_id: int, mr_iid: int, yorum: str) -> bool:
    """MR'a yorum gönder."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    try:
        r = requests.post(url, headers=HEADERS, json={"body": yorum}, verify=False, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"Yorum gönderilemedi (proje {project_id}, MR {mr_iid}): {e}")
        return False


def mr_incele(mr: dict, incelenenler: set) -> bool:
    """Tek bir MR'ı incele ve yorumla."""
    mr_id      = mr["id"]
    mr_iid     = mr["iid"]
    project_id = mr["project_id"]
    baslik     = mr["title"]
    yazar      = mr["author"]["username"]
    kaynak     = mr["source_branch"]
    hedef      = mr["target_branch"]
    mr_ref     = mr["references"]["full"]

    # 1. Local state dosyasına bak
    if mr_id in incelenenler:
        return False

    # 2. Namespace filtresi
    if HEDEF_NAMESPACE and not mr_ref.startswith(HEDEF_NAMESPACE + "/"):
        return False

    # 3. GitLab'da zaten yorum var mı kontrol et (dosya silinmiş olsa bile)
    if mr_zaten_yorumlanmis_mi(project_id, mr_iid):
        log(f"  → Atlandı (zaten yorumlandı): {mr_ref}")
        incelenenler.add(mr_id)
        state_kaydet(incelenenler)
        return False

    log(f"İnceleniyor: {mr_ref} — {baslik} ({yazar})")

    # Hemen işaretle — script kapansa bile tekrar incelemesin
    incelenenler.add(mr_id)
    state_kaydet(incelenenler)

    diff = mr_diff_getir(project_id, mr_iid)
    if not diff.strip():
        log(f"  → Diff boş, atlandı.")
        return True

    inceleme = ollama_incele(diff, baslik, yazar, kaynak, hedef)

    basarili = mr_yorum_yaz(project_id, mr_iid, inceleme)
    if basarili:
        log(f"  → Yorum yazıldı: {mr_ref}")

    return True


def main():
    global BOT_KULLANICI
    BOT_KULLANICI = bot_kullanici_getir()

    log(f"MR İnceleme Ajanı başlatıldı — Model: {OLLAMA_MODEL}")
    log(f"Bot kullanıcısı: {BOT_KULLANICI}")
    log(f"Tarama aralığı: {POLL_INTERVAL // 60} dakika")

    incelenenler = state_oku()
    log(f"State dosyasından yüklenen MR sayısı: {len(incelenenler)}")

    while True:
        log("--- Tarama başlıyor ---")
        mr_listesi = mr_listesi_getir()
        yeni_sayisi = 0

        for mr in mr_listesi:
            if mr_incele(mr, incelenenler):
                yeni_sayisi += 1
                time.sleep(5)

        log(f"--- Tarama bitti. Yeni incelenen: {yeni_sayisi} / Toplam MR: {len(mr_listesi)} ---")
        log(f"Sonraki tarama {POLL_INTERVAL // 60} dakika sonra...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
