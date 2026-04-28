# 🚀 Dataset_Engine: Verilog Dataset Engine

Bu proje, Verilog donanım tanımlama dili (HDL) için yüksek kaliteli ve doğrulanmış sentetik veri setleri oluşturmak amacıyla geliştirilmiş bir otomasyon motorudur. **Gemini** modelinin gücünü, **Icarus Verilog** simülasyon araçlarıyla birleştirerek "kendi kendini düzelten" bir veri üretim döngüsü sunar.

## 🛠️ Temel Özellikler
* **Paralel İşleme:** Çok çekirdekli işlem desteği ile binlerce dosyayı hızla işler.
* **Otomatik Doğrulama:** Üretilen testbench'leri Icarus Verilog ile koşturur ve sadece çalışan kodları veri setine ekler.
* **Mantıksal Hata Enjeksiyonu:** Modellerin hata bulma yeteneğini artırmak için sentaksı bozmadan mantıksal buglar ekler.
* **Detaylı Açıklama Üretimi:** Her modül için donanım mühendisliği perspektifiyle Türkçe teknik dokümantasyon oluşturur.

---

# 🚀 Dataset_Engine: Verilog Dataset Engine (English)

This project is an automation engine developed to generate high-quality, verified synthetic datasets for the Verilog Hardware Description Language (HDL). By combining the capabilities of the **Gemini** model with **Icarus Verilog** simulation tools, it provides a "self-correcting" data generation loop.

## 🛠️ Key Features
* **Parallel Processing:** Processes thousands of files rapidly using multi-core processing support.
* **Automated Verification:** Runs generated testbenches through Icarus Verilog and only saves verified code to the dataset.
* **Logical Bug Injection:** Injects logical bugs without breaking syntax to improve the error-detection capabilities of trained models.
* **Technical Explanations:** Generates detailed technical documentation for each module from a hardware engineering perspective.

## ⚙️ Setup / Kurulum
1. Install Icarus Verilog: `sudo apt install iverilog` (Ubuntu/Debian)
2. Install dependencies: `pip install -r requirements.txt`
3. Set your environment variables: `GITHUB_TOKEN` and `GEMINI_API_KEY`.


## 🚀 Usage / Kullanım

### 1. GitHub'dan Verilog Dosyası İndirme
`veri_motoru10.py` içindeki `download_verilog()` satırının başındaki `#` işaretini kaldır:
```python
download_verilog()
```

### 2. Hazır Dataset ile Çalışma
Elinde `.v` dosyaları varsa `verilog_dataset/` klasörüne at ve direkt çalıştır:
```bash
python veri_motoru10.py
```

### 3. Çıktı Formatı
`final_dataset_tr.jsonl` dosyasında her satır bir JSON objesidir:
```json
{"file": "alu.v", "instruction": "...", "input": "", "output": "module alu ..."}
```

### 4. Doğrulanmış Dosyalar
Icarus simülasyonundan geçen modüller `dogrulanmis/` klasörüne kopyalanır.

### 5. gemini.py
Model adını veya parametreleri değiştirmek istersen `gemini.py` dosyasını düzenle.
