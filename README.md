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


## 🚀 Kullanım

### 1. GitHub'dan Verilog Dosyası İndirme
`dataset_engine.py` içindeki `download_verilog()` satırının başındaki `#` işaretini kaldır:
```python
download_verilog()
```

### 2. Hazır Dataset ile Çalışma
Elinde `.v` dosyaları varsa `verilog_dataset/` klasörüne at ve direkt çalıştır:
```bash
python dataset_engine.py
```

### 3. Çıktı Formatı
`final_dataset_tr.jsonl` dosyasında her satır bir JSON objesidir:
```json
{"file": "alu.v", "instruction": "...", "input": "", "output": "module alu ..."}
```

### 4. Doğrulanmış Dosyalar
Icarus simülasyonundan geçen modüller `dogrulanmis/` klasörüne kopyalanır.

### 5. gemini.py
Model adını veya parametreleri değiştirmek istersen `gemini.py` dosyasından bakıp değiştirebilirsin.

### 6. Prompt
`dataset_engine.py` dosyasının içinde --- Gemini Promptları --- kısmında promptu istediğiniz gibi değiştirin.

## 7. Ayarlar

`dataset_engine.py` içindeki şu değerleri ihtiyacına göre değiştirebilirsin:

- `worker_count = 10` → Paralel işçi sayısı (CPU'na göre ayarla)
- `time.sleep(1)` → API rate limit gecikmesi
- `3072 < len(code) < 600000` → İşlenecek dosya boyut aralığı (byte)
- `files_to_process[başlangıç:bitiş]` → Belirli bir dosya aralığı işlemek için


## 🚀 Usage

1. **Download Verilog files from GitHub**
   Remove the `#` from the `download_verilog()` line in `dataset_engine.py`

2. **Work with existing dataset**
   Place `.v` files in `verilog_dataset/` folder and run:
```bash
python dataset_engine.py
```

3. **Output format**
   Each line in `final_dataset_tr.jsonl` is a JSON object:
```json
   {"file": "alu.v", "instruction": "...", "input": "", "output": "module alu ..."}
```

4. **Verified files**
   Modules that pass Icarus simulation are copied to `dogrulanmis/`

5. **gemini.py**
   Edit `gemini.py` to change the model name or parameters.

6. **Prompts**
   Modify prompts in the `--- Gemini Promptları ---` section of `dataset_engine.py`

7. **Settings**
   Adjust these values in `dataset_engine.py`:
   - `worker_count = 10` → Number of parallel workers
   - `time.sleep(1)` → API rate limit delay
   - `3072 < len(code) < 600000` → File size range (bytes)
   - `files_to_process[start:end]` → Process a specific file range
