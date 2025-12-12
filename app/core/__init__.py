import os
from pathlib import Path

MAGIC = b"TIVI_ENGINE_DATA_CODE\n"

def encodeVideo(file_path):
    file_path = Path(file_path)
    out_path = file_path.with_suffix(".dat")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    with open(out_path, "wb") as f:
        f.write(MAGIC + data)
    
    os.remove(file_path)