from core.archive import Archive
from core import *

archive = Archive()
# result = archive.createArchiveBucket('tividb_003')
# print(result)

# encodeVideo("/tmp/1/1-8.mp4")

# for i in ["3-1", "3-2"]:
#     # encodeVideo(f"/tmp/1/{i}.mp4")
#     archive.upload(f"/tmp/1/{i}.dat", "tividb_003")


result = archive.list_bucket('tividb_003')
print(result)