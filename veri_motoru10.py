import os
import sys
import json
import time
import hashlib
import random
import logging
import subprocess
import tempfile
from functools import partial
from multiprocessing import Pool, Manager, cpu_count

import requests
from github import Github, RateLimitExceededException
import google.generativeai as genai

# --- Ayarlar ve API Kurulumu ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SAVE_DIR = "verilog_dataset"
OUTPUT_FILE = "final_dataset_tr.jsonl"
PROCESSED_LOG = "islenen_dosyalar.txt"

# TODO: İleride Github'dan doğrudan dosya çeken bir kazıma (scraping) aşaması eklenirse burası kullanılacak
DOWNLOADED_HASHES = "indirme_gecmisi.txt" 

os.makedirs(SAVE_DIR, exist_ok=True)

if not GITHUB_TOKEN or not GEMINI_API_KEY:
    print("⚠️ HATA: GITHUB_TOKEN veya GEMINI_API_KEY bulunamadı! .env veya export ayarlarını kontrol et.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# İstemcileri hazırlayalım
g = Github(GITHUB_TOKEN) # Github tarafı şu an aktif değil ama dursun
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash')


# --- Yardımcı Fonksiyonlar ---

def clean_code(text: str) -> str:
    # Modelin ürettiği markdownları temizliyoruz
    text = text.replace("```verilog", "").replace("```v", "").replace("```", "").strip()
    if "module" in text and "endmodule" in text:
        start = text.find("module")
        end = text.rfind("endmodule") + 9
        return text[start:end].strip()
    return text.strip()

# Not: Github API entegrasyonu tamamlandığında lazım olacak
def safe_request(url: str, retries=3, delay=2) -> str:
    for i in range(retries):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.text
            logging.warning(f"İstek patladı(GG) ({r.status_code}) {url}")
        except Exception as e:
            logging.warning(f"Bağlantı hatası: {e} -> {url}")
        time.sleep(delay)
    return None

def file_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8", errors="ignore")).hexdigest()

def generate_with_retry(func, code, retries=5):
    # Rate limit vb. durumlarda patlamamak için exponential backoff
    for i in range(retries):
        try:
            return func(code)
        except Exception as e:
            wait_time = (2 ** i) + random.random() 
            logging.warning(f"⚠️ Deneme {i+1}/{retries} başarısız ({e}). {wait_time:.2f} sny bekleniyor...")
            time.sleep(wait_time)
    return ""


# --- Gemini Promptları ---

def generate_instruction(code: str) -> str:
    prompt = f"""Bu Verilog modülü için kısa ve profesyonel bir donanım mühendisliği spesifikasyonu yaz. 
Temel işlevini, giriş/çıkışlarını ve varsa iç durum makinesi (state machine) mantığını net bir şekilde Türkçe olarak açıkla. 
SADECE METİN DÖNDÜR, markdown formatı kullanma.

Kod:
{code}"""
    return model.generate_content(prompt).text.strip()

def generate_testbench(code: str) -> str:
    prompt = f"""Bu modül için kapsamlı ve kendi kendini test eden (self-checking) bir Verilog testbench yaz. 
Kurallar:
1. Icarus Verilog uyumlu sentaks kullan.
2. Timescale, clock üretimi ve sınır durum (edge-case) senaryolarını ekle.
3. Çıktıları beklenen değerlerle karşılaştıran otomatik doğrulama mantığı kur.
4. SADECE tüm testler başarıyla geçerse simülasyonun sonunda 'SIMULATION_PASSED' yazdır.
5. SADECE geçerli Verilog kodunu döndür.

Modül:
{code}"""
    return clean_code(model.generate_content(prompt).text)

def generate_buggy(code: str) -> str:
    prompt = f"""Bu Verilog koduna 2-3 adet ince MANTIKSAL donanım hatası (bug) ekle.
İyi hata örnekleri: eksik reset durumları, bit düzeyinde (bitwise &) ve mantıksal (logical &&) operatörleri karıştırma, yanlış durum makinesi geçişleri veya sayaçlarda ±1 hataları (off-by-one).
KESİNLİKLE sentaks hatası ekleme. Kod sorunsuz bir şekilde derlenmeye devam etmeli.
SADECE hatalı kodu döndür.

Kod:
{code}"""
    return clean_code(model.generate_content(prompt).text)

def explain_code(code: str) -> str:
    prompt = f"""Bu Verilog modülünün yapısal ve detaylı bir açıklamasını Türkçe olarak yap. 
Altında yatan dijital mantığı, zamanlama kısıtlamalarını, blok seviyesi mimariyi ve register/kombinasyonel mantığın nasıl etkileşime girdiğini anlat.
SADECE METİN DÖNDÜR.

Kod:
{code}"""
    return model.generate_content(prompt).text.strip()


# --- Icarus Verilog Test Aşaması ---

def verify_with_icarus(module_code: str, tb_code: str) -> bool:
    # Geçici dosyalarla simülasyon yapıp ortalığı temizliyoruz
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = os.path.join(tmpdir, "module.v")
        tb_path = os.path.join(tmpdir, "tb.v")
        vvp_out = os.path.join(tmpdir, "sim.vvp")
        
        with open(module_path, "w", encoding="utf-8", errors="ignore") as f: 
            f.write(module_code)
        with open(tb_path, "w", encoding="utf-8", errors="ignore") as f: 
            f.write(tb_code)
            
        try:
            # Derleme aşaması
            compile_process = subprocess.run(
                ["iverilog", "-g2012", "-o", vvp_out, module_path, tb_path], 
                capture_output=True, text=True, timeout=15
            )
            if compile_process.returncode != 0:
                return False
                
            # Çalıştırma aşaması
            sim_process = subprocess.run(["vvp", vvp_out], capture_output=True, text=True, timeout=15)
            output = sim_process.stdout + sim_process.stderr
            
            return "SIMULATION_PASSED" in output and "Error" not in output and "FATAL" not in output
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False


# --- Ana İşlem Döngüleri ---

def process_file(file, shared_processed_files):
    file_path = os.path.join(SAVE_DIR, file)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            
        # Çok kısa veya çok uzun (gürültü) dosyaları es geçiyoruz
        if not (50 < len(code) < 15000):
            return None
            
        logging.info(f"İşleniyor: {file}")
        
        inst = generate_with_retry(generate_instruction, code)
        tb = generate_with_retry(generate_testbench, code)
        verified = tb and verify_with_icarus(code, tb)
        buggy = generate_with_retry(generate_buggy, code)
        exp = generate_with_retry(explain_code, code)
        
        result = [
            {"file": file, "instruction": inst, "input": "", "output": code},
            {"file": file, "instruction": "Bu Verilog modülü için kendi kendini doğrulayan bir testbench yaz.",
             "input": code, "output": tb, "verified": verified} if verified else None,
            {"file": file, "instruction": "Bu Verilog kodundaki mantıksal hataları bularak düzelt.",
             "input": buggy, "output": code},
            {"file": file, "instruction": "Bu Verilog kodunun çalışma mantığını ve mimarisini detaylıca açıkla.",
             "input": code, "output": exp}
        ]
        
        shared_processed_files[file] = True
        time.sleep(2)  # Rate limite takılmamak için ufak bir gecikme
        return [r for r in result if r is not None]
        
    except Exception as e:
        logging.error(f"🚨 {file} dosyasında bir şeyler ters gitti: {e}")
        time.sleep(5)
        return None

def build_dataset_parallel():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".v")]
    
    with Manager() as manager:
        shared_processed_files = manager.dict()
        
        # Kaldığımız yerden devam edebilmek için logu okuyoruz
        if os.path.exists(PROCESSED_LOG):
            with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
                for line in f.read().splitlines():
                    shared_processed_files[line] = True
                    
        files_to_process = [f for f in files if f not in shared_processed_files]
        func = partial(process_file, shared_processed_files=shared_processed_files)
        
        worker_count = min(4, cpu_count())
        logging.info(f"Paralel işleme {worker_count} worker ile başlıyor...")
        
        with Pool(processes=worker_count) as pool, \
             open(OUTPUT_FILE, "a", encoding="utf-8") as out, \
             open(PROCESSED_LOG, "a", encoding="utf-8") as log_out:
                 
            for result_list in pool.imap_unordered(func, files_to_process):
                if result_list:
                    for res in result_list:
                        out.write(json.dumps(res, ensure_ascii=False) + "\n")
                    out.flush()
                    
                    log_out.write(result_list[0]["file"] + "\n")
                    log_out.flush()

def check_dependencies():
    # Icarus kurulu mu diye ufak bir kontrol, yarra yemeyek sonra kapiş
    try:
        subprocess.run(["iverilog", "-V"], capture_output=True, check=True)
        subprocess.run(["vvp", "-V"], capture_output=True, check=True)
        logging.info("✅ Icarus Verilog sistemde mevcut, simülasyonlar çalışabilir.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        logging.error("❌ HATA: Icarus Verilog bulunamadı! Simülasyonlar çalışmaz. Lütfen 'iverilog' paketini kurun.")
        sys.exit(1)


if __name__ == "__main__":
    logging.info("🚀 Veri seti oluşturma motoru başlatılıyor...")
    check_dependencies()
    build_dataset_parallel()
    logging.info("🏁 İşlem tamamlandı. Hayırlı olsun!")