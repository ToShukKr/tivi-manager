import requests
import base64
import re
from bs4 import BeautifulSoup as bs
from time import sleep

REQUEST_TIMEOUT = 10

class ProviderAPI():
    __version__ = 1.0

    def __init__(self, url):
        self.filmix_url = 'https://filmix.fm'
        self.url = url
        self.name = self.getName()

    def getName(self):
        link_name = self.url.split('/')[-1].replace('.html','')
        return re.sub(r'^.*?-', '', link_name).replace('-', ' ')

    def getIDFromURL(self, url):
        return url.rsplit('/', 1)[-1].split('-')[0]

    def decodeBase64(self, encoded_url):
        tokens = (":<:bzl3UHQwaWk0MkdXZVM3TDdB", ":<:SURhQnQwOEM5V2Y3bFlyMGVI", ":<:bE5qSTlWNVUxZ01uc3h0NFFy", ":<:Mm93S0RVb0d6c3VMTkV5aE54", ":<:MTluMWlLQnI4OXVic2tTNXpU")
        clean_encoded_url = encoded_url[2:].replace("\/","/")
        while True:
            for token in tokens:
                clean_encoded_url = clean_encoded_url.replace(token, "")
            if not ":<:" in clean_encoded_url:
                break
        return base64.b64decode(clean_encoded_url)

    def getStramData(self, url):
        id = self.getIDFromURL(url)
        session = requests.Session()
        response = session.get(url)
        try:
            session_cookie = "FILMIXNET={}".format(session.cookies.get_dict()['FILMIXNET'])
        except:
            session_cookie = 'FILMIXNET=ms604jm828es9j6t83qs3ptmf9'
        url = "{}{}".format(self.filmix_url, "/api/movies/player-data?t=1651831246576")
        payload={'post_id': id, 'showfull': 'true'}
        files=[]
        headers = {'x-requested-with': 'XMLHttpRequest', 'Cookie': session_cookie}
        response = requests.request("POST", url, headers=headers, data=payload, files=files, timeout=REQUEST_TIMEOUT)
        return response.json()

    def getTranslations(self):
        translation_list = []
        translations = self.getStramData(self.url)['message']['translations']['video']
        for i in translations:
            translation_list.append(i)
        return translation_list

    def getContentURL(self, URL, translation=None):
        stream_data = self.getStramData(URL)['message']['translations']['video']

        if not translation:
            try:
                translation = self.getTranslations()[0]
            except:
                translation = 'Original'

        translation_url = stream_data[translation]

        content_url = self.decodeBase64(translation_url)
        encoded_video_content = requests.get(content_url.decode("UTF-8"), timeout=REQUEST_TIMEOUT)
        return self.decodeBase64(encoded_video_content.content.decode("UTF-8")).decode("UTF-8")

    def getESList(self, id):
        # [0] - season, [1] - episode
        return id.split('s')[1].split('e')

    def getSeasons(self, translation=None):
        if not translation:
            try:
                translation = self.getTranslations()[0]
            except:
                translation = 'Original'

        try:
            decoded_content_json = self.getContentURL(self.url)
        except:
            content_template = {
            translation: {
                "translator_id": 0,
                "seasons": {1: "Season"},
                "episodes": {1: "Episode"}
                }
            }
            return content_template

        content_template = {}
        seasons_template = {}
        season = {}
        episode = {}
        for i in eval(decoded_content_json):
            series = {}
            for v in i['folder']:
                s = self.getESList(v['id'])[0]
                e = self.getESList(v['id'])[1]
                series[e] = "Серия {}".format(e)

            season[s] = "Сезон {}".format(s)

            episodes_json = {
            s : series
            }
            episode.update(episodes_json)

        content_template = {
        translation: {
            "translator_id": 0,
            "seasons": season,
            "episodes": episode
            }
        }
        return content_template

    def parseURLs(self, urls, quality):
        quality_list = []
        for i in urls.split(','):
            quality_list.append(i[i.find('[')+len('['):i.rfind(']')])
            if '1080p' in quality_list:
                quality_list.remove('1080p')
            if not quality in quality_list:
                get_quality = "[{}]".format(quality_list[-1])
            else:
                get_quality = "[{}]".format(quality)
        for i in urls.split(','):
            if i.startswith(get_quality):
                return i.replace(get_quality,'')

    def getStream(self, season, episode, quality, translation=None):
        if not quality in ["360p", "480p", "720p"]:
            available_res = '"360p", "480p", "720p"'
            raise ValueError(f'Resolution "{quality}" is not defined\nUse one of these: {available_res}')

        video_content = eval(self.getContentURL(self.url))
        for i in video_content:
            folder = i['folder']
            for folder in i['folder']:
                if self.getESList(folder['id'])[0] == season:
                    for folder in i['folder']:
                        if self.getESList(folder['id'])[1] == episode:
                            return self.parseURLs(folder['file'], quality)
        raise ValueError('Error, episode or season not found')


    def getMovie(self, quality, translation=None):
        if not quality in ["360p", "480p", "720p"]:
            available_res = '"360p", "480p", "720p"'
            raise ValueError(f'Resolution "{quality}" is not defined\nUse one of these: {available_res}')
        content_url = self.decodeBase64(self.getStramData(self.url)['message']['translations']['video'][self.getTranslations()[0]]).decode("UTF-8")
        return self.parseURLs(content_url, quality)


# url = "https://filmix.ac/films/drama/2982-nkj-sekretnye-materialy-hochu-verit-2008.html"
# filmix = ProviderAPI(url)
# print(filmix.name)
# print(filmix.getSeasons())
# print(filmix.getStream('1', '8', '720p'))

# url = "https://filmix.fm/films/drama/2982-nkj-sekretnye-materialy-hochu-verit-2008.html"
# filmix = ProviderAPI(url)
# print(filmix.name)
# print(filmix.getSeasons())
# print(filmix.getMovie('480p'))
