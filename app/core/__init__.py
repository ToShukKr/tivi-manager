from core.variables import *
from core.providers.filmix import *

def do_search(query, page=1):
    url = 'https://filmix.fm/engine/ajax/sphinx_search.php'
    headers = {'x-requested-with': 'XMLHttpRequest'}
    data = {'story': query, 'search_start': page, 'film': 'on'}
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
