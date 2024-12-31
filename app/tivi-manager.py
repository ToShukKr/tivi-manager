#!/usr/local/bin/python
# curl -X POST -H "Content-Type: application/json" -d '{"name": "Секретные материалы", "page": "1"}' http://127.0.0.1:8080/api/v1/search
# curl -X POST -H "Content-Type: application/json" -d '{"url": "https://filmix.fm/films/komedia/16490-trudnyy-rebenok-2-1991.html"}' http://127.0.0.1:8080/api/v1/get-url
# curl -X POST -H "Content-Type: application/json" http://127.0.0.1:8080/api/v1/get-list-queue
from core import *

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
logging.getLogger('apscheduler').setLevel(logging.WARNING)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/v1/search', methods=['POST'])
def search():
    json_data = request.get_json()
    name = json_data.get('name')
    page = json_data.get('page')
    if not name or not page:
        return jsonify({'error': 'Missing name or page in JSON data'}), 400
    return jsonify(do_search(name, page))

@app.route('/api/v1/get-url', methods=['POST'])
def get_url():
    json_data = request.get_json()
    if 'kp_id' not in json_data or not json_data['kp_id']:
        return jsonify({'error': 'kp_id is required!'}), 400
    addToQueue(json_data)
    return jsonify(json_data)

@app.route('/api/v1/get-list-queue', methods=['POST'])
def get_list_queue():
    return jsonify(getActiveQueue())

@scheduler.task('interval', id='runQueueJob', seconds=60)
def job():
    if len(getActiveQueue()) < MAX_QUEUE:
        if getQueueList():
            kp_id = getQueueList()[0]
            type = getQueueData(kp_id)['type']
            logger.info(f"Running a NEW QUEUE: {kp_id}")
            os.system(f"tivi-queue {type} {kp_id} &")
        else:
            logger.info(f"Checking for running new queues")
    else:
        logger.info(f"QUEUE Is already operating: {getActiveQueue()[0]['kp_id']}")

if __name__ == '__main__':
    app.run(debug=True, port=8080, host="0.0.0.0")
