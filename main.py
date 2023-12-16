import requests
import random
import m3u8
import time


class TwitchBase:
    def __init__(self, _channel_name):
        self._CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
        self._GQL_URL = "https://gql.twitch.tv/gql"
        self.CHANNEL_NAME = _channel_name
        self.LIVE_MANIFEST = None

        self.initialize()

    def _get_access_token(self, variables, data_path):
        try:
            body = {
                "operationName": "PlaybackAccessToken_Template",
                "variables": variables,
                "query": """
                    query PlaybackAccessToken_Template(
                        $login: String!
                        $isLive: Boolean!
                        $vodID: ID!
                        $isVod: Boolean!
                        $playerType: String!
                    ) {
                        streamPlaybackAccessToken(
                            channelName: $login
                            params: {
                                platform: "web"
                                playerBackend: "mediaplayer"
                                playerType: $playerType
                            }
                        ) @include(if: $isLive) {
                            value
                            signature
                            authorization {
                                isForbidden
                                forbiddenReasonCode
                            }
                        }
                        videoPlaybackAccessToken(
                            id: $vodID
                            params: {
                                platform: "web"
                                playerBackend: "mediaplayer"
                                playerType: $playerType
                            }
                        ) @include(if: $isVod) {
                            value
                            signature
                        }
                    }
                """,
            }

            headers = {
                "Accept": "/",
                "Client-ID": self._CLIENT_ID,
                "Content-Type": "application/json; charset=UTF-8",
            }

            response = requests.post(self._GQL_URL, json=body, headers=headers)
            response.raise_for_status()
            results = response.json()

            token_data = results.get("data", {}).get(
                f"{data_path}PlaybackAccessToken", {}
            )
            access_token = token_data.get("value")

            token_data = results.get("data", {}).get(
                f"{data_path}PlaybackAccessToken", {}
            )
            signature = token_data.get("signature")

            if access_token and signature:
                return (access_token, signature)

            raise Exception(f"ERROR FETCHING ACCESS TOKEN\n{str(e)}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"INVALID ACCESS TOKEN REQUEST\n{str(e)}")

    def _get_manifest(self, token_data, url):
        try:
            params = {
                "allow_source": "true",
                "allow_audio_only": "true",
                "allow_spectre": "true",
                "p": random.randint(1000000, 10000000),
                "player": "twitchweb",
                "playlist_include_framerate": "true",
                "segment_preference": "4",
                "token": token_data[0],
                "sig": token_data[1],
            }

            headers = {
                "Accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
                "Referer": "",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            }

            response = requests.get(
                url,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            results = response.content.decode("utf-8")

            if results:
                return results

            raise Exception(f"ERROR FETCHING MANIFEST\n{str(e)}")

        except Exception as e:
            raise Exception(f"INVALID MANIFEST REQUEST\n{str(e)}")

    def initialize(self):
        try:
            variables = {
                "isLive": True,
                "isVod": False,
                "vodID": "",
                "login": self.CHANNEL_NAME,
                "playerType": "site",
            }

            token_data = self._get_access_token(variables, "stream")
            live_m3u8_content = self._get_manifest(
                token_data=token_data,
                url=f"https://usher.ttvnw.net/api/channel/hls/{self.CHANNEL_NAME}.m3u8",
            )
            self.LIVE_MANIFEST = m3u8.loads(live_m3u8_content)

        except Exception as e:
            raise Exception(f"ERROR FETCHING MANIFEST\n{e}")

    def get_playlist(self):
        try:
            headers = {
                "Accept": "application/x-mpegURL, application/vnd.apple.mpegurl, application/json, text/plain",
                "Referer": "",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            }

            response = requests.get(
                self.LIVE_MANIFEST.playlists[1].uri,
                headers=headers,
            )
            response.raise_for_status()
            results = response.content.decode("utf-8")
            playlist = m3u8.loads(results)

            self.get_ts_file(playlist.segments[-1])

            if results:
                return results

            raise Exception(f"ERROR FETCHING MANIFEST\n{str(e)}")

        except Exception as e:
            raise Exception(f"INVALID MANIFEST REQUEST\n{str(e)}")

    def get_ts_file(self, segment):
        try:
            headers = {
                "Referer": "",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            }

            response = requests.get(
                segment.uri,
                headers=headers,
            )
            response.raise_for_status()

            with open("data/vid.mp4", "ab") as f:
                f.write(response.content)
                print("downloaded")

            if response.content:
                return True

            raise Exception(f"ERROR FETCHING MANIFEST\n{str(e)}")

        except Exception as e:
            raise Exception(f"INVALID MANIFEST REQUEST\n{str(e)}")


if __name__ == "__main__":
    tb = TwitchBase("frexs")

    while True:
        tb.get_playlist()
        time.sleep(2)
