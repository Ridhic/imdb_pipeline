import requests
from lxml import html
import json

def scrape_imdb_top_250():
    headers = {
        'authority': 'www.imdb.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    }
    response = requests.get('https://www.imdb.com/chart/top/', headers=headers)
    tree = html.fromstring(response.content)

    movies = []
    movie_json = tree.xpath('//script[@id="__NEXT_DATA__"]//text()')
    movie_data = json.loads(movie_json[0]).get('props').get('pageProps').get('pageData').get('chartTitles').get('edges')

    for row in movie_data:
        title = row.get('node').get('titleText').get('text')
        image = row.get('node').get('primaryImage').get('url')
        year = row.get('node').get('releaseYear').get('year')
        rating = row.get('node').get('ratingsSummary').get('aggregateRating')
        vote_count = row.get('node').get('ratingsSummary').get('voteCount')
        plot = row.get('node').get('plot').get('plotText').get('plainText')
        movies.append({
            "title": title,
            "image": image,
            "year": int(year),
            "rating": float(rating),
            "vote_count": int(vote_count),
            "plot": plot
        })

    return movies
