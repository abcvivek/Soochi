from trafilatura import Crawler

def crawl_links(links):
    crawler = Crawler()
    articles = []
    for link in links:
        article = crawler.crawl(link)
        articles.append(article)
    return articles
