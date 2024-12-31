from core.variables import *
from core.providers.filmix import *

def do_search(query, page=1):
    url = 'https://filmix.fm/engine/ajax/sphinx_search.php'
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

def getActiveQueue():
    result = subprocess.run(['ps', '-aux'], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to get processess list: {result.stderr}")
        return []
    processes = result.stdout.splitlines()
    tivi_processes = []
    for process in processes:
        match = re.search(r'tivi-queue (\w+) (\d+)', process)
        if match:
            process_type = match.group(1)
            kp_id = match.group(2)
            with open(os.path.join(QUEUE_DIR, f"{kp_id}.json"), 'r') as file:
                data = json.load(file)
            tivi_processes.append({"type": process_type, "kp_id": int(kp_id), "name": data['name'], "url": data['url']})
    return tivi_processes

@retry
def getDownloadURL(url):
    logger.info(f'Getting Download URL for : {url}')
    return ProviderAPI(url).getMovie('480p')

def addToQueue(json_data):
    kp_id = json_data['kp_id']
    queue_file = os.path.join(QUEUE_DIR, f"{kp_id}.json")
    with open(queue_file, 'w') as file:
        json.dump(json_data, file, indent=4, ensure_ascii=False)
    if os.path.exists(queue_file):
        logger.info(f'Added to Queue : {kp_id}')
        return True
    return False

def getQueueData(kp_id):
    with open(os.path.join(QUEUE_DIR, f"{kp_id}.json"), 'r') as file:
        data = json.load(file)
    return data

def getQueueList():
    return [f[:-5] for f in os.listdir(QUEUE_DIR) if f.endswith('.json')]

@retry
def downloadCacheFile(link, kp_id):
    logger.info(f'Downloading: {kp_id}')
    logfile = os.path.join(LOGS_DIR, f"{DOWNLOAD_THREAD_PREFIX_NAME}_{kp_id}.log")
    DOWNLOAD_FILENAME = f"{DOWNLOAD_THREAD_PREFIX_NAME}-{kp_id}{VIDEO_FILE_EXTENSION}"
    os.system(f'aria2c -k 1M -s {DOWNLOAD_THREADS} -x {DOWNLOAD_THREADS} -o "..{os.path.join(CACHE_DIR, f"{DOWNLOAD_FILENAME}")}" "{link}" > {logfile} 2>&1')
    if os.path.exists(logfile):
        os.remove(logfile)
    logger.info(f'Successfully downloaded: {kp_id}')

def convertVideo(kp_id):
    logger.info(f'Converting: {kp_id}')
    DOWNLOAD_FILENAME = f"{DOWNLOAD_THREAD_PREFIX_NAME}-{kp_id}{VIDEO_FILE_EXTENSION}"
    logfile = os.path.join(LOGS_DIR, f"convert_{kp_id}.log")
    os.system(f'ffmpeg -y -i {os.path.join(CACHE_DIR, f"{DOWNLOAD_FILENAME}")} -vf "scale=1920:1080,setsar=1" -b:v 4M -b:a 192k -ac 2 -ar 44100 -c:a aac -c:v libx264 -preset slow -crf 22 {os.path.join(CACHE_DIR, f"{kp_id}{VIDEO_FILE_EXTENSION}")} > {logfile} 2>&1')
    if os.path.exists(logfile):
        os.remove(logfile)
    logger.info(f'Successfully converting: {kp_id}')


def add_fake_header(input_video, output_bin, header="TIVIHEADER"):
    with open(output_bin, 'wb') as out_file:
        out_file.write(header.encode('utf-8'))
        with open(input_video, 'rb') as video_file:
            out_file.write(video_file.read())

# def remove_fake_header(input_bin, output_video, header_size=10):
#     # Открываем бинарный файл с заголовком
#     with open(input_bin, 'rb') as bin_file:
#         # Пропускаем первые `header_size` байт (размер заголовка)
#         bin_file.seek(header_size)
#
#         # Читаем оставшуюся часть файла и записываем её в новый видеофайл
#         with open(output_video, 'wb') as video_file:
#             video_file.write(bin_file.read())

def uploadToArchiveORG(kp_id):
    old_file = os.path.join(CACHE_DIR, f"{kp_id}{VIDEO_FILE_EXTENSION}")
    new_file = os.path.join(CACHE_DIR, f"{kp_id}.bin")
    add_fake_header(old_file, new_file)
    aws_access_key_id = "NNUXnuHlaYYyTl67"
    aws_secret_access_key = "WKwXgP3VStr07nFY"
    identifier = "tivi_temp"
    md = {'title': identifier, 'collection': identifier, 'mediatype': 'data', 'scanner': 'VM Brasseur', 'subject': identifier}
    item = internetarchive.get_item(identifier)
    item.upload(new_file, access_key=aws_access_key_id, secret_key=aws_secret_access_key, metadata=md, verbose=True)
    if os.path.exists(new_file):
        os.remove(new_file)
    logger.info(f"Item URL is: https://archive.org/details/{identifier}")
