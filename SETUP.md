# Kurulum Adımları — Sıfırdan Kurulum Rehberi

Bu belgede sistemin sıfırdan kurulumu adım adım anlatılmaktadır.
Tüm adımlar bu makinede test edilmiş ve çalışır durumda olduğu doğrulanmıştır.

**Test Edilen Sistem:**
- HP Z2 Tower G4 Workstation
- Intel Xeon E-2144G @ 3.60GHz (8 çekirdek)
- 32GB RAM
- NVIDIA Quadro P620 (2GB VRAM — GPU kullanılmıyor, CPU modu)
- Ubuntu Linux
- 500GB disk

---

## 1. Ollama Kurulumu

### 1.1 Kur

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 1.2 GPU'yu Devre Dışı Bırak

> Quadro P620'nin 2GB VRAM'i 14B model için yetersiz, SIGSEGV hatası verir.
> Bu adım bu donanım için **zorunludur.** Farklı bir GPU varsa atlanabilir.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="CUDA_VISIBLE_DEVICES="' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

### 1.3 Modelleri İndir

```bash
# Kod denetim modeli (~9GB, uzun sürebilir)
ollama pull qwen2.5-coder:14b

# RAG embedding modeli (~274MB)
ollama pull nomic-embed-text
```

### 1.4 Test Et

```bash
ollama run qwen2.5-coder:14b "Merhaba, çalışıyor musun?"
```

Yanıt geliyorsa `/bye` ile çık.

---

## 2. AnythingLLM Kurulumu

### 2.1 İndir

```bash
curl -L -o AnythingLLMDesktop.AppImage https://cdn.anythingllm.com/latest/AnythingLLMDesktop.AppImage
chmod +x AnythingLLMDesktop.AppImage
```

### 2.2 Başlat

```bash
./AnythingLLMDesktop.AppImage --no-sandbox
```

### 2.3 Kurulum Sihirbazı

Uygulama ilk açılışta kurulum sihirbazı başlatır:

1. **Data Handling & Privacy** ekranı → Next
2. **Email** ekranı → Skip (zorunlu değil)
3. **Workspace** ekranı → istediğin ismi yaz (örn: "Kod Standartları") → Create

### 2.4 Ollama Bağlantısı

Sol alt köşedeki **ingiliz anahtarı (Settings)** ikonuna tıkla:

- **LLM Preference** → Provider: `Ollama` → URL: `http://127.0.0.1:11434` → Model: `qwen2.5-coder:14b` → Save
- **Embedding Preference** → Provider: `Ollama` → Model: `nomic-embed-text` → Save

### 2.5 Test Et

Workspace sohbetine yaz: `Merhaba, çalışıyor musun?`

Yanıt geliyorsa bağlantı çalışıyor.

### 2.6 PDF Standartlarını Yükle (Opsiyonel)

Workspace ekranında upload ikonuna tıklayıp PDF dosyalarını sürükle-bırak.
AnythingLLM dosyaları otomatik olarak vektör veritabanına ekler.

---

## 3. Continue.dev Kurulumu (VS Code)

### 3.1 Extension'ı Kur

```bash
code --install-extension Continue.continue
```

Veya VS Code → Extensions (`Ctrl+Shift+X`) → `Continue` ara → Kur

### 3.2 Ollama'ya Bağla

`~/.continue/config.yaml` dosyasını şu içerikle güncelle:

```yaml
name: Local Config
version: 1.0.0
schema: v1

models:
  - name: Qwen Coder (Local)
    provider: ollama
    model: qwen2.5-coder:14b
    apiBase: http://localhost:11434

tabAutocomplete:
  - name: Qwen Coder Autocomplete
    provider: ollama
    model: qwen2.5-coder:14b
    apiBase: http://localhost:11434
```

### 3.3 VS Code'u Yeniden Başlat

Sol panelde Continue simgesi çıkacak. `Ctrl+L` ile chat panelini aç.

---

## 4. GitLab Webhook Kurulumu

### 4.1 Bağımlılıkları Kur

```bash
pip install flask requests
```

### 4.2 Token Ayarla

```bash
echo 'export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
echo 'export WEBHOOK_SECRET="gizli-anahtar"' >> ~/.bashrc
source ~/.bashrc
```

### 4.3 GitLab URL'sini Düzenle

`gitlab_reviewer.py` dosyasının 12. satırındaki `GITLAB_URL` değerini güncelle:

```python
GITLAB_URL = "http://gitlab.sirket.local"
```

### 4.4 Webhook Dinleyiciyi Başlat

```bash
cd /home/kullanici/Projeler/localAI
python gitlab_reviewer.py
```

### 4.5 GitLab'da Webhook Ekle

Makinenin IP'sini bul:
```bash
hostname -I | awk '{print $1}'
```

Her proje için GitLab → **Settings → Webhooks → Add new webhook:**
- URL: `http://<makine-ip>:5050/webhook`
- Secret token: `WEBHOOK_SECRET` değerin
- Trigger: sadece `Push events`

### 4.6 Servis Olarak Çalıştır (Opsiyonel)

Makine yeniden başladığında otomatik devreye girsin:

```bash
sudo nano /etc/systemd/system/ai-reviewer.service
```

```ini
[Unit]
Description=AI GitLab Kod İnceleyici
After=network.target

[Service]
User=celikada
WorkingDirectory=/home/celikada/Projeler/localAI
Environment="GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx"
Environment="WEBHOOK_SECRET=gizli-anahtar"
ExecStart=/usr/bin/python3 gitlab_reviewer.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ai-reviewer
sudo systemctl start ai-reviewer
```

### 4.7 Log Takibi

```bash
tail -f /home/celikada/Projeler/localAI/kod_inceleme.log
```

---

## Kurulum Sonrası Kontrol Listesi

- [ ] `ollama list` → qwen2.5-coder:14b ve nomic-embed-text görünüyor
- [ ] `curl http://localhost:11434/api/tags` → JSON yanıt geliyor
- [ ] AnythingLLM açık ve sohbet çalışıyor
- [ ] VS Code → Continue.dev simgesi sol panelde görünüyor
- [ ] `Ctrl+L` ile Continue.dev chat açılıyor
- [ ] `gitlab_reviewer.py` çalışıyor (veya systemd servisi aktif)

---

## Sorun Giderme

**SIGSEGV / model yüklenemiyor:**
```bash
echo -e '[Service]\nEnvironment="CUDA_VISIBLE_DEVICES="' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

**Ollama bağlanmıyor:**
```bash
curl http://localhost:11434/api/tags
sudo systemctl status ollama
```

**AnythingLLM model görmüyor:**
- Ollama'nın çalıştığından emin ol
- URL olarak `http://127.0.0.1:11434` kullan (`localhost` yerine)

**AnythingLLM yeniden başlatma:**
```bash
./AnythingLLMDesktop.AppImage --no-sandbox
```
