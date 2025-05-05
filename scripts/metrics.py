from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

def push_scrape_metrics(record_count):
    registry = CollectorRegistry()
    g = Gauge('imdb_scraped_records_total', 'Number of IMDb records scraped', registry=registry)
    g.set(record_count)
    push_to_gateway('pushgateway:9091', job='imdb_scraper', registry=registry)
