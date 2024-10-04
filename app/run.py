# curl -X POST http://127.0.0.1:8080/api/v1/search -H "Content-Type: application/json" -d '{"name": "Секретные материалы", "page": "1"}'
# curl -X POST http://127.0.0.1:8080/api/v1/get-url -H "Content-Type: application/json" -d '{"url": "https://filmix.fm/films/komedia/16490-trudnyy-rebenok-2-1991.html"}'
from core import *

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
    print(json_data)
    print(getDownloadURL(json_data['url']))
    return jsonify(json_data)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
