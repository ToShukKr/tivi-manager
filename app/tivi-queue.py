#!/usr/local/bin/python
from core import *

if __name__ == '__main__':
    try:
        type = sys.argv[1:][0]
        kp_id = sys.argv[1:][1]
    except Exception as e:
        logger.error(f'Please provide correct arguments: {e}')
        exit(1)
    link = getDownloadURL(getQueueData(kp_id)['url'])
    downloadCacheFile(link, kp_id)
    convertVideo(kp_id)
    uploadToArchiveORG(kp_id)
    if os.path.exists(os.path.join(QUEUE_DIR, f"{kp_id}.json")):
        os.remove(os.path.join(QUEUE_DIR, f"{kp_id}.json"))
