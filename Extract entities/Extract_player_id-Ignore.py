import requests

def get_category_page_ids(category, cmtype="page"):
    """
    Fetches page IDs of pages within a given category on Wikipedia, handling pagination.

    :param category: The category to search within (replace spaces with underscores).
    :param cmtype: The type of category members to fetch (default is "page").
    :return: A list of page IDs.
    """
    S = requests.Session()

    URL = "https://en.wikipedia.org/w/api.php"

    page_ids = []

    PARAMS = {
        "action": "query",
        "cmtitle": f"Category:{category.replace(' ', '_')}",
        "cmlimit": "max",
        "list": "categorymembers",
        "format": "json",
        "cmtype": cmtype
    }

    while True:
        R = S.get(url=URL, params=PARAMS)
        DATA = R.json()

        pages = DATA["query"]["categorymembers"]
        for page in pages:
            page_ids.append(page["pageid"])

        if 'continue' in DATA:
            PARAMS['cmcontinue'] = DATA['continue']['cmcontinue']
        else:
            break

    return page_ids

# Example usage
categories = ['La Liga players', 'Serie A players', 'Premier League players', 'Ligue 1 players', 'Bundesliga players']
clubs_categories = ['La Liga clubs', 'Serie A clubs', 'Premier League clubs', 'Ligue 1 clubs', 'Bundesliga clubs']

for category in clubs_categories:
    page_ids = get_category_page_ids(category)  # Adjust limit as needed
    print(f"Fetched {len(page_ids)} page IDs for {category}")
    with open(f"{category.replace(' ', '_')}.txt", "w") as f:
        for page_id in page_ids:
            f.write(f"{page_id}\n")

for category in categories:
    page_ids = get_category_page_ids(category)  # Adjust limit as needed
    print(f"Fetched {len(page_ids)} page IDs for {category}")
    with open(f"{category.replace(' ', '_')}.txt", "w") as f:
        for page_id in page_ids:
            f.write(f"{page_id}\n")
