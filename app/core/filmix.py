import requests
import base64
import re
from bs4 import BeautifulSoup as bs
from time import sleep

REQUEST_TIMEOUT = 10

class ProviderAPI():
    __version__ = 1.1

    def __init__(self, url):
        self.provider_name = "filmix"
        self.url = url
        self.name = self.getName()
        self.id = self.getID()
        self.provider_url = self.getProviderURL()

    def getProviderURL(self):
        return self.url.split('/')[0:3].__str__().replace("'", "").replace("[", "").replace("]", "").replace(", ", "/")

    def getName(self):
        link_name = self.url.split('/')[-1].replace('.html','')
        return re.sub(r'^.*?-', '', link_name).replace('-', ' ')

    def getIDFromURL(self, url):
        return url.rsplit('/', 1)[-1].split('-')[0]

    def getID(self):
        return self.url.split('-')[0].split('/')[-1]

    def decodeBase64(self, encoded_url):
        tokens = (":<:bzl3UHQwaWk0MkdXZVM3TDdB", ":<:SURhQnQwOEM5V2Y3bFlyMGVI", ":<:bE5qSTlWNVUxZ01uc3h0NFFy", ":<:Mm93S0RVb0d6c3VMTkV5aE54", ":<:MTluMWlLQnI4OXVic2tTNXpU")
        clean_encoded_url = encoded_url[2:].replace(r"\/","/")
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

        additional_cookies = "dle_password=483f1fce06d055e8dae9b585551e9603; dle_user_id=1639040"
        combined_cookies = "{}; {}".format(session_cookie, additional_cookies)

        url = "{}{}".format(self.provider_url, "/api/movies/player-data?t=1651831246576")
        payload = {'post_id': id, 'showfull': 'true'}
        files = []
        headers = {'x-requested-with': 'XMLHttpRequest', 'Cookie': combined_cookies}

        response = requests.request("POST", url, headers=headers, data=payload, files=files, timeout=REQUEST_TIMEOUT)
        return response.json()

    def getTranslations(self):
        translation_list = []
        translations = self.getStramData(self.url)['message']['translations']['video']
        for i in translations:
            translation_list.append(i)
        return translation_list

    def getContentURL(self, URL, translation_id=0):
        stream_data = self.getStramData(URL)['message']['translations']['video']
        translation_key = list(stream_data.keys())[translation_id] if translation_id in range(len(stream_data)) else list(stream_data.keys())[0]
        translation_url = stream_data.get(translation_key, list(stream_data.values())[0])
        content_url = self.decodeBase64(translation_url)
        encoded_video_content = requests.get(content_url.decode("UTF-8"), timeout=REQUEST_TIMEOUT)
        return self.decodeBase64(encoded_video_content.content.decode("UTF-8")).decode("UTF-8")

    def getESList(self, id):
        # [0] - season, [1] - episode
        return id.split('s')[1].split('e')

    def getContentType(self):
        try:
            self.getContentURL(self.url)
            return "serial"
        except:
            return "movie"

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
                "seasons": {1: "Season"},
                "episodes": {1: "Episode"}
            }
            return content_template

        content_template = {}
        season = {}
        episode = {}
        for i in eval(decoded_content_json):
            series = {}
            for v in i['folder']:
                s = self.getESList(v['id'])[0]
                e = self.getESList(v['id'])[1]
                series[e] = "Episode {}".format(e)

            season[s] = "Season {}".format(s)

            episodes_json = {
            s : series
            }
            episode.update(episodes_json)

        content_template = {
            "seasons": season,
            "episodes": episode
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

    def getStream(self, season, episode, quality="720p", translation_id=0):
        if not quality in ["360p", "480p", "720p"]:
            available_res = '"360p", "480p", "720p"'
            raise ValueError(f'Resolution "{quality}" is not defined\nUse one of these: {available_res}')

        video_content = eval(self.getContentURL(self.url, translation_id))
        for i in video_content:
            folder = i['folder']
            for folder in i['folder']:
                if self.getESList(folder['id'])[0] == season:
                    for folder in i['folder']:
                        if self.getESList(folder['id'])[1] == episode:
                            return self.parseURLs(folder['file'], quality)
        raise ValueError('Error, episode or season not found')


    def getMovie(self, quality="720p", translation_id=0):
        if not quality in ["360p", "480p", "720p"]:
            available_res = '"360p", "480p", "720p"'
            raise ValueError(f'Resolution "{quality}" is not defined\nUse one of these: {available_res}')
        content_url = self.decodeBase64(self.getStramData(self.url)['message']['translations']['video'][self.getTranslations()[translation_id]]).decode("UTF-8")
        return self.parseURLs(content_url, quality)


# url = "https://filmix.my/multser/komedia/9184-v-l-simpsony-1989.html"
# filmix = ProviderAPI(url)
# print(filmix.name)
# print(filmix.getSeasons())
# print(filmix.getStream('1', '8', '720p'))

# url = "https://filmix.my/mults/otechestvennye/52316-v-priklyucheniya-vasi-kurolesova-1981.html"
# filmix = ProviderAPI(url)
# print(filmix.name)
# print(filmix.getMovie('720p'))

# url = "https://filmix.my/film/triller/6123-v-ff-terminator-2-sudnyy-den-1991.html"
# filmix = ProviderAPI(url)
#
# print(filmix.getStramData(url))
# print(filmix.getMovie())

# url = "https://filmix.my/mults/otechestvennye/52316-v-priklyucheniya-vasi-kurolesova-1981.html"
# url = "https://filmix.my/seria/semejnye/101429-v--voroniny-2021.html"
# filmix = ProviderAPI(url)
# print(filmix.getSeasons())

# url = "https://filmix.my/seria/drama/8349-v-sekretnye-materialy-big-2002.html"
# filmix = ProviderAPI(url)
# print(filmix.getStream('8', '12', '720p', 1))