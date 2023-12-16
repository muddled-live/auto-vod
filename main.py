import os
from autovod import twitch
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":
    t = twitch.TwitchBase(os.getenv("CHANNEL_NAME"))
    t.start(6)
