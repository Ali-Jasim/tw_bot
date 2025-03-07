import tweepy
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Twitter API credentials (replace with your own or use environment variables)

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

print(API_KEY)


def post_test_tweet():
    # Authenticate with Twitter
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
        wait_on_rate_limit=True,
    )

    # Create a test tweet with timestamp
    tweet_text = f"This is a test tweet posted via Tweepy at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        # Post the tweet
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        print(f"Tweet posted successfully! Tweet ID: {tweet_id}")
        return tweet_id
    except tweepy.TooManyRequests as e:
        # Handle rate limiting
        print(f"Rate limit exceeded: {e}")

        # Check for rate limit reset time in response headers
        if hasattr(e, "response") and "x-rate-limit-reset" in e.response.headers:
            reset_time = int(e.response.headers["x-rate-limit-reset"])
            current_time = int(time.time())
            sleep_time = reset_time - current_time + 5  # Add 5 seconds buffer

            if sleep_time > 0:
                print(f"Rate limit will reset in {sleep_time} seconds. Waiting...")
                time.sleep(sleep_time)
                # Try again after waiting
                print("Retrying tweet...")
                return post_test_tweet()  # Recursive retry

        print("Couldn't determine rate limit reset time. Waiting 15 minutes...")
        time.sleep(15 * 60)  # Wait 15 minutes as a fallback
        return post_test_tweet()  # Recursive retry
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return None


if __name__ == "__main__":
    post_test_tweet()
