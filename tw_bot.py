import tweepy
from dotenv import load_dotenv
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import requests
from bs4 import BeautifulSoup
import time
import json
import datetime

load_dotenv()

# Load credentials from .env file
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# File to store seen articles
SEEN_ARTICLES_FILE = "seen_articles.json"
CHECK_INTERVAL = 600  # Check every 10 minutes (adjust as needed)


def load_seen_articles():
    """Load previously seen articles from file"""
    try:
        if os.path.exists(SEEN_ARTICLES_FILE):
            with open(SEEN_ARTICLES_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading seen articles: {e}")
        return {}


def save_seen_articles(seen_articles):
    """Save seen articles to file"""
    try:
        with open(SEEN_ARTICLES_FILE, "w") as f:
            json.dump(seen_articles, f)
    except Exception as e:
        print(f"Error saving seen articles: {e}")


def authenticate():
    """Set up and return authenticated client"""


def post_tweet(text):

    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,  # Fixed: was using ACCESS_SECRET incorrectly
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
    )

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        print(f"Tweet posted successfully! Tweet ID: {tweet_id}")
        return tweet_id
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return None


def get_fox_news_articles():
    """Scrape latest news from Fox News website and return list of articles with URLs"""
    url = "https://www.foxnews.com/"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Get top articles with links
        articles = []
        article_elements = soup.select(".article, .story, .article-list article")[:10]

        for article in article_elements:
            title_element = article.select_one("h2, .title, .headline, a.title")
            link_element = article.select_one("a")

            if title_element and link_element and link_element.get("href"):
                title = title_element.get_text().strip()
                link = link_element.get("href")

                # Make sure link is absolute URL
                if not link.startswith(("http://", "https://")):
                    if link.startswith("/"):
                        link = f"https://www.foxnews.com{link}"
                    else:
                        link = f"https://www.foxnews.com/{link}"

                articles.append({"title": title, "url": link})

        return articles

    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def get_article_content(url):
    """Fetch and extract content from an article URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Try to find the article body - this will vary depending on the website structure
        article_body = soup.select_one(
            ".article-body, .story-body, .article-content, main article"
        )

        if not article_body:
            # If can't find specific article body, get all paragraphs
            paragraphs = soup.select("p")
            content = " ".join(
                [
                    p.get_text().strip()
                    for p in paragraphs
                    if len(p.get_text().strip()) > 100
                ]
            )
        else:
            # Get all paragraphs in the article body
            paragraphs = article_body.select("p")
            content = " ".join([p.get_text().strip() for p in paragraphs])

        # Clean up the content
        content = content.replace("\n", " ").replace("\t", " ")
        while "  " in content:  # Remove extra spaces
            content = content.replace("  ", " ")

        return content[:2000]  # Limit length to avoid overwhelming the model

    except Exception as e:
        print(f"Error fetching article content: {e}")
        return ""


def generate_text(prompt, content):
    """Generate text using the local model from Ollama"""
    ollama_client = ChatOllama(model="smollm2", base_url="http://127.0.0.1:11434/")
    messages = [
        SystemMessage(
            content="You are an X bot. Use the voice of Sean Hannity to write a Post. The post is a funny rant. Keep it short, satirical, funny, and sweet!. One sentence summary of the article. Do not include any links, hashtags, or mentions (@someone). 100 character limit."
        ),
        HumanMessage(content=f"{prompt}\n\nArticle content: {content}"),
    ]
    response = ollama_client.invoke(messages)
    # Remove any quotation marks that might still be in the response
    cleaned_text = response.content.replace('"', "").replace("'", "")
    return cleaned_text


def monitor_fox_news():
    """Continuously monitor Fox News for new articles, checking one at a time"""
    seen_articles = load_seen_articles()

    print(f"Starting Fox News monitor at {datetime.datetime.now()}")
    print(f"Currently tracking {len(seen_articles)} articles")

    while True:
        try:
            articles = get_fox_news_articles()
            new_article = None

            # Find the first new article we haven't seen before
            for article in articles:
                if article["url"] not in seen_articles:
                    new_article = article
                    # Mark it as seen with the current timestamp
                    seen_articles[article["url"]] = {
                        "title": article["title"],
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                    break  # Only take the first new article

            # If we have a new article, fetch content, summarize and post tweet
            if new_article:
                print(f"Found new article at {datetime.datetime.now()}")
                print(f"Title: {new_article['title']}")
                print(f"URL: {new_article['url']}")

                # Fetch the full article content
                article_content = get_article_content(new_article["url"])

                if article_content:
                    prompt_text = f"Summarize this article and create a tweet about it. Article title: {new_article['title']}"
                    tweet_text = generate_text(prompt_text, article_content).strip()

                    print(f"Generated tweet: {tweet_text}")
                    formatted_tweet = (
                        "👀 BREAKING: \n\n" + tweet_text + "\n\nWhat do you think?"
                    )

                    # Uncomment to actually post the tweet
                    post_tweet(formatted_tweet)

                # Save updated seen articles
                save_seen_articles(seen_articles)

            # Clean up old articles (older than 24 hours)
            current_time = datetime.datetime.now()
            for url, data in list(seen_articles.items()):
                timestamp = datetime.datetime.fromisoformat(data["timestamp"])
                if (current_time - timestamp).total_seconds() > 86400:  # 24 hours
                    del seen_articles[url]

            # Save after cleanup
            save_seen_articles(seen_articles)

            # Wait before checking again
            print(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(60)  # Wait a minute before retrying after an error


if __name__ == "__main__":
    # Uncomment the line below to run as a monitor
    # monitor_fox_news()

    # Or run once for testing
    articles = get_fox_news_articles()
    if articles:
        article = articles[0]
        print(f"Testing with article: {article['title']}")
        article_content = get_article_content(article["url"])
        prompt_text = f"Summarize this article and create a tweet about it. Article title: {article['title']}"
        tweet_text = generate_text(prompt_text, article_content)

        formatted_tweet = (
            "👀 BREAKING: \n\n" + tweet_text.strip() + "\n\n What do you think?"
        )
        # print(formatted_tweet)
        post_tweet(formatted_tweet)
