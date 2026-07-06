import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser( description="TiVi Manager" )
    parser.add_argument( "--kp_id", required=True, help="File ID (used as the <kp_id>.dat name inside the bucket)" )
    return parser.parse_args()

def main():
    args = parse_args()
    archive = Archive()
    archive.upload_video(file=args.file,bucket=args.bucket,kp_id=args.kp_id)

if __name__ == "__main__":
    main()