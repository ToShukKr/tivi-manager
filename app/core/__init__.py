from core.variables import *

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
