from core.variables import *
from core.providers.filmix import *

def getRandomName(len=8):
     return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=len))

def do_search(query, page=1):
    url = f'{FILMIX_URL}/engine/ajax/sphinx_search.php'
    headers = {'x-requested-with': 'XMLHttpRequest'}
    data = {'story': query, 'search_start': page}
    response = requests.post(url, headers=headers, data=data)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article', class_='shortstory')
    result = {
        "name": query,
        "pages": 1,
        "current_page": page,
        "content": []
    }
    for article in articles:
        name_tag = article.find('h2', class_='name')
        name = name_tag.text.strip() if name_tag else 'N/A'
        year_tag = article.find('div', class_='item year')
        year = year_tag.find('a').text.strip() if year_tag else 'N/A'
        translation_tag = article.find('div', class_='item translate')
        translation = translation_tag.find('span', class_='item-content').text.strip() if translation_tag else 'N/A'
        link = name_tag.find('a')['href'].strip() if name_tag and name_tag.find('a') else 'N/A'
        poster_tag = article.find('img')
        poster_link = poster_tag['src'].strip() if poster_tag else 'N/A'

        result['content'].append({
            "name": name,
            "year": year,
            "translation": translation,
            "link": link,
            "poster": poster_link
        })
    navigation = soup.find('div', class_='navigation')
    if navigation:
        pages = navigation.find_all('span', class_='click')
        if pages:
            last_page = pages[-1].text.strip()
            result['pages'] = int(last_page)
    return result

def currentActiveDownloads():
    return len([file for file in os.listdir(IN_PROGRESS) if file.endswith('.json')])

@retry
def getDownloadURL(queue_current_data):
    url = queue_current_data['url']
    translation_id = queue_current_data['translation']['id']
    type = queue_current_data['type']
    logger.info(f'Getting Download URL for : {url}')
    if type == "movie":
        return ProviderAPI(url).getMovie(DEFAULT_QUALITY, translation_id)
    season = queue_current_data['data']['season']
    episode = queue_current_data['data']['episode']
    return ProviderAPI(url).getStream(season, episode, DEFAULT_QUALITY, translation_id)

@retry
def downloadCacheFile(link, queue_data):
    logger.info(f'Downloading: "{queue_data['name']}"')
    logfile = os.path.join(LOGS_DIR, f"{DOWNLOAD_THREAD_PREFIX_NAME}_{queue_data['uid']}.log")
    os.system(f'aria2c -k 1M -s {DOWNLOAD_THREADS} -x {DOWNLOAD_THREADS} -o "..{os.path.join(CACHE_DIR, f"{queue_data['output_filename']}")}" "{link}" > {logfile} 2>&1')
    if os.path.exists(logfile):
        os.remove(logfile)
    logger.info(f'Successfully downloaded: "{queue_data['name']}"')
    return True

def convertVideo(queue_data):
    logger.info(f'Converting: "{queue_data['name']}"')
    DOWNLOAD_FILENAME = os.path.join(CACHE_DIR, f"{queue_data['output_filename']}")
    OUTPUT_FILENAME = os.path.join(UPLOAD_CACHE_DIR, f"{queue_data['output_filename']}")
    logfile = os.path.join(LOGS_DIR, f"{CONVERT_THREAD_PREFIX_NAME}_{queue_data['uid']}.log")
    os.system(f'ffmpeg -y -i {DOWNLOAD_FILENAME} -vf "scale=1920:1080,setsar=1" -b:v 4M -b:a 192k -ac 2 -ar 44100 -c:a aac -c:v libx264 -preset faster -crf 22 {OUTPUT_FILENAME} > {logfile} 2>&1')
    if os.path.exists(logfile):
        os.remove(logfile)
    logger.info(f'Successfully converting: "{queue_data['name']}"')
    return True

