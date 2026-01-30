from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from io import BytesIO
import requests
import spacy
from collections import Counter
import json
from datetime import datetime
import os
import time

time.sleep(1)

newsapi_key = os.getenv("NEWSAPI_KEY")
gnews_key = os.getenv("GNEWS_KEY")
mstack_key = os.getenv("MEDIASTACK_KEY")

# Load spaCy for accurate trend detection
nlp = spacy.load("en_core_web_sm")

def load_background(image_url, width=1080, height=1080):
    try:
        r = requests.get(image_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB")
        return bg.resize((width, height))
    except:
        return Image.new("RGB", (width, height), (18, 18, 18))


def fetch_master_news(query="trending news"):
    all_articles = []
    seen_urls = set()
    
    # --- API 1: NewsAPI.org ---
    try:
        url = f"https://newsapi.org/v2/top-headlines?q={query}&apiKey={newsapi_key}"
        data = requests.get(url).json()
        for art in data.get('articles', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source']['name'],
                    'image': art.get('urlToImage')   
                })
                seen_urls.add(art['url'])
    except: print("NewsAPI error")

    # --- API 2: GNews.io ---
    try:
        url = f"https://gnews.io/api/v4/top-headlines?q={query}&token={gnews_key}&lang=en"
        data = requests.get(url).json()
        for art in data.get('articles', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source']['name'],
                    'image': art.get('image')
                })
                seen_urls.add(art['url'])
    except: print("GNews error")

    # --- API 3: Mediastack ---
    try:

        url = f"http://api.mediastack.com/v1/news?access_key={mstack_key}&keywords={query}"
        data = requests.get(url).json()
        for art in data.get('data', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source'],
                    'image': art.get('image')
                })
                seen_urls.add(art['url'])
    except: print("Mediastack error")

    return all_articles

def generate_trending_report(articles):
    entity_tracker = [] # To count mentions
    topic_map = {}      # To store which articles belong to which trend

    for art in articles:
        # Combine Title and Description for context
        full_text = f"{art['title']} {art['desc']}"
        doc = nlp(full_text)
        
        # Extract Organizations, People, and Locations
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PERSON", "GPE"]:
                name = ent.text.strip()
                entity_tracker.append(name)
                
                # Link article to this entity
                if name not in topic_map:
                    topic_map[name] = []
                topic_map[name].append(art)

    # Get Top 3
    top_3 = Counter(entity_tracker).most_common(3)
    
    # Prepare JSON structure
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_articles_analyzed": len(articles),
        "trending_topics": []
    }

    for name, count in top_3:
        report["trending_topics"].append({
            "topic": name,
            "mention_count": count,
            "articles": topic_map[name][:3] # Store top 3 articles for this trend
        })

    # Save to file
    with open('trending_report.json', 'w') as f:
        json.dump(report, f, indent=4)

    return report

# EXECUTE
raw_news = fetch_master_news("technology india")
final_report = generate_trending_report(raw_news)

print("JSON saved successfully!")

def draw_wrapped_text(draw, text, font, x, y, max_width, fill, line_spacing=8):
    words = text.split()
    lines = []
    line = ""

    for word in words:
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    for ln in lines:
        draw.text((x, y), ln, fill=fill, font=font)
        y += font.getbbox(ln)[3] + line_spacing

    return y  # return where the next text should start


def generate_trending_image(report):
    if not report["trending_topics"]:
        print("No trending topics found.")
        return

    top_topic = report["trending_topics"][0]
    topic_name = top_topic["topic"]
    article = top_topic["articles"][0]

    title = article["title"]
    source = article["source"]
    desc = article["desc"]

    WIDTH, HEIGHT = 1080, 1080

    bg_img = load_background(article.get("image"))
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 140))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonts (fallback-safe)
    FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
    FONT_REG  = r"C:\Windows\Fonts\segoeui.ttf"
    title_font = ImageFont.truetype(FONT_BOLD, 40)
    meta_font  = ImageFont.truetype(FONT_REG, 25)
    desc_font = ImageFont.truetype(FONT_REG, 25)

    # Layout
    margin_x = 80
    y = 200
    max_width = WIDTH - 2 * margin_x

    y = 200

    # Header
    draw.text((margin_x, 100), "NEWS FOR YOU", fill="#aaaaaa", font=meta_font)
    draw.text((margin_x, 140), topic_name.upper(), fill="#ffffff", font=meta_font)

    # Title
    y = draw_wrapped_text(
        draw=draw,
        text=title,
        font=title_font,
        x=margin_x,
        y=y,
        max_width=max_width,
        fill="white",
        line_spacing=12
    )

    y += 20  # space between title and description

    y = draw_wrapped_text(
        draw=draw,
        text=desc,
        font=desc_font,
        x=margin_x,
        y=y,
        max_width=max_width,
        fill="#dddddd",
        line_spacing=10
    )

    # Footer
    draw.text(
        (margin_x, HEIGHT - 120),
        f"Source: {source}",
        fill="#bbbbbb",
        font=meta_font
    )

    filename = "top_trending_topic.png"
    img.save(filename, quality=95)
    print(f"Trending image generated: {filename}")

generate_trending_image(final_report)