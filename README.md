# Lokal AI Kod Denetim Ajanı

Git projelerindeki kodları şirket standartlarıyla karşılaştıran, PDF dokümanlarını referans alan, tamamen internet bağlantısı olmadan çalışan AI ajanı.

## Sistem Gereksinimleri

| Bileşen | Minimum |
|---------|---------|
| RAM | 16GB (32GB önerilen) |
| Disk | 20GB boş alan |
| OS | Linux (bu kurulum) veya Windows |
| GPU | Opsiyonel — yoksa CPU kullanır |

## Mimari

```
Git Repo (VS Code)
      │
      ▼
Continue.dev (VS Code extension)
      │  anlık kod denetimi
      ▼
Ollama  ←─────────────────────────────────────────┐
  └─ qwen2.5-coder:14b                            │
      │                                           │
      ├──────────────────────────────────────────►│
      ▼                                           │
AnythingLLM                                       │
  └─ Standart PDF'leri (RAG)                      │
  └─ Git repo analizi                             │
      │                                           │
Ekip push eder                                    │
      │                                           │
      ▼                                           │
gitlab_reviewer.py (:5050)  ───────────────────►──┘
  └─ kod_inceleme.log
```

## Kurulum

Ayrıntılı adımlar için: [local-ai-kurulum.md](local-ai-kurulum.md)

### Hızlı Başlangıç

```bash
# 1. Ollama kur
curl -fsSL https://ollama.com/install.sh | sh

# 2. Modelleri indir
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text

# 3. GPU'yu devre dışı bırak (Quadro P620 — 2GB VRAM yetersiz)
echo -e '[Service]\nEnvironment="CUDA_VISIBLE_DEVICES="' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama

# 4. Token'ları ayarla
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
export WEBHOOK_SECRET="gizli-anahtar"

# 4. Webhook dinleyiciyi başlat
pip install flask requests
python gitlab_reviewer.py
```

## Dosya Yapısı

```
localAI/
├── local-ai-kurulum.md     # Adım adım kurulum rehberi
├── gitlab_reviewer.py      # GitLab webhook dinleyici
├── kod_inceleme.log        # AI inceleme sonuçları (otomatik oluşur)
└── v_docker/               # Docker ile kurulum (başka makine için)
    ├── README.md
    ├── docker-compose.yml
    ├── Dockerfile
    ├── gitlab_reviewer.py
    ├── requirements.txt
    └── .env.example
```

## Araçlar

| Araç | Amaç | Port |
|------|------|------|
| Ollama | Model motoru | 11434 |
| AnythingLLM | PDF & RAG arayüzü | 3001 |
| Continue.dev | VS Code içi denetim | — |
| gitlab_reviewer.py | Otomatik push incelemesi | 5050 |

## Log Takibi

```bash
tail -f kod_inceleme.log
```
