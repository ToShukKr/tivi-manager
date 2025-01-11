#!/usr/local/bin/python
# curl -X POST -H "Content-Type: application/json" -d '{"name": "Секретные материалы", "page": "1"}' http://127.0.0.1:8080/api/v1/search
# curl -X POST -H "Content-Type: application/json" -d '{"url": "https://filmix.fm/films/komedia/16490-trudnyy-rebenok-2-1991.html"}' http://127.0.0.1:8080/api/v1/get-info
# curl -X POST -H "Content-Type: application/json" -d '{"id": 12, "name": "Трудный ребенок", "url": "https://filmix.fm/films/komedia/16490-trudnyy-rebenok-2-1991.html", "translation": {"id":0, "name":"LostFilm"}}' http://127.0.0.1:8080/api/v1/add-to-queue
# curl -X POST -H "Content-Type: application/json" http://127.0.0.1:8080/api/v1/get-list-queue
# curl -X POST -H "Content-Type: application/json" http://127.0.0.1:8080/api/v1/get-metadata
from core import *

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
logging.getLogger('apscheduler').setLevel(logging.INFO)

getMetadataFromBucket()

@app.route('/')
def index():
    return render_template('index.html', current_path=request.path)

@app.route('/movies')
def movies():
    return render_template('index.html', current_path=request.path)

@app.route('/api/v1/search', methods=['POST'])
def search():
    json_data = request.get_json()
    name = json_data.get('name')
    page = json_data.get('page')
    if not name or not page:
        return jsonify({'error': 'Missing name or page in JSON data'}), 400
    return jsonify(do_search(name, page))

@app.route('/api/v1/get-info', methods=['POST'])
def get_translate():
    data = {}
    json_data = request.get_json()
    url = json_data.get('url')
    if not url:
        return jsonify({'error': 'Missing url in JSON data'}), 400
    filmix = ProviderAPI(url)
    type = filmix.getContentType()
    translations = [{"id": idx, "name": name} for idx, name in enumerate(filmix.getTranslations())]
    if type == "series":
        data = filmix.getSeasons()
    return {"translations": translations, "type": type, "data": data}

@app.route('/api/v1/add-to-queue', methods=['POST'])
def add_to_queue():
    #TODO. Add checking already existing item in DB
    # Content type
    json_data = request.get_json()
    id = json_data.get('id')
    url = json_data.get('url')
    name = json_data.get('name')
    translation = json_data.get('translation')
    uid = getRandomName()
    filmix = ProviderAPI(url)
    type = filmix.getContentType()
    if type == "series":
        data = filmix.getSeasons()['episodes']
        all_series = []
        for i in data:
            for e in data[i]:
                all_series.append(f"{i}-{e}")
        for item in all_series:
            season = item.split("-")[0]
            episode = item.split("-")[-1]
            video_file_name = f"{id}_{season}_{episode}_{uid}"
            queue_template = {
                "uid": uid,
                "kp_id": f"{id}{uid}",
                "fx_id": id,
                "output_filename": f"{video_file_name}.mp4",
                "url": url,
                "name": name,
                "translation": translation,
                "type": type,
                "bucket": ARCHIVE_BUCKET_NAME,
                "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": "",
                "data": {"season": season, "episode": episode}
                }
            queue_file = os.path.join(QUEUE_DIR, f"{video_file_name}.json")
            with open(queue_file, 'w') as file:
                json.dump(queue_template, file, indent=4, ensure_ascii=False)
            if os.path.exists(queue_file):
                logger.info(f'Added to Queue : "{name} (Season:{season}, Episode:{episode}) ({translation['name']})"')
        return jsonify({"status": True, "message": f"Successfully added series '{name} ({translation['name']})' to queue", "result": []}), 200

    queue_template = {
        "uid": uid,
        "kp_id": f"{id}{uid}",
        "fx_id": id,
        "output_filename": f"{id}_{uid}.mp4",
        "url": url,
        "name": name,
        "translation": translation,
        "type": type,
        "bucket": ARCHIVE_BUCKET_NAME,
        "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration": "",
        "data": []
        }
    queue_file = os.path.join(QUEUE_DIR, f"{id}_{uid}.json")
    with open(queue_file, 'w') as file:
        json.dump(queue_template, file, indent=4, ensure_ascii=False)
    if os.path.exists(queue_file):
        logger.info(f'Added to Queue : "{name} ({translation['name']})"')
        return jsonify({"status": True, "message": f"Successfully added '{name} ({translation['name']})' to queue", "result": []}), 200
    return jsonify({"status": False, "message": f"Failed to add movie '{name} ({translation['name']})' to queue", "result": []}), 200

