import requests
import spacy
from collections import Counter
import json
from datetime import datetime

# Load spaCy for accurate trend detection
nlp = spacy.load("en_core_web_sm")

def fetch_master_news(query="trending+news"):
    all_articles = []
    seen_urls = set()
    
    # --- API 1: NewsAPI.org ---
    try:
        url = f"https://newsapi.org/v2/everything?q={query}&apiKey=e657de4f04dc403ab6908849f710704c"
        data = requests.get(url).json()
        for art in data.get('articles', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source']['name']
                })
                seen_urls.add(art['url'])
    except: print("NewsAPI error")

    # --- API 2: GNews.io ---
    try:
        gnews_key = "0b74370c656a6eb17e5d728650b8ef50"
        url = f"https://gnews.io/api/v4/search?q={query}&token={gnews_key}&lang=en"
        data = requests.get(url).json()
        for art in data.get('articles', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source']['name']
                })
                seen_urls.add(art['url'])
    except: print("GNews error")

    # --- API 3: Mediastack ---
    try:
        mstack_key = "cccd8a63afbf8bcabd7e268190592b76"
        url = f"http://api.mediastack.com/v1/news?access_key={mstack_key}&keywords={query}"
        data = requests.get(url).json()
        for art in data.get('data', []):
            if art['url'] not in seen_urls:
                all_articles.append({
                    'title': art['title'],
                    'url': art['url'],
                    'desc': art.get('description', ''),
                    'source': art['source']
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
raw_news = fetch_master_news("ai engineering")
final_report = generate_trending_report(raw_news)
print("JSON saved successfully!")