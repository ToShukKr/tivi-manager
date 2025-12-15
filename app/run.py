from core.archive import Archive
from core.filmix import ProviderAPI
from core import *

logger = setup_logger("tivi")
archive = Archive()

def addMetadataToBucket(url):
    filmix = ProviderAPI(url)
    archive.add_metadata_to_bucket(id=filmix.id, name=filmix.name, type=filmix.type, content=filmix.getSeasons())

def getContentList(url):
    filmix = ProviderAPI(url)
    if filmix.type == "serial":
        content = filmix.getSeasons()
        return [f"{s}-{e}" for s, episodes in content["episodes"].items() for e in episodes.keys()]
    elif filmix.type == "movie":
        return ["0-0"]
    else:
        raise ValueError("Unknown content type")

if __name__ == "__main__":   
        parser = argparse.ArgumentParser(description="TIVI Manager - Download and upload videos to Archive.org")
        parser.add_argument("--url", required=True, help="Filmix URL to process")
        args = parser.parse_args()

        url = args.url
        filmix = ProviderAPI(url)
        logger.info(f"Processing: {filmix.name} ({filmix.type})")

        tividb_identifier = f"tividb_{filmix.id}"        
        archive.createArchiveBucket(tividb_identifier)
        in_bucket = set(archive.list_bucket(tividb_identifier))
        logger.info(f"Found {len(in_bucket)} files in bucket")

        all_content = set(getContentList(url))
        logger.info(f"Total content available: {len(all_content)} episodes")

        missing = sorted(all_content - in_bucket)
        logger.info(f"Found {len(missing)} missing episodes")

        addMetadataToBucket(url)
        logger.info("Metadata in bucket updated")

        archive.addMetadataToDB(filmix)
        logger.info("Metadata in database updated")
        for item in missing:
            season, episode = item.split('-')
            stream_url = filmix.getStream(season, episode, quality="720p")
            download_path = download(stream_url, logger)
            if download_path is None:
                logger.error(f"Failed to download S{season}E{episode}")
                continue

            renamed_path = download_path.parent / f"{item}.mp4"
            download_path.rename(renamed_path)
            encodeVideo(renamed_path)
            dat_path = renamed_path.with_suffix(".dat")
            archive.upload(dat_path, tividb_identifier)
            logger.info(f"S{season}E{episode} uploaded successfully")