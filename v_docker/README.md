# Lokal AI Kod Denetim Ajanı — Docker Kurulumu

Ana kurulumun Docker versiyonu. Tek komutla tüm servisler ayağa kalkar.

## Gereksinimler

- Docker Engine 24+
- Docker Compose v2+
- 20GB boş disk (modeller dahil ~11GB)

GPU desteği için:
- NVIDIA sürücüsü kurulu
- [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

## Servisler

| Servis | Açıklama | Port |
|--------|----------|------|
| `ollama` | AI model motoru | 11434 |
| `model-puller` | İlk açılışta modelleri indirir | — |
| `anythingllm` | PDF & RAG arayüzü | 3001 |
| `gitlab-reviewer` | GitLab webhook dinleyici | 5050 |

## Kurulum

### 1. Token dosyasını oluştur

```bash
cp .env.example .env
```

`.env` dosyasını düzenle:

```env
GITLAB_URL=http://gitlab.sirket.local
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
WEBHOOK_SECRET=gizli-anahtar-belirle
```

### 2. Başlat

```bash
docker compose up -d
```

İlk açılışta `model-puller` servisi otomatik olarak şunları indirir:
- `qwen2.5-coder:14b` (~9GB)
- `nomic-embed-text` (~274MB)

İndirme sürecini izlemek için:

```bash
docker compose logs -f model-puller
```

### 3. Kontrol

```bash
# Tüm servislerin durumu
docker compose ps

# Ollama'nın modelleri yükledi mi
curl http://localhost:11434/api/tags

# AnythingLLM arayüzü
# Tarayıcıda aç: http://localhost:3001
```

## GPU Desteği (Opsiyonel)

`docker-compose.yml` içinde `ollama` servisindeki `deploy` bloğunun yorumunu kaldır:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Ardından yeniden başlat:

```bash
docker compose up -d ollama
```

## GitLab Webhook Ayarı

Webhook dinleyici `http://<makine-ip>:5050/webhook` adresinde çalışır.

Makinenin IP'sini bulmak için:
```bash
hostname -I | awk '{print $1}'
```

GitLab'da her proje için:
1. **Settings → Webhooks → Add new webhook**
2. URL: `http://<makine-ip>:5050/webhook`
3. Secret token: `.env` dosyasındaki `WEBHOOK_SECRET`
4. Trigger: sadece `Push events`

## Log Takibi

```bash
# Canlı log
tail -f logs/kod_inceleme.log

# Veya Docker üzerinden
docker compose logs -f gitlab-reviewer
```

## Yönetim

```bash
# Durdur
docker compose down

# Modelleri silmeden durdur (volume'lar korunur)
docker compose down --volumes=false

# Güncelle
docker compose pull
docker compose up -d
```

## Sorun Giderme

**model-puller sürekli yeniden başlıyor:**
Ollama servisinin tam olarak ayağa kalkması için birkaç saniye gerekebilir, bu normaldir. `restart: "no"` ayarı sayesinde modeller indikten sonra durur.

**gitlab-reviewer Ollama'ya bağlanamıyor:**
`docker compose ps` ile `ollama` servisinin `healthy` olduğunu kontrol et.

**AnythingLLM model görmüyor:**
Settings → LLM Provider → Ollama → URL: `http://ollama:11434` (container adı kullan, localhost değil)
