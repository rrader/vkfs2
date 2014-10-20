import vk


class VKDelegate(object):
    def __init__(self, username, password):
        self.vkapi = vk.API('4597332', username, password, scope='friends,photos,audio,video,wall,audio')
        self.vkapi.access_token='O0P0jAGQB8Vp7Y0XOIkM'
    
    def wall_post(self):
        self.vkapi.wall.post(message="Hello, world")

    def profile(self):
        return self.vkapi.users.get(fields='sex, bdate, city, country, photo_50, photo_100, photo_200_orig, photo_200, photo_400_orig, photo_max, photo_max_orig, photo_id, online, online_mobile, domain, has_mobile, contacts, connections, site, education, universities, schools, can_post, can_see_all_posts, can_see_audio, can_write_private_message, status, last_seen, common_count, relation, relatives, counters, screen_name, maiden_name, timezone, occupation,activities, interests, music, movies, tv, books, games, about, quotes ')[0]

    def my_audio_files(self):
        return self.vkapi.audio.get()['items']

    def recommended_audio_files(self):
        return self.vkapi.audio.getRecommendations()['items']

    def search_audio_files(self, query):
        print("VK: search %s" % query)
        return self.vkapi.audio.search(q=query, performer_only=1)['items']
