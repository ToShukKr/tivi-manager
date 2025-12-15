import os
import json
import tempfile
import logging
from pathlib import Path
from dotenv import load_dotenv
import internetarchive as ia
from core import *


class Archive:
    def __init__(self):
        from . import setup_logger
        self.logger = setup_logger("tivi")
        
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
            self.logger.info(f"Uploading {file_path.name} ({file_size / 1024 / 1024:.2f} MB) to {bucket}... (attempt {attempt})")
            
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
                    self.logger.info(f"{file_path.name} uploaded successfully to {bucket}")
                    os.remove(file_path)
                    return True
            except Exception as e:
                self.logger.error(f"Upload error: {e}")

            attempt += 1

    def list_bucket(self, bucket):
        item = ia.get_item(bucket)
        return [f.name.replace('.dat', '') for f in item.get_files() if f.name.endswith('.dat')]

    def upload_metadata(self, id, name, type, content):
        bucket="tivi_metadata"
        self.createArchiveBucket(bucket)
        metadata = {
            "id": id,
            "name": name,
            "type": type,
            "content": content
        }
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_file = Path(tmp_dir) / f"{id}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.upload(str(json_file), bucket)

    def add_metadata_to_bucket(self, id, name, type, content):
        bucket = f"tividb_{id}"
        self.createArchiveBucket(bucket)
        metadata = {
            "id": id,
            "name": name,
            "type": type,
            "content": content
        }
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_file = Path(tmp_dir) / f"metadata.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.upload(str(json_file), bucket)

    def addMetadataToDB(self, filmix):
        bucket = "tivi_metadata"
        metadata_file = "metadata.json"
        try:
            try:
                item = ia.get_item(bucket)
                files = item.get_files()
                metadata_file_obj = None
                
                for f in files:
                    if f.name == metadata_file:
                        metadata_file_obj = f
                        break
                
                if metadata_file_obj:
                    response = requests.get(f"https://archive.org/download/{bucket}/{metadata_file}")
                    response.raise_for_status()
                    encoded_content = response.text
                else:
                    encoded_content = base64.b64encode(json.dumps([], ensure_ascii=False).encode()).decode()
            except Exception as e:
                encoded_content = base64.b64encode(json.dumps([], ensure_ascii=False).encode()).decode()
            
            try:
                decoded_json = base64.b64decode(encoded_content).decode('utf-8')
                metadata_list = json.loads(decoded_json)
            except Exception as e:
                metadata_list = []
            
            new_item = {
                "id": filmix.id,
                "name": filmix.name,
                "type": filmix.type,
                "content": filmix.getSeasons()
            }
            
            item_found = False
            for i, item in enumerate(metadata_list):
                if item.get("id") == filmix.id:
                    metadata_list[i] = new_item
                    item_found = True
                    break
            
            if not item_found:
                metadata_list.append(new_item)

            new_encoded_content = base64.b64encode(json.dumps(metadata_list, ensure_ascii=False, indent=2).encode()).decode()
            backup_filename = f"metadata.json_{datetime.now().strftime('%d-%m-%Y-%H-%M-%S')}"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                
                new_metadata_path = tmp_path / metadata_file
                with open(new_metadata_path, 'w', encoding='utf-8') as f:
                    f.write(new_encoded_content)
                
                backup_path = tmp_path / backup_filename
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(encoded_content)

                self.createArchiveBucket(bucket)
                
                result1 = ia.upload(
                    bucket,
                    files=[str(new_metadata_path)],
                    access_key=os.environ.get("ARCHIVE_ACCESS_KEY"),
                    secret_key=os.environ.get("ARCHIVE_SECRET_KEY"),
                    verbose=False
                )
                success1 = any(r.status_code == 200 for r in result1)
                
                result2 = ia.upload(
                    bucket,
                    files=[str(backup_path)],
                    access_key=os.environ.get("ARCHIVE_ACCESS_KEY"),
                    secret_key=os.environ.get("ARCHIVE_SECRET_KEY"),
                    verbose=False
                )
                success2 = any(r.status_code == 200 for r in result2)
            
            if success1 and success2:
                return True
            else:
                return False

        except Exception as e:
            return False