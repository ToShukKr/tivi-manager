import os
from pathlib import Path
import logging
from datetime import datetime
import requests
import time
import json
import base64
import tempfile
import argparse

MAGIC = b"TIVI_ENGINE_DATA_CODE\n"

def setup_logger(name):
    logger = logging.getLogger(name)    
    if logger.handlers:
        return logger
    
    log_dir = Path("/tmp")
    log_file = log_dir / f"tivi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)    
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def encodeVideo(file_path):
    file_path = Path(file_path)
    out_path = file_path.with_suffix(".dat")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    with open(out_path, "wb") as f:
        f.write(MAGIC + data)
    
    os.remove(file_path)

def download(download_url, logger=None, max_retries=100):
    if logger is None:
        logger = setup_logger("tivi")
    
    file_name = download_url.split('/')[-1]
    if not file_name or '.' not in file_name:
        file_name = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    file_path = Path("/tmp") / file_name
    attempt = 1
    
    while attempt <= max_retries:
        try:
            logger.info(f"Downloading: {download_url} (attempt {attempt}/{max_retries})")

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            last_log_time = time.time()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)                    
                        current_time = time.time()
                        if current_time - last_log_time >= 10:
                            if total_size > 0:
                                percent = (downloaded_size / total_size) * 100
                                mb_downloaded = downloaded_size / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                logger.info(f"⏳ Progress: {percent:.1f}% ({mb_downloaded:.2f} MB / {mb_total:.2f} MB)")
                            else:
                                mb_downloaded = downloaded_size / (1024 * 1024)
                                logger.info(f"⏳ Downloaded: {mb_downloaded:.2f} MB")
                            last_log_time = current_time
            
            if total_size > 0 and downloaded_size != total_size:
                logger.warning(f"Incomplete download: {downloaded_size} bytes of {total_size}")
                file_path.unlink()
                attempt += 1
                continue
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ File downloaded successfully ({file_size_mb:.2f} MB)")

            return file_path
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt}/{max_retries}")
            if file_path.exists():
                file_path.unlink()
            attempt += 1
            
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt}/{max_retries}: {e}")
            if file_path.exists():
                file_path.unlink()
            attempt += 1
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on attempt {attempt}/{max_retries}: {e}")
            if file_path.exists():
                file_path.unlink()
            attempt += 1
            
        except Exception as e:
            logger.warning(f"Unexpected error on attempt {attempt}/{max_retries}: {e}")
            if file_path.exists():
                file_path.unlink()
            attempt += 1
    
    logger.error(f"✗ Failed to download after {max_retries} attempts")
    return None
