import requests
from bs4 import BeautifulSoup

def fetch_top_headlines(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    headlines = []
    # BBC uses h3 tags broadly
    for h3 in soup.find_all("h3")[:10]:
        text = h3.get_text(strip=True)
        if len(text) > 20:
            headlines.append(text)
        if len(headlines) >= 5:
            break
    return headlines

if __name__ == "__main__":
    url = "https://www.bbc.com/news"
    headlines = fetch_top_headlines(url)
    if headlines:
        print("BBC Top Headlines:")
        for i, h in enumerate(headlines, 1):
            print(f"{i}. {h}")
    else:
        print("No headlines found")
