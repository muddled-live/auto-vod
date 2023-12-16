import os
import requests
import random
import m3u8
import time
import subprocess
import shutil


class TwitchBase:
    def __init__(self, _channel_name):
        self._CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
        self._GQL_URL = "https://gql.twitch.tv/gql"
        self.TMP_STORAGE = "autovod/tmp"
        self.CHANNEL_NAME = _channel_name
        self.LIVE_MANIFEST = None
        self.uri_list = []
        self.vod_duration = 0

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

        except requests.HTTPError as e:
            if response.status_code == 404:
                print("Channel not live")
            else:
                print(f"HTTP error occurred: {e}")

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

            if results:
                return playlist

            raise Exception(f"ERROR FETCHING MANIFEST\n{str(e)}")

        except Exception as e:
            raise Exception(f"INVALID MANIFEST REQUEST\n{str(e)}")

    def start(self, target_duration):
        try:
            if not os.path.exists(self.TMP_STORAGE):
                os.makedirs(self.TMP_STORAGE)

            while self.vod_duration < target_duration:
                playlist = self.get_playlist()
                for seg in playlist.segments:
                    if seg.uri not in self.uri_list:
                        response = requests.get(seg.uri)
                        self.uri_list.append(seg.uri)
                        self.vod_duration += seg.duration

                        with open(
                            f"{self.TMP_STORAGE}/{len(self.uri_list)}.ts", "wb"
                        ) as f:
                            f.write(response.content)

                        with open(f"{self.TMP_STORAGE}/m.txt", "a") as f:
                            f.write(f"file '{len(self.uri_list)}.ts'\n")

                time.sleep(4)

            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    f"{self.TMP_STORAGE}/m.txt",
                    "-c",
                    "copy",
                    f"vods/{self.CHANNEL_NAME}.mp4",
                ]
            )
            shutil.rmtree(self.TMP_STORAGE)

        except Exception as e:
            raise Exception(f"ERROR: \n{str(e)}")
