import re


def _make_pattern(keyword: str) -> re.Pattern:
    escaped = re.escape(keyword)
    # For keywords >= 6 chars use word boundary; short ones require exact boundary
    return re.compile(r'(?<!\w)' + escaped + r'(?!\w)', re.IGNORECASE)


def match_company(text: str, companies: list) -> str:
    for company in companies:
        for kw in company["keywords"]:
            if _make_pattern(kw).search(text):
                return company["name"]
    return None


def filter_articles(articles: list, companies: list) -> list:
    result = []
    for article in articles:
        search_text = f"{article.get('title', '')} {article.get('raw_text', '')}"
        company = match_company(search_text, companies)
        if company:
            article["company"] = company
            result.append(article)
    return result
