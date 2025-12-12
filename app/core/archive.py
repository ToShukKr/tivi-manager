import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import internetarchive as ia


class Archive:
    def __init__(self):
        env_path = str(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(env_path)

    def createArchiveBucket(self, bucket):
        item = ia.get_item(bucket)
        if item.exists:
            return True
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            keep_file = Path(tmp_dir) / ".keep"
            keep_file.write_text("")
            
            result = ia.upload(
                bucket,
                files=[str(keep_file)],
                metadata={"mediatype": "data", "title": bucket, "creator": "TIVI"},
                access_key=os.environ.get("ARCHIVE_ACCESS_KEY"),
                secret_key=os.environ.get("ARCHIVE_SECRET_KEY")
            )
            
            return any(r.status_code == 200 for r in result)

    def upload(self, file_path, bucket):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        attempt = 1
        
        while True:
            print(f"⏳ Uploading {file_path.name} ({file_size / 1024 / 1024:.2f} MB) to {bucket}... (attempt {attempt})")
            
            try:
                result = ia.upload(
                    bucket,
                    files=[str(file_path)],
                    access_key=os.environ.get("ARCHIVE_ACCESS_KEY"),
                    secret_key=os.environ.get("ARCHIVE_SECRET_KEY"),
                    verbose=True
                )
                
                success = any(r.status_code == 200 for r in result)
                if success:
                    print(f"✓ {file_path.name} uploaded successfully to {bucket}")
                    return True
            except Exception as e:
                print(f"✗ Upload error: {e}")
            
            attempt += 1

    def list_bucket(self, bucket):
        item = ia.get_item(bucket)
        return [f.name.replace('.dat', '') for f in item.get_files() if f.name.endswith('.dat')]
