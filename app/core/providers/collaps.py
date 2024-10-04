import requests
from bs4 import BeautifulSoup
import re
import json
import os

class ProviderAPI():
    __version__ = 1.0

    def __init__(self, kp_id):
        self.provider_name = 'collaps'
        self.kp_id = kp_id
        self.name = None
        self.translations = "Original"
        self.contentType = self.getContentType()

    def getPageData(self):
        for i in range(10):
            url = f"https://api.delivembd.ws/embed/kp/{self.kp_id}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.content
            if response.status_code == 429:
                print("Too many requests, waiting 5 seconds to new request")
                sleep(10)
                continue
            print("Failed to retrieve the webpage.")
            return False

    def getmakePlayerContent(self):
        soup = BeautifulSoup(self.getPageData(), 'html.parser')
        scripts = soup.find_all('script', {'data-name': 'mk'})
        for script in scripts:
            if script.string:
                return script.string

    def getContentType(self):
        '''
        Determine type of content: `serial` or `movie`
        '''
        lines = self.getmakePlayerContent().split("\n")
        for line in lines:
            if "seasons" in line:
                return 'serial'
        return 'movie'

    def getSeriesJSONContent(self):
        clear_text = self.getmakePlayerContent()
        start_index = clear_text.find("seasons:[{")
        end_index = clear_text.find("}]}]")
        seasons_text = clear_text[start_index + len("seasons:[") : end_index].strip()
        return json.loads(json.dumps("["+seasons_text+"}]}]"))

    def getMovie(self, quality=None, translation=None):
        clear_text = self.getmakePlayerContent()
        start_index = clear_text.find("hls:")
        if start_index != -1:
            end_index = clear_text.find("audio:", start_index)
            if end_index != -1:
                hls_text = clear_text[start_index:end_index].strip()
                hls_link = re.search(r'"(.*?)"', hls_text)
                if hls_link:
                    return hls_link.group(1)
                else:
                    print("HLS link not found.")
            else:
                print("End of 'audio:' not found.")
        else:
            print("Start of 'hls:' not found. Looks like its serial?")

        return False

    def getStream(self, season, episode, quality=None, translation=None):
        sorted_content = sorted(json.loads(self.getSeriesJSONContent()), key=lambda x: x['season'])
        for se in sorted_content:
            if int(se['season']) == int(season):
                for ep in se['episodes']:
                    if int(ep['episode']) == int(episode):
                        return ep['hls']
        return None

    def getSeasons(self):
        full_template = {
                    "result":{
                      "name": self.name,
                      "type": self.contentType,
                      "translations": self.translations,
                      "seasons":{},
                      "episodes":{}
                     }
                    }
        season_count_id = 0
        episodes_count_id = 0
        seasons_template = {}
        episodes_template = {}

        if self.contentType == 'serial':
            sorted_content = sorted(json.loads(self.getSeriesJSONContent()), key=lambda x: x['season'])
            for se in sorted_content:
                for ep in se['episodes']:
                    season_count_id = season_count_id  + 1
                    seasons_template[se['season']] = "Season"
                full_template['result']['seasons'] = seasons_template
                season_count_id = 0
            for se in sorted_content:
                current_episodes_template = {}
                episodes_count_id = episodes_count_id  + 1
                current_episodes_count_id = 0
                for ep in se['episodes']:
                    current_episodes_count_id = current_episodes_count_id + 1
                    current_episodes_template[current_episodes_count_id] = ep['title']
                episodes_template[episodes_count_id] = current_episodes_template
            full_template['result']['episodes'] = episodes_template

        if self.contentType == 'movie':
            full_template['result']['episodes'] = {1: 'Episode'}
            full_template['result']['seasons'] = {1: 'Season'}
        return full_template


kp_id = "443"
# kp_id = "479090"
# kp_id = "4531254"
# kp_id = "77046"
collaps = ProviderAPI(kp_id)
print(collaps.getSeasons())
# print(collaps.getStream('24', '5', '1080p', None))
print(collaps.getMovie('720p', 'Живов Юрий (Авторский)'))
