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
from github import Github, Auth, RateLimitExceededException # Auth eklendim (Github uyarısını çözmek için)
from google import genai 

# --- Ayarlar ve API Kurulumu ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SAVE_DIR = "verilog_dataset"
VERIFIED_DIR = "dogrulanmis"
os.makedirs(VERIFIED_DIR, exist_ok=True)
OUTPUT_FILE = "final_dataset_tr.jsonl"
PROCESSED_LOG = "islenen_dosyalar.txt"

# ADEL9st: İleride Github'dan doğrudan dosya çeken bir kazıma (scraping) aşaması eklenirse burası kullanılacak
DOWNLOADED_HASHES = "indirme_gecmisi.txt" 

os.makedirs(SAVE_DIR, exist_ok=True)

if not GITHUB_TOKEN or not GEMINI_API_KEY:
    print("⚠️ HATA: GITHUB_TOKEN veya GEMINI_API_KEY bulunamadı! .env veya export ayarlarını kontrol et.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# İstemcileri hazırlayalım 
auth = Auth.Token(GITHUB_TOKEN) # Github tarafı şu an aktif değil ama dursun(aktif)
g = Github(auth=auth)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = 'gemini-2.5-flash-lite' # gemini.py den istediğini değiştirebilirsin


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

# --- Github dosya çekme ---
def download_verilog():
    # Eski kayıtları yükle
    seen_hashes = set()
    if os.path.exists(DOWNLOADED_HASHES):
        with open(DOWNLOADED_HASHES, "r") as f:
            seen_hashes = set(f.read().splitlines())

    queries = [
        "language:verilog alu stars:>=20",
        "language:verilog fpga stars:>=20",
        "language:verilog cpu stars:>=10"
    ]

    repos = []
    for q in queries:
        try:
            repos.extend([r.full_name for r in g.search_repositories(query=q)[:20]])
        except RateLimitExceededException:
            logging.warning("GitHub rate limit aşıldı.")
            break

    repos = list(set(repos))
    logging.info(f"{len(repos)} repo bulundu")

    for repo_name in repos:
        try:
            repo = g.get_repo(repo_name)
            tree = repo.get_git_tree(repo.default_branch, recursive=True)

            for file in tree.tree:
                if (file.path.endswith(".v") and 
                    all(x not in file.path.lower() for x in ["test", "tb", "sim", "bench"])):
                    
                    url = f"https://raw.githubusercontent.com/{repo.full_name}/{repo.default_branch}/{file.path}"
                    
                    # Dosya adını belirle
                    filename = f"{repo.name}_{os.path.basename(file.path)}"
                    file_path = os.path.join(SAVE_DIR, filename)

                    # Eğer dosya zaten varsa indirme
                    if os.path.exists(file_path):
                        continue

                    content = safe_request(url)
                    if not content: continue

                    h = file_hash(content)
                    if h in seen_hashes:
                        continue
                    
                    # Yeni dosyayı kaydet
                    seen_hashes.add(h)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # Hash'i geçmişe kaydet
                    with open(DOWNLOADED_HASHES, "a") as f:
                        f.write(h + "\n")

                    logging.info(f"📥 {filename}")
                    time.sleep(0.3)

        except Exception as e:
            logging.warning(f"{repo_name} atlandı: {e}")


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
    prompt = f"""Bu Verilog modülü için teknik spesifikasyon yaz. 
Kurallar: SADECE düz metin, MAX 100 kelime. Sıra: Amaç, I/O pinleri, çalışma mantığı.
Kod:
{code}"""
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()

def generate_testbench(code: str) -> str:
    prompt = f"""Aşağıdaki Verilog modülü için self-checking testbench yaz.
Kurallar: SADECE Verilog kodu, açıklama yok. `timescale 1ns/1ps` ekle. 
Hata yoksa "SIMULATION_PASSED" yazdır.
Modül:
{code}"""
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return clean_code(response.text)

def generate_buggy(code: str) -> str:
    prompt = f"""Bu Verilog koduna 2 adet ince mantıksal hata ekle. 
SADECE hatalı kodu döndür, açıklama yapma.
Kod:
{code}"""
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return clean_code(response.text)

def explain_code(code: str) -> str:
    prompt = f"""Bu Verilog modülünü Türkçe açıkla. 
Dijital mantık ve register etkileşimine odaklan. SADECE METİN, MAX 150 kelime.
Kod:
{code}"""
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()

# --- Icarus Verilog Test Aşaması ---

def verify_with_icarus(module_code: str, tb_code: str) -> bool:
    # Geçici dosyalarla simülasyon yapıp ondan sonra siliyor
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = os.path.join(tmpdir, "module.v")
        tb_path = os.path.join(tmpdir, "tb.v")
        vvp_out = os.path.join(tmpdir, "sim.vvp")
        
        with open(module_path, "w", encoding="utf-8", errors="ignore") as f: 
            f.write(module_code)
        with open(tb_path, "w", encoding="utf-8", errors="ignore") as f: 
            f.write(tb_code)
            
        try:
            # Derleme yapan yer
            compile_process = subprocess.run(
                ["iverilog", "-g2012", "-o", vvp_out, module_path, tb_path], 
                capture_output=True, text=True, timeout=15
            )
            if compile_process.returncode != 0:
                return False
                
            # Çalıştıran taraf
            sim_process = subprocess.run(["vvp", vvp_out], capture_output=True, text=True, timeout=15, cwd=tmpdir)
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
            
        # Çok kısa veya çok uzun (gürültü) dosyaları pas geçiyoruz
        if not (3072 < len(code) < 600000):
            return None
            
        logging.info(f"İşleniyor: {file}")
        
        inst = generate_with_retry(generate_instruction, code)
        tb = generate_with_retry(generate_testbench, code)
        verified = tb and verify_with_icarus(code, tb)
        if verified:
            verified_path = os.path.join(VERIFIED_DIR, file)
            with open(verified_path, "w", encoding="utf-8") as vf:
                vf.write(code)
            logging.info(f"Tam çalışıyor, gönderildi: {file}")
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
        time.sleep(1)  # Rate limite takılmamak için gecikme
        return [r for r in result if r is not None]
        
    except Exception as e:
        logging.error(f"🚨 {file} dosyasında bir şeyler ters gitti: {e}")
        time.sleep(5)
        return None

def build_dataset_parallel():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".v") and os.path.isfile(os.path.join(SAVE_DIR, f))]
    
    with Manager() as manager:
        shared_processed_files = manager.dict()
        total_cost = manager.Value('d', 0.0)

        
        # Kaldığımız yerden devam edebilmek için logu okuma
        if os.path.exists(PROCESSED_LOG):
            with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
                for line in f.read().splitlines():
                    shared_processed_files[line] = True
                    
        files_to_process = [f for f in files if f not in shared_processed_files] #[] #buradaki sonraki [] aralık belitmede kullanabilirsin yoksa sil
        func = partial(process_file, shared_processed_files=shared_processed_files)
        
        worker_count = 10 #min(4, cpu_count()) 
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
    # Icarus kurulu mu diye ufak bir kontrol,
    try:
        subprocess.run(["iverilog", "-V"], capture_output=True, check=True)
        subprocess.run(["vvp", "-V"], capture_output=True, check=True)
        logging.info("✅ Icarus Verilog sistemde mevcut, simülasyonlar çalışabilir.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        logging.error("❌ HATA: Icarus Verilog bulunamadı! Simülasyonlar çalışmaz. Lütfen 'iverilog' paketini kurun.")
        sys.exit(1)


if __name__ == "__main__":
    logging.info("🚀 Veri seti oluşturma motoru başlatılıyor...")
    
    # Bağımlılık Kontrolü
    check_dependencies()
    
    # GitHub'dan Veri Toplama
    logging.info("📁 1. AŞAMA: GitHub üzerinden Verilog projeleri taranıyor ve indiriliyor...")
   
    # Not: Elinde hazır bir dataset varsa bu kodun altındaki # ekle yoksa kaldır Githubdan çeksin
    #download_verilog()
    
    # Mevcut dosya sayısını hesaplar
    indirilen_dosyalar = [f for f in os.listdir(SAVE_DIR) if f.endswith(".v")]
    
    print("\n" + "="*50)
    print(f"✅ GitHub İndirme İşlemi Tamamlandı.")
    print(f"📂 '{SAVE_DIR}' klasöründe toplam {len(indirilen_dosyalar)} dosya hazır bekliyor.")
    print("="*50)
    
    # Kullanıcı Onayı ve AI İşleme
    onay = input("\n🤖 AI yorumlama ve Icarus Verilog doğrulama aşamasına geçmek istiyor musun? (y/n): ")
    
    if onay.lower() == 'y':
        logging.info("⚙️ 2. AŞAMA: Paralel işleme ve AI analiz hattı başlatılıyor...")
        build_dataset_parallel() #
        logging.info("🏁 İşlem başarıyla tamamlandı. 'final_dataset_tr.jsonl' dosyan hazır!")
    else:
        logging.info("🛑 İşlem kullanıcı tarafından durduruldu. Sadece indirme yapıldı.")
