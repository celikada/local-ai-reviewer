# Lokal AI Kod Denetim Ajanı — Kurulum Rehberi

HP Z2 Workstation · 32GB RAM · Windows için hazırlanmıştır.

---

## Amaç

Git projelerindeki kodları şirket/ekip standartlarıyla karşılaştıran, PDF dokümanlarını referans alan, tamamen internet bağlantısı olmadan çalışan bir AI ajanı kurmak.

---

## Mimari

```
Git Repo (VS Code)
      │
      ▼
Continue.dev (VS Code extension)
      │  anlık kod denetimi
      ▼
Ollama  ←────────────────────────────────┐
  └─ qwen2.5-coder:14b (model)           │
      │                                  │
      ▼                                  │
AnythingLLM                              │
  └─ Standart PDF'leri (RAG ile)  ───────┘
  └─ Git repo analizi
```

---

## Adım 1 — Ollama Kurulumu

### 1.1 İndir ve Kur

[https://ollama.com](https://ollama.com) adresinden Windows installer'ı indir ve çalıştır.

### 1.2 Modeli İndir

PowerShell veya CMD'de:

```bash
ollama pull qwen2.5-coder:14b
```

> 32GB RAM ile bu model rahat çalışır (~9GB disk).
> İndirme uzun sürebilir, bekle.

### 1.3 GPU Devre Dışı Bırak (Quadro P620 için zorunlu)

Quadro P620'nin VRAM'i 2GB olduğundan 14B model GPU'ya sığmaz ve SIGSEGV hatası verir. Ollama'yı CPU modunda çalıştırmak için:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="CUDA_VISIBLE_DEVICES="' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

### 1.4 Test Et

```bash
ollama run qwen2.5-coder:14b "Merhaba, çalışıyor musun?"
```

Yanıt geliyorsa Ollama hazır. `/bye` ile çık.

### 1.5 Servis Olarak Başlat

Ollama kurulumdan sonra arka planda otomatik çalışır.
Manuel başlatmak için:

```bash
ollama serve
```

API adresi: `http://localhost:11434`

---

## Adım 2 — AnythingLLM Kurulumu

### 2.1 İndir ve Kur

[https://anythingllm.com](https://anythingllm.com) → "Download for Desktop" → Windows installer.

### 2.2 Ollama'ya Bağla

1. AnythingLLM'i aç
2. **Settings → LLM Provider** → `Ollama` seç
3. URL: `http://127.0.0.1:11434`
4. Model: `qwen2.5-coder:14b`
5. Kaydet

### 2.3 Embedding Modelini Ayarla

Embedding (RAG için gerekli):

```bash
ollama pull nomic-embed-text
```

AnythingLLM → **Settings → Embedding** → `Ollama` → `nomic-embed-text`

### 2.4 Workspace Oluştur

1. **+ New Workspace** → isim ver (örn: "Kod Standartları")
2. Bu workspace'e standart PDF'lerini yükle (sürükle-bırak)
3. AnythingLLM PDF'leri otomatik olarak vektör veritabanına atar

### 2.5 Standartları Test Et

Workspace sohbetinde sor:

```
Bu projedeki naming convention standartımız nedir?
```

PDF'ten ilgili bölümü bulup cevap veriyorsa RAG çalışıyor demektir.

---

## Adım 3 — VS Code + Continue.dev Kurulumu

### 3.1 Extension'ı Kur

VS Code → Extensions (Ctrl+Shift+X) → `Continue` ara → Kur

### 3.2 Ollama'ya Bağla

Continue kurulumundan sonra otomatik olarak Ollama'yı algılar.
Manuel ayar için `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen Coder (Local)",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen Coder Autocomplete",
    "provider": "ollama",
    "model": "qwen2.5-coder:14b"
  }
}
```

### 3.3 Kullanım

| Kısayol | İşlev |
|--------|-------|
| `Ctrl+L` | Chat panelini aç |
| Kod seç → `Ctrl+L` | Seçili kodu sohbete ekle |
| `Ctrl+I` | Kod üzerinde inline düzenleme |
| `@codebase` | Tüm projeyi tara |

---

## Adım 4 — Standart Denetimi Kullanımı

### AnythingLLM ile (PDF referanslı)

Workspace'te bir dosyayı yapıştır ve sor:

```
Bu kod dosyası standartlarımıza uyuyor mu?
Hangi kuralları ihlal ediyor, varsa belirt.
```

### Continue.dev ile (VS Code içinde)

Dosyayı seç → `Ctrl+L` → sor:

```
Bu fonksiyon SOLID prensiplerine uyuyor mu?
```

```
Bu sınıfı standartlarımıza göre gözden geçir ve yorum ekle.
```

```
@codebase bu projede hangi dosyalar naming convention'a uymuyor?
```

---

## Özet: Hangi Araç Ne İçin?

| Araç | Kullanım Amacı |
|------|---------------|
| **Ollama** | Modeli çalıştırır, motor görevi görür |
| **AnythingLLM** | PDF standartlarını yükle, repo analizi yap |
| **Continue.dev** | VS Code içinde anlık kod denetimi |

---

## Sorun Giderme

**Ollama bağlanmıyor:**
```bash
# Çalışıp çalışmadığını kontrol et
curl http://localhost:11434/api/tags
```

**Model yüklenemiyor / SIGSEGV hatası:**
- Quadro P620'nin 2GB VRAM'i 14B model için yetersiz, GPU'yu devre dışı bırak:
```bash
echo -e '[Service]\nEnvironment="CUDA_VISIBLE_DEVICES="' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

**Model çok yavaş:**
- CPU ile çalışması normaldir, Quadro P620 bu model için yetersiz VRAM'e sahip
- Daha küçük model dene: `ollama pull qwen2.5-coder:7b`

**AnythingLLM model görmüyor:**
- Ollama'nın çalıştığından emin ol (`ollama serve`)
- URL'yi kontrol et: `http://127.0.0.1:11434` (localhost yerine IP kullan)

---

## Adım 5 — GitLab Webhook ile Otomatik Kod Denetimi

Her push sonrasında AI otomatik olarak diff'i inceler ve sonucu `kod_inceleme.log` dosyasına yazar.

### Mimari Eklentisi

```
Ekip üyesi → git push
      │
      ▼
Şirket İçi GitLab
      │ webhook (push event)
      ▼
Bu Makine :5050/webhook  ←── gitlab_reviewer.py
      │ diff'i çeker (GitLab API)
      ▼
Ollama (qwen2.5-coder:14b)
      │ inceler
      ▼
kod_inceleme.log
```

### 5.1 Python Bağımlılıklarını Kur

```bash
pip install flask requests
```

### 5.2 GitLab Personal Access Token Oluştur

1. GitLab → sağ üst profil → **Edit Profile**
2. Sol menü → **Access Tokens**
3. Token adı: `ai-reviewer`
4. Scope: `read_api` (diff okumak için yeterli)
5. **Create personal access token** → tokeni kopyala

### 5.3 Ortam Değişkenlerini Ayarla

Token'ı asla dosyaya yazma, ortam değişkeni kullan:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
export WEBHOOK_SECRET="seçtiğin-gizli-anahtar"
```

Kalıcı olması için `~/.bashrc` veya `~/.zshrc` dosyasına ekle:

```bash
echo 'export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
echo 'export WEBHOOK_SECRET="seçtiğin-gizli-anahtar"' >> ~/.bashrc
source ~/.bashrc
```

### 5.4 GitLab URL'sini Düzenle

`gitlab_reviewer.py` dosyasının 12. satırındaki `GITLAB_URL` değerini şirket GitLab adresinle değiştir:

```python
GITLAB_URL = "http://gitlab.sirket.local"   # ← kendi adresin
```

### 5.5 Webhook Dinleyiciyi Başlat

```bash
cd /home/celikada/Projeler/localAI
python gitlab_reviewer.py
```

Başarılı çıktı:
```
Webhook dinleyici başlatılıyor → http://0.0.0.0:5050/webhook
Log dosyası: /home/celikada/Projeler/localAI/kod_inceleme.log
```

### 5.6 GitLab'da Webhook Ekle

Her denetlenmesini istediğin proje için:

1. GitLab → proje → **Settings → Webhooks**
2. **URL:** `http://<bu-makinenin-IP>:5050/webhook`
3. **Secret token:** 5.3'te belirlediğin `WEBHOOK_SECRET`
4. **Trigger:** sadece `Push events` işaretle
5. **Add webhook**

Bu makinenin IP'sini bulmak için:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

### 5.7 Log Dosyasını İzle

Canlı takip için:
```bash
tail -f /home/celikada/Projeler/localAI/kod_inceleme.log
```

### 5.8 Örnek Log Çıktısı

```
======================================================================
Tarih     : 2025-01-15 14:32:10
Repo      : backend-api
Branch    : feature/user-auth
Pusher    : ahmet.yilmaz
Commit    : a3f9c12b — kullanıcı girişi eklendi
Değişenler: src/auth/login.py, src/auth/token.py
======================================================================
--- AI İNCELEME ---
login.py'de 8. satırda hardcoded şifre tespit edildi: password="admin123".
Bu güvenlik açığı kapatılmalı, ortam değişkeni kullanılmalı.
token.py SOLID prensiplerine uygun görünüyor.
Commit mesajı yeterince açıklayıcı değil, daha detaylı yazılabilir.
======================================================================
```

### 5.9 Servis Olarak Çalıştır (Opsiyonel)

Makine yeniden başladığında otomatik devreye girsin:

```bash
sudo nano /etc/systemd/system/ai-reviewer.service
```

Dosya içeriği:
```ini
[Unit]
Description=AI GitLab Kod İnceleyici
After=network.target

[Service]
User=celikada
WorkingDirectory=/home/celikada/Projeler/localAI
Environment="GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx"
Environment="WEBHOOK_SECRET=seçtiğin-gizli-anahtar"
ExecStart=/usr/bin/python3 gitlab_reviewer.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ai-reviewer
sudo systemctl start ai-reviewer
```

---

## Özet: Hangi Araç Ne İçin? (Güncellenmiş)

| Araç | Kullanım Amacı |
|------|---------------|
| **Ollama** | Modeli çalıştırır, motor görevi görür |
| **AnythingLLM** | PDF standartlarını yükle, repo analizi yap |
| **Continue.dev** | VS Code içinde anlık kod denetimi |
| **gitlab_reviewer.py** | Ekip push'larını otomatik inceler, log'a yazar |

---

## Notlar

- Tüm veriler yerel kalır, internet bağlantısı gerekmez
- Modeller `~/.ollama/models` klasöründe saklanır (Linux)
- AnythingLLM veritabanı uygulama klasöründe tutulur, yedeklenebilir
- `GITLAB_TOKEN` ve `WEBHOOK_SECRET` asla kod içine yazılmamalı
