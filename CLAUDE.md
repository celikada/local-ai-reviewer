# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje Amacı

İnternet bağlantısı olmadan çalışan, şirket içi GitLab'a bağlanan yerel AI kod denetim sistemi. Ekip üyelerinin push ettiği kodları Ollama üzerinden otomatik inceler, sonuçları log dosyasına yazar.

## Mimari

```
GitLab (push event) → gitlab_reviewer.py (:5050) → Ollama API (:11434) → kod_inceleme.log
                                                          ↓
                                                  qwen2.5-coder:14b
```

- **`gitlab_reviewer.py`** — Flask webhook sunucusu. GitLab push hook alır, commit diff'ini GitLab API'den çeker, Ollama'ya gönderir, yanıtı log'a yazar.
- **`v_docker/`** — Aynı sistemin Docker Compose versiyonu (başka makine için). `gitlab_reviewer.py` burada da var, fark: tüm ayarlar ortam değişkeninden okunur, `OLLAMA_URL` varsayılan olarak `http://ollama:11434` (container adı).
- **`AnythingLLMDesktop.AppImage`** — PDF standartlarını RAG ile sorgulamak için arayüz. Git'e dahil değil (.gitignore).

## Ortam Değişkenleri

`gitlab_reviewer.py` şu değişkenleri okur:

| Değişken | Açıklama |
|----------|----------|
| `GITLAB_TOKEN` | GitLab Personal Access Token (`read_api` scope) |
| `WEBHOOK_SECRET` | GitLab webhook secret token |

`GITLAB_URL` ve `OLLAMA_MODEL` doğrudan dosya içinde tanımlı — değiştirilecekse ilgili satırları düzenle.

## Webhook Sunucusunu Çalıştırma

```bash
pip install flask requests
python gitlab_reviewer.py
```

Sunucu `0.0.0.0:5050/webhook` adresinde dinler. Sadece `Push Hook` event'larını işler, diğerlerini yok sayar.

## Docker Versiyonu

```bash
cd v_docker
cp .env.example .env   # GITLAB_TOKEN ve WEBHOOK_SECRET doldur
docker compose up -d
```

İlk çalıştırmada `model-puller` servisi `qwen2.5-coder:14b` ve `nomic-embed-text` modellerini otomatik indirir.

## Donanım Notu

Bu repo HP Z2 Tower G4 (32GB RAM, Quadro P620 2GB VRAM) üzerinde geliştirildi. Quadro P620 için Ollama'nın GPU kullanımı devre dışı bırakılmıştır:

```
/etc/systemd/system/ollama.service.d/override.conf
→ Environment="CUDA_VISIBLE_DEVICES="
```

Farklı donanımda bu kısıtlamaya gerek olmayabilir.
