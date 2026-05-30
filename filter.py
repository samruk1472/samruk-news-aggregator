def match_company(text: str, companies: list) -> str:
    text_lower = text.lower()
    for company in companies:
        for kw in company["keywords"]:
            if kw.lower() in text_lower:
                return company["name"]
    return None


def filter_articles(articles: list[dict], companies: list[dict]) -> list[dict]:
    result = []
    for article in articles:
        search_text = f"{article.get('title', '')} {article.get('raw_text', '')}"
        company = match_company(search_text, companies)
        if company:
            article["company"] = company
            result.append(article)
    return result
