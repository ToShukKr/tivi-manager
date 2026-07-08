#!/usr/bin/env python3

import os
import argparse
import tempfile
import logging
import json
from pathlib import Path
import internetarchive as ia

MAGIC = b"TIVI_ENGINE_DATA_CODE\n"

def setup_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


class Archive:
    def __init__(self):
        self.logger = setup_logger("tivi")
        self.access_key = "NNUXnuHlaYYyTl67"
        self.secret_key = "H3P5DurWMhOPOyXo"

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
                metadata={
                    "mediatype": "data",
                    "title": bucket,
                    "creator": "tivi-engine",
                },
                access_key=self.access_key,
                secret_key=self.secret_key,
            )

            return any(r.status_code == 200 for r in result)

    def encodeVideo(self, file_path):
        """Read the file, prepend the MAGIC header, write a .dat next to it."""
        file_path = Path(file_path)
        out_path = file_path.with_suffix(".dat")

        self.logger.info(f"Encoding {file_path.name} -> {out_path.name}")

        with open(file_path, "rb") as f:
            data = f.read()

        with open(out_path, "wb") as f:
            f.write(MAGIC + data)

        # Note: We do not remove the original file here; the caller will handle cleanup.
        return out_path

    # def decodeVideo(self, file_path):
    #     """
    #     Reverse of encodeVideo: read a .dat file, verify and strip the MAGIC
    #     header, then write the original video back out.
    #
    #     Returns the path to the decoded file, or raises ValueError if the
    #     MAGIC header is missing (i.e. the file is not TIVI-encoded).
    #     """
    #     file_path = Path(file_path)
    #
    #     with open(file_path, "rb") as f:
    #         data = f.read()
    #
    #     # Make sure the file actually starts with our MAGIC marker.
    #     if not data.startswith(MAGIC):
    #         raise ValueError(f"{file_path.name} is not a TIVI-encoded file (MAGIC header not found)")
    #
    #     # Strip the MAGIC header, keeping only the original payload.
    #     payload = data[len(MAGIC):]
    #
    #     # Drop the .dat suffix to restore the original name.
    #     out_path = file_path.with_suffix("")
    #
    #     self.logger.info(f"Decoding {file_path.name} -> {out_path.name}")
    #
    #     with open(out_path, "wb") as f:
    #         f.write(payload)
    #
    #     # Uncomment the next line if you also want to delete the .dat afterwards.
    #     # os.remove(file_path)
    #
    #     return out_path

    def upload(self, file_path, bucket, remote_name=None):
        """
        Upload a file to the bucket.
        remote_name is the path/name inside the bucket (e.g. 'series/12345.dat').
        Returns True on success, False on failure after max attempts.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size

        # If a remote name is given, map the local path to the path inside the archive.
        if remote_name:
            files = {remote_name: str(file_path)}
        else:
            files = [str(file_path)]

        max_attempts = 5
        attempt = 1
        while attempt <= max_attempts:
            self.logger.info(
                f"Uploading {file_path.name} "
                f"({file_size / 1024 / 1024:.2f} MB) to {bucket}"
                + (f" as {remote_name}" if remote_name else "")
                + f"... (attempt {attempt}/{max_attempts})"
            )

            try:
                result = ia.upload(
                    bucket,
                    files=files,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    verbose=True,
                )

                success = any(r.status_code == 200 for r in result)
                if success:
                    self.logger.info(
                        f"{file_path.name} uploaded successfully to {bucket}"
                    )
                    # Note: We do not remove the file here; the caller will handle cleanup.
                    return True
                else:
                    self.logger.error(f"Upload failed with status codes: {[r.status_code for r in result]}")

            except Exception as e:
                self.logger.error(f"Upload error: {e}")

            attempt += 1

        self.logger.error(f"Failed to upload {file_path.name} after {max_attempts} attempts.")
        return False

    def list_bucket_files(self, bucket, prefix=None):
        """
        List files in an archive.org bucket.
        Returns a list of file metadata dictionaries.
        """
        item = ia.get_item(bucket)
        if not item.exists:
            raise FileNotFoundError(f"Bucket not found: {bucket}")

        files = []
        for file_obj in item.files:
            file_info = {
                "name": file_obj.get("name"),
                "size": file_obj.get("size"),
                "format": file_obj.get("format"),
                "mtime": file_obj.get("mtime"),
                "md5": file_obj.get("md5"),
                "sha1": file_obj.get("sha1"),
            }
            if prefix:
                if file_info["name"].startswith(prefix):
                    files.append(file_info)
            else:
                files.append(file_info)
        return files

    def get_kp_id_files(self, bucket, kp_id):
        """
        Get all files in the bucket under the kp_id directory.
        Returns a JSON string with file information.
        """
        prefix = f"{kp_id}/"
        files = self.list_bucket_files(bucket, prefix=prefix)
        return json.dumps({
            "bucket": bucket,
            "kp_id": kp_id,
            "prefix": prefix,
            "count": len(files),
            "files": files
        }, indent=2, ensure_ascii=False)

    def download_file(self, bucket, remote_name, local_path):
        """
        Download a file from the bucket to local_path.
        Returns True if successful, False if file not found.
        """
        item = ia.get_item(bucket)
        if not item.exists:
            return False
        # Check if file exists
        for f in item.files:
            if f.get('name') == remote_name:
                # Download the file
                file_obj = item.get_file(remote_name)
                with open(local_path, 'wb') as f_out:
                    file_obj.write_to(f_out)
                return True
        return False


    def upload_video(self, file, bucket, kp_id):
            """
            Full cycle: encode the video + upload it to the bucket under the right path.

            Final path inside the bucket: <kp_id>/<filename>.dat
            (e.g. series/12345/episode01.dat or movies/67890/movie.dat)
            """
            file_path = Path(file)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")


            filename = file_path.stem
            self.createArchiveBucket(bucket)
            encoded_path = self.encodeVideo(file_path)

            parts = []
            parts.append(str(kp_id))
            parts.append(f"{filename}.dat")
            remote_name = "/".join(parts)

            # 3. Upload.
            success = self.upload(encoded_path, bucket, remote_name=remote_name)
            if success:
                # Remove both the original file and the encoded file
                try:
                    os.remove(file_path)          # Remove the original .mp4
                    os.remove(encoded_path)       # Remove the .dat file
                except OSError as e:
                    self.logger.warning(f"Failed to remove temporary files: {e}")
                return True
            else:
                # If upload failed, we leave the files as they are for potential retry.
                return False


def parse_args():
    parser = argparse.ArgumentParser( description="Encode a video file (add the TIVI MAGIC header) and upload it to an archive.org bucket." )
    parser.add_argument( "--bucket", default="tivi_db", help="Destination bucket on archive.org (default: tivi_db)" )
    parser.add_argument( "--file", help="Path to the video file on the local system" )
    parser.add_argument( "--kp-id", help="File ID (used as the <kp_id>.dat name inside the bucket)" )
    parser.add_argument( "--get", action="store_true", help="Get JSON list of files in the bucket under the kp_id directory" )
    return parser.parse_args()

def main():
    args = parse_args()
    archive = Archive()

    if args.get:
        if not args.kp_id:
            print("Error: --kp-id is required when using --get")
            return
        print(archive.get_kp_id_files(args.bucket, args.kp_id))
    else:
        if not args.file or not args.kp_id:
            print("Error: --file and --kp-id are required for upload")
            return
        archive.upload_video(file=args.file, bucket=args.bucket, kp_id=args.kp_id)

if __name__ == "__main__":
    main()
