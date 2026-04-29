import requests
from bs4 import BeautifulSoup

def scrape_headlines(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    headlines = []
    for headline in soup.find_all('h2', class_='headline-class'):  # Adjust the selector as needed
        headlines.append(headline.text.strip())
    return headlines

if __name__ == '__main__':
    url = 'https://example-news-website.com'  # Replace with the actual news website URL
    print(scrape_headlines(url))