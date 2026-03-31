# GEMINI.md

Bu dosya, Gemini CLI'ın bu depoda çalışırken uyması gereken temel yönergeleri, proje mimarisini ve geliştirme standartlarını içerir.

## Proje Genel Bakışı

**LocalAI**, internet bağlantısı gerektirmeyen, şirket içi GitLab sunucusuyla entegre çalışan yerel bir AI kod denetim sistemidir. Sistem, HP Z2 Tower G4 (32GB RAM) üzerinde CPU-only modunda çalışacak şekilde optimize edilmiştir.

### Temel Bileşenler:
- **`mr_reviewer.py` (Ana Araç)**: Periyodik olarak (polling) GitLab üzerindeki açık Merge Request'leri (MR) tarayan, diff'leri inceleyen ve sonuçları doğrudan MR altına yorum olarak yazan aktif ajan.
- **`gitlab_reviewer.py` (Alternatif)**: Flask tabanlı webhook sunucusu. Push event'lerini yakalar ve inceleme sonuçlarını yerel bir log dosyasına yazar.
- **Ollama**: Yerel LLM motoru (`qwen2.5-coder:14b` ve `nomic-embed-text` modellerini kullanır).
- **AnythingLLM**: PDF formatındaki kurumsal standartları RAG (Retrieval-Augmented Generation) ile sorgulamak için kullanılır.
- **Continue.dev**: VS Code içinde anlık kod denetimi ve otomatik tamamlama sağlar.

## Çalıştırma ve Kurulum Komutları

### MR İnceleme Ajanını Başlatma (Ana Kullanım)
```bash
export GITLAB_TOKEN="your_token"
export OLLAMA_MODEL="qwen2.5-coder:14b"
python mr_reviewer.py
```

### Webhook Sunucusunu Başlatma (Opsiyonel)
```bash
export GITLAB_TOKEN="your_token"
export WEBHOOK_SECRET="your_secret"
python gitlab_reviewer.py
```

### Donanım Kısıtları (Önemli)
- **GPU Kısıtı**: Quadro P620 (2GB VRAM) yetersiz olduğu için Ollama **her zaman CPU modunda** çalıştırılmalıdır (`CUDA_VISIBLE_DEVICES=""`).
- **Bellek**: 32GB RAM, 14B modelin CPU üzerinde verimli çalışması için kritiktir.

## Geliştirme Konvansiyonları

### 1. State Yönetimi
- `mr_reviewer.py`, daha önce incelenen MR'ları `mr_reviewed.json` dosyasında saklar.
- İnceleme öncesinde GitLab API üzerinden mükerrer yorum kontrolü yapar.

### 2. İnceleme Standartları
AI prompt'u şu alanlara odaklanır:
- Naming convention ihlalleri.
- SOLID prensipleri ve kod kalitesi.
- Güvenlik açıkları (Hardcoded şifreler, SQL Injection, XSS).
- Yapıcı ve Türkçe geri bildirim.

### 3. Hedef Proje Mimarisi (Denetlenen Projeler)
Projenin denetlediği sistemler genellikle şu standartlara uyar:
- **Dil/Framework**: Java 21, Spring Boot 3.x.
- **Mimari**: Controller → Service → Repository katmanlı yapı.
- **Finansal Kurallar**: `BigDecimal` kullanımı, Idempotency key, Audit log zorunluluğu.

## Anahtar Dosyalar ve Klasörler
- `mr_reviewer.py`: Ana MR tarama ve yorumlama mantığı.
- `mr_reviewed.json`: İncelenen MR ID'lerinin listesi.
- `local-ai-kurulum.md`: Adım adım kurulum ve sorun giderme rehberi.
- `.claude/agents/`: Uzman AI talimatları (Backend, DevOps, vb.).
