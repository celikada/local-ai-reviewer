"""
GitLab MR Otomatik Kod İnceleme Ajanı (Multi-Agent Destekli)
Çalıştırmak için: python3 mr_reviewer.py
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
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")
POLL_INTERVAL   = 600          # saniye (10 dakika)
MAX_DIFF_CHARS  = 8000
HEDEF_NAMESPACE = "mmatss"     # sadece bu namespace'i incele, "" ise hepsini incele
STATE_FILE      = "/home/celikada/Projeler/localAI/mr_reviewed.json"
LOG_FILE        = "/home/celikada/Projeler/localAI/mr_inceleme.log"
AGENT_DIR       = "/home/celikada/Projeler/localAI/.claude/agents"
AI_IMZA         = "AI kod inceleme ajanı tarafından otomatik oluşturulmuştur"
# ----------------

HEADERS = {
    "PRIVATE-TOKEN": GITLAB_TOKEN,
    "Content-Type": "application/json",
}

# Global değişkenler
BOT_KULLANICI = ""
AGENT_DATA = {}


def log(mesaj: str):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    satir = f"[{zaman}] {mesaj}"
    print(satir)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(satir + "\n")


def agents_yukle():
    """Agents klasöründeki tüm .md dosyalarını oku."""
    global AGENT_DATA
    if not os.path.exists(AGENT_DIR):
        log(f"Uyarı: Ajan dizini bulunamadı: {AGENT_DIR}")
        return

    for dosya in os.listdir(AGENT_DIR):
        if dosya.endswith(".md"):
            isim = dosya.replace(".md", "")
            yol = os.path.join(AGENT_DIR, dosya)
            try:
                with open(yol, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            content = parts[2].strip()
                    AGENT_DATA[isim] = content
            except Exception as e:
                log(f"Ajan yüklenemedi ({dosya}): {e}")
    log(f"{len(AGENT_DATA)} adet uzman ajan yüklendi.")


def alakali_ajanlari_sec(degisiklikler: list) -> tuple:
    """Değişen dosyalara göre ilgili ajanların talimatlarını ve isimlerini döndürür."""
    secilenler = set()
    
    # Her zaman dahil edilecek temel ajanlar
    if "software-architect" in AGENT_DATA: secilenler.add("software-architect")
    if "cybersecurity-expert" in AGENT_DATA: secilenler.add("cybersecurity-expert")

    for d in degisiklikler:
        path = d.get("new_path", "").lower()
        if path.endswith(".java") or "/src/main/" in path:
            secilenler.add("backend-developer")
        if ".sql" in path or "migration" in path:
            secilenler.add("database-expert")
        if any(x in path for x in ["docker", "jenkins", "gitlab-ci", ".yml", ".yaml"]):
            secilenler.add("devops-engineer")
        if path.endswith((".js", ".ts", ".vue", ".html", ".css")):
            secilenler.add("frontend-developer")
        if "test" in path:
            secilenler.add("tester")

    context = ""
    agent_names = sorted(list(secilenler))
    for ajan in agent_names:
        if ajan in AGENT_DATA:
            context += f"\n### {ajan.upper()} STANDARTLARI ###\n{AGENT_DATA[ajan]}\n"
    
    return context, agent_names


def bot_kullanici_getir() -> str:
    try:
        r = requests.get(f"{GITLAB_URL}/api/v4/user", headers=HEADERS, verify=False, timeout=10)
        r.raise_for_status()
        return r.json().get("username", "")
    except Exception as e:
        log(f"Kullanıcı bilgisi alınamadı: {e}")
        return ""


def state_oku() -> set:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except: pass
    return set()


def state_kaydet(incelenenler: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(incelenenler), f)


def mr_zaten_yorumlanmis_mi(project_id: int, mr_iid: int) -> bool:
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    try:
        r = requests.get(url, headers=HEADERS, params={"per_page": 100}, verify=False, timeout=30)
        r.raise_for_status()
        for yorum in r.json():
            yazar = yorum.get("author", {}).get("username", "")
            icerik = yorum.get("body", "")
            if yazar == BOT_KULLANICI and AI_IMZA in icerik:
                return True
        return False
    except Exception as e:
        log(f"Yorum kontrolü başarısız (proje {project_id}, MR {mr_iid}): {e}")
        return False


def mr_listesi_getir() -> list:
    url = f"{GITLAB_URL}/api/v4/merge_requests"
    params = {"scope": "all", "state": "opened", "per_page": 100}
    try:
        r = requests.get(url, headers=HEADERS, params=params, verify=False, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"MR listesi alınamadı: {e}")
        return []


def mr_diff_ve_degisiklik_getir(project_id: int, mr_iid: int):
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=30)
        r.raise_for_status()
        data = r.json()
        degisiklikler = data.get("changes", [])
        parcalar = []
        for d in degisiklikler:
            parcalar.append(f"### {d.get('new_path', d.get('old_path'))}\n{d.get('diff', '')}")
        return "\n".join(parcalar)[:MAX_DIFF_CHARS], degisiklikler
    except Exception as e:
        return f"[Diff alınamadı: {e}]", []


def ollama_incele(diff: str, mr_baslik: str, yazar: str, kaynak: str, hedef: str, ajan_standartlari: str) -> str:
    bugun = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""Sen çok kıdemli bir yazılım mimarı ve kod inceleme uzmanısın. 
Aşağıdaki Merge Request'i (MR) sana verilen uzman ajan standartlarına göre titizlikle incele ve profesyonel bir rapor hazırla.

**ÖNEMLİ: KESİNLİKLE TÜRKÇE YAZ VE AŞAĞIDAKİ FORMATI BİREBİR UYGULA.**

MR Bağlamı: {mr_baslik} (Yazar: {yazar}, {kaynak} -> {hedef})

{ajan_standartlari}

--- İNCELENECEK DIFF BAŞLANGICI ---
{diff}
--- İNCELENECEK DIFF SONU ---

Raporunu TAM OLARAK şu formatta oluştur:

# Kod İnceleme Raporu — {mr_baslik}

---

## Kritik Bulgular (Varsa)
(Hata, veri kaybı, güvenlik açığı veya thread leak gibi ciddi sorunlar)

### K-1 — (Bulgu Başlığı)
- **Konum**: `dosya_yolu:satır_no` (Eğer belliyse)
- **Sorun**: (Teknik detaylı açıklama)
- **Öneri**: 
  ```java
  // Varsa düzeltilmiş kod örneği
  ```

---

## Önemli Bulgular (Varsa)
(Kod kalitesi, performans veya idiomatik olmayan kullanımlar)

### O-1 — (Bulgu Başlığı)
- **Konum**: `dosya_yolu:satır_no`
- **Sorun**: (Açıklama)
- **Öneri**: (Çözüm yolu)

---

## Öneri Bulguları
(Style, naming, checkstyle veya ufak iyileştirmeler)

| # | Konum | Açıklama |
|---|---|---|
| R-1 | `dosya_yolu` | (Kısa açıklama) |

---

## Genel Değerlendirme

**Mimari**: (Genel mimari yapı hakkında yorum)

**Test Kapsamı**: (Varsa test dosyaları hakkında yorum)

**Sonuç**: (✅ Merge önerilir / ❌ Merge önerilmez / ⚠️ Düzeltmelerle merge edilebilir)

---
*Bu rapor AI kod inceleme ajanı tarafından dinamik uzman kuralları kullanılarak oluşturulmuştur. Model: {OLLAMA_MODEL}*"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL, 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "num_thread": 8
                }
            },
            timeout=7200,
        )
        r.raise_for_status()
        return r.json().get("response", "[Yanıt alınamadı]")
    except Exception as e:
        log(f"Ollama kritik hata: {e}")
        if "Read timed out" in str(e):
            return "Bunu review ederken kör oldum sanırım. Benden bu kadar :P \n\n*(Not: Kod değişikliği çok büyük olduğu için AI analiz süresi doldu.)*"
        return f"[Ollama hatası: {e}]"



def mr_yorum_yaz(project_id: int, mr_iid: int, yorum: str) -> bool:
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    try:
        r = requests.post(url, headers=HEADERS, json={"body": yorum}, verify=False, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"Yorum gönderilemedi (proje {project_id}, MR {mr_iid}): {e}")
        return False


def mr_incele(mr: dict, incelenenler: set) -> bool:
    mr_id      = mr["id"]
    mr_iid     = mr["iid"]
    project_id = mr["project_id"]
    baslik     = mr["title"]
    yazar      = mr["author"]["username"]
    kaynak     = mr["source_branch"]
    hedef      = mr["target_branch"]
    mr_ref     = mr["references"]["full"]

    if mr_id in incelenenler: return False
    if HEDEF_NAMESPACE and not mr_ref.startswith(HEDEF_NAMESPACE + "/"): return False

    # 1. GitLab Yorum Kontrolü
    if mr_zaten_yorumlanmis_mi(project_id, mr_iid):
        log(f"  → Atlandı (zaten yorumlandı): {mr_ref}")
        incelenenler.add(mr_id)
        state_kaydet(incelenenler)
        return False

    log(f"İnceleniyor: {mr_ref} — {baslik}")

    # 2. Diff ve Değişiklikleri Al
    diff, degisiklikler = mr_diff_ve_degisiklik_getir(project_id, mr_iid)
    if not diff.strip() or "[Diff alınamadı" in diff:
        log(f"  → Diff alınamadı veya boş, atlandı.")
        return False

    # 3. Ajanları Belirle ve Logla
    ajan_standartlari, secilen_ajanlar = alakali_ajanlari_sec(degisiklikler)
    log(f"  → Kullanılan Uzmanlar: {', '.join(secilen_ajanlar)}")

    # 4. İnceleme Öncesi State Kaydet (Mükerrerliği önlemek için)
    incelenenler.add(mr_id)
    state_kaydet(incelenenler)

    # 5. Ollama İncelemesi
    inceleme = ollama_incele(diff, baslik, yazar, kaynak, hedef, ajan_standartlari)

    # 6. AI Yorumunu Log Dosyasına Yaz
    log("-" * 40)
    log("--- AI İNCELEME SONUCU ---")
    log(inceleme)
    log("--- İNCELEME SONUCU BİTİŞİ ---")
    log("-" * 40)

    # 7. Yorum Yaz
    if mr_yorum_yaz(project_id, mr_iid, inceleme):
        log(f"  → Yorum GitLab'a gönderildi: {mr_ref}")
        return True

    return False


def main():
    global BOT_KULLANICI
    BOT_KULLANICI = bot_kullanici_getir()
    agents_yukle()

    log(f"MR İnceleme Ajanı (Multi-Agent Mode) başlatıldı — Model: {OLLAMA_MODEL}")
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