@app.route('/api/v1/get-metadata', methods=['POST'])
def get_metadata():
    if os.path.exists(METADATA_YT_FILE):
        with open(METADATA_YT_FILE, 'r', encoding='utf-8') as file:
            return jsonify({"status": True, "message": f"Metadata object", "result": json.load(file)}), 200
    return jsonify({"status": False, "message": f"Failed to read metadata file", "result": []}), 200

@app.route('/api/v1/get-list-queue', methods=['POST'])
def get_list_queue():
    result = {"queue": [], "in_progress": []}
    if os.path.exists(QUEUE_DIR) and os.path.isdir(QUEUE_DIR):
        for file_name in os.listdir(QUEUE_DIR):
            file_path = os.path.join(QUEUE_DIR, file_name)
            if os.path.isfile(file_path) and file_name.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = json.load(file)
                    result["queue"].append(content)

    json_files = [file for file in os.listdir(IN_PROGRESS) if file.endswith('.json')]
    if not json_files:
        logger.debug(f'Queue directory is empty')
        return []
    first_queue_file = json_files[0]
    with open(os.path.join(IN_PROGRESS, first_queue_file), 'r', encoding='utf-8') as file:
        content = json.load(file)
    result["in_progress"].append(content)
    result["in_progress"][0]["translation"] = str(content['translation']['name'])

    download_file = os.path.join(LOGS_DIR, f"{DOWNLOAD_THREAD_PREFIX_NAME}_{content['uid']}.log")
    status = ""
    log = ""
    if os.path.exists(download_file):
        status = "Downloading"
        log = getDownloadInfo()
    elif os.path.exists(UPLOAD_MARKER):
        status = "Uploading"
        log = "Uploading"
    result["in_progress"][0]["status"] = status
    result["in_progress"][0]["log"] = log
    return jsonify({"status": True, "message": f"List of qeues and in progress", "result": result}), 200

@scheduler.task('interval', id='runQueueJob', seconds=60)
def job():
    # TODO
    # Check if file already in DB
    # Add current time to object
    if DISABLE_QUEUE:
        logger.info(f'Currently queue is disabled, please set DISABLE_QUEUE=False')
        return
    if currentActiveDownloads() == 0:
        try:
            json_files = [file for file in os.listdir(QUEUE_DIR) if file.endswith('.json')]
            if not json_files:
                logger.debug(f'Queue directory is empty')
                return False
            first_queue_file = json_files[0]
            queue_path = os.path.join(QUEUE_DIR, first_queue_file)
            in_progress_path = os.path.join(IN_PROGRESS, first_queue_file)
            shutil.copy(queue_path, in_progress_path)

            with open(in_progress_path, 'r', encoding='utf-8') as file:
                queue_current_data = json.load(file)
            download_url = getDownloadURL(queue_current_data)
            downloadCacheFile(download_url, queue_current_data)
            duration = getVideoDuration(queue_current_data)
            queue_current_data["duration"] = str(duration)
            upload_bin_file = videoToBin(queue_current_data)
            if queue_current_data['type'] == "series":
                series_dir = queue_current_data['fx_id']
                print(series_dir)
                uploadToBucket({f"{series_dir}/{queue_current_data['output_filename'].replace(VIDEO_FILE_EXTENSION, BIN_FILE_EXTENSION)}": upload_bin_file}, verbose=True)
            else:
                uploadToBucket(upload_bin_file, verbose=True)
            if os.path.exists(upload_bin_file):
                os.remove(upload_bin_file)
            updateMetadataFile(queue_current_data)
            if os.path.exists(queue_path):
                os.remove(queue_path)
            if os.path.exists(in_progress_path):
                os.remove(in_progress_path)
        except Exception as e:
            logger.error(e)
    else:
        download_result = getDownloadInfo()
        if download_result:
            logger.info(f"Active number of queue is: {currentActiveDownloads()}. Downloading status: {download_result}")


if __name__ == '__main__':
    app.run(debug=os.getenv("DEBUG", False), port=8080, host="0.0.0.0")
