# 🚀 Veri Motoru 10: Verilog Dataset Engine

Bu proje, Verilog donanım tanımlama dili (HDL) için yüksek kaliteli ve doğrulanmış sentetik veri setleri oluşturmak amacıyla geliştirilmiş bir otomasyon motorudur. **Gemini 3 Flash** modelinin gücünü, **Icarus Verilog** simülasyon araçlarıyla birleştirerek "kendi kendini düzelten" bir veri üretim döngüsü sunar.

## 🛠️ Temel Özellikler
* **Paralel İşleme:** Çok çekirdekli işlem desteği ile binlerce dosyayı hızla işler.
* **Otomatik Doğrulama:** Üretilen testbench'leri Icarus Verilog ile koşturur ve sadece çalışan kodları veri setine ekler.
* **Mantıksal Hata Enjeksiyonu:** Modellerin hata bulma yeteneğini artırmak için sentaksı bozmadan mantıksal buglar ekler.
* **Detaylı Açıklama Üretimi:** Her modül için donanım mühendisliği perspektifiyle Türkçe teknik dokümantasyon oluşturur.

---

# 🚀 Veri Motoru 10: Verilog Dataset Engine (English)

This project is an automation engine developed to generate high-quality, verified synthetic datasets for the Verilog Hardware Description Language (HDL). By combining the capabilities of the **Gemini 3 Flash** model with **Icarus Verilog** simulation tools, it provides a "self-correcting" data generation loop.

## 🛠️ Key Features
* **Parallel Processing:** Processes thousands of files rapidly using multi-core processing support.
* **Automated Verification:** Runs generated testbenches through Icarus Verilog and only saves verified code to the dataset.
* **Logical Bug Injection:** Injects logical bugs without breaking syntax to improve the error-detection capabilities of trained models.
* **Technical Explanations:** Generates detailed technical documentation for each module from a hardware engineering perspective.

## ⚙️ Setup / Kurulum
1. Install Icarus Verilog: `sudo apt install iverilog` (Ubuntu/Debian)
2. Install dependencies: `pip install -r requirements.txt`
3. Set your environment variables: `GITHUB_TOKEN` and `GEMINI_API_KEY`.