def videoToBin(queue_data, header="TIVIHEADER"):
    input_video = os.path.join(UPLOAD_CACHE_DIR, f"{queue_data['output_filename']}")
    output_bin = os.path.join(UPLOAD_CACHE_DIR, f"{queue_data['output_filename'].replace(VIDEO_FILE_EXTENSION, BIN_FILE_EXTENSION)}")
    try:
        with open(output_bin, 'wb') as out_file:
            out_file.write(header.encode('utf-8'))
            with open(input_video, 'rb') as video_file:
                out_file.write(video_file.read())
        logger.info(f"File '{input_video}' encrypted to '{output_bin}'")
        if os.path.exists(input_video):
            os.remove(input_video)
        return output_bin
    except Exception as e:
        logger.error(f"Error encrypting file: {e}")
        return False

@retry
def uploadToBucket(file_path, bucket_name=ARCHIVE_BUCKET_NAME, verbose=True):
    metadata = {
        'title': bucket_name,
        'collection': 'opensource',
        'mediatype': 'data',
        'scanner': 'Python Uploader',
        'subject': 'single_file_upload'
    }
    item = internetarchive.get_item(bucket_name)
    logger.info(f"Uploading to bucket: {file_path}")
    open(UPLOAD_MARKER, 'w').close()
    item.upload(file_path, access_key=ARCHIVE_ACCESS_KEY_ID, secret_key=ARCHIVE_SECRET_ACCESS_KEY, metadata=metadata, verbose=verbose)
    logger.info(f"File '{file_path}' successfully uploaded")
    if os.path.exists(UPLOAD_MARKER):
        os.remove(UPLOAD_MARKER)
        return True
    return False

def uploadMetadataToBucket():
    if uploadToBucket(METADATA_YT_FILE, ARCHIVE_METADATA_BUCKET_NAME, False):
        logger.info(f"Successfully updating metadata file")
        return True

def getMetadataFromBucket():
    logger.info(f"Getting metadata file from the bucket")
    metadata_archive_bucket = f"{ARCHIVE_URL}/download/{ARCHIVE_METADATA_BUCKET_NAME}/metadata.json"
    try:
        response = requests.get(metadata_archive_bucket, stream=True)
        if response.status_code == 200:
            with open(METADATA_YT_FILE, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            logger.info(f"Metadata file successfully recived from bucket")
            return True
        else:
            logger.info(f"Failed to update or get metadata file: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to update metadata file {METADATA_YT_FILE}: {e}")
        return False

def updateMetadataFile(queue_data):
    try:
        if not os.path.exists(METADATA_YT_FILE):
            getMetadataFromBucket()
        with open(METADATA_YT_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        data.append(queue_data)
        with open(METADATA_YT_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        uploadMetadataToBucket()
    except Exception as e:
        logger.error(e)

def getDownloadInfo():
    RESULT = []
    log_files = glob.glob(os.path.join(LOGS_DIR, f'{DOWNLOAD_THREAD_PREFIX_NAME}_*.log'))
    for log in log_files:
        with open(log) as file_in:
            for line in file_in:
                try:
                    RESULT.append(line[line.index('[#')+len('[#'):line.index(']')])
                except:
                    pass
    try:
        final_result = re.sub(r"^\S+\s|CN:\S+\s|DL:\S+\s", "", RESULT[-1])
    except:
        final_result = []
    return final_result

def getLastLogLine():
    log_files = glob.glob(os.path.join(LOGS_DIR, f'{CONVERT_THREAD_PREFIX_NAME}_*.log'))
    for log in log_files:
        with open(log, 'r') as file:
            lines = file.readlines()
            if lines:
                return lines[-1].strip()
            else:
                return None

def getVideoDuration(queue_data):
    OUTPUT_FILENAME = os.path.join(CACHE_DIR, f"{queue_data['output_filename']}")
    try:
        result = run(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {OUTPUT_FILENAME}', stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True).stdout.strip()
        return result
    except Exception as e:
        logger.error(e)
        return 0

# def remove_fake_header(input_bin, output_video, header="TIVIHEADER"):
#     header_length = len(header.encode('utf-8'))
#     with open(input_bin, 'rb') as in_file:
#         in_file.seek(header_length)
#         remaining_data = in_file.read()
#     with open(output_video, 'wb') as out_file:
#         out_file.write(remaining_data)
