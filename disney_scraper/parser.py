from bs4 import BeautifulSoup


def parse_disneyland_attraction_lists(html: str) -> list[dict]:
    """
    Parses the HTML content and extracts attraction data.
    :param html: The HTML content as a string.
    :return: A list of dictionaries containing attraction data.
    """
    print("Parsing HTML content...")

    soup = BeautifulSoup(html, "html.parser")

    # Attraction lists have the class `card-list`
    # Usually there is one list for open and one for closed attractions
    attraction_lists = soup.find_all("div", class_="card-list")
    if not attraction_lists:
        print("No attraction lists found.")
        return []

    # Example attraction item
    """
    <div class="m-button-card m-card" title="Learn more about &quot;it's a small world&quot;">
        <article>
            <ahref="https://www.disneylandparis.com/en-gb/attractions/disneyland-park/its-a-small-world-app/" class="card-content">
                <div class="card-image">
                    <span class=" lazy-load-image-background  lazy-load-image-loaded"
                        style="color: transparent; display: inline-block; height: auto; width: 100%;">
                            <img height="90px" alt width="100%"
                            src="https://media.disneylandparis.com/d4th/en-gb/images/n016335_2_2028jan27_world_it-a-small-world-attraction_16-9_tcm752-256994.jpg?w=180">
                    </span>
                </div>
                <div class="card-text">
                    <div class="card-description full-description">
                        <h2>
                            "it's a small world"
                        </h2>
                        <div class="activity-info">
                            Height: Any Height
                        </div>
                        <div class="activity-info">
                            Fun For Little Ones, Disney Premier Access, Disney Premier Access One, Disney Premier Access Ultimate
                        </div>
                        <div class="activity-info">
                            Disneyland Park, Fantasyland
                        </div>
                    </div>
                </div>
            </a>
        </article>
    </div>
    """

    # Extract and clean-up the attraction data
    attractions = []
    for attraction_list in attraction_lists:
        for attraction in attraction_list.find_all("div", class_="m-button-card m-card"):
            try:
                new_attraction = {}

                new_attraction["title"] = attraction.get("title", "")
                if new_attraction["title"]:
                    new_attraction["title"] = new_attraction["title"].replace("Learn more about ", "").strip()

                a_tag = attraction.find("a")
                new_attraction["link"] = a_tag.get("href", "") if a_tag else ""

                img_tag = attraction.find("img")
                new_attraction["image"] = img_tag.get("src", "") if img_tag else ""

                h2_tag = attraction.find("h2")
                new_attraction["description"] = h2_tag.text.strip() if h2_tag and h2_tag.text else ""

                info_tags = attraction.find_all("div", class_="activity-info")
                new_attraction["min_height_cm"] = info_tags[0].text.strip() if len(info_tags) > 0 else ""
                if new_attraction["min_height_cm"]:
                    new_attraction["min_height_cm"] = new_attraction["min_height_cm"].replace("Height: ", "").strip()
                    if new_attraction["min_height_cm"] == "Any Height":
                        new_attraction["min_height_cm"] = "0"
                    if "cm" in new_attraction["min_height_cm"]:
                        new_attraction["min_height_cm"] = new_attraction["min_height_cm"].replace("cm", "").strip()
                    if "m" in new_attraction["min_height_cm"]:
                        new_attraction["min_height_cm"] = str(
                            float(new_attraction["min_height_cm"].replace("m", "").strip()) * 100
                        )

                new_attraction["keywords"] = info_tags[1].text.strip() if len(info_tags) > 1 else ""
                new_attraction["location"] = info_tags[2].text.strip() if len(info_tags) > 2 else ""

                attractions.append(new_attraction)
            except (AttributeError, IndexError) as e:
                print(f"Error parsing attraction data: {e}")

    print(f"Parsed {len(attractions)} attractions.")
    return attractions


def parse_disneyland_dining_lists(html: str) -> list[dict]:
    """
    Parses the HTML content and extracts dining data.
    :param html: The HTML content as a string.
    :return: A list of dictionaries containing dining data.
    """

    print("Parsing HTML content...")

    soup = BeautifulSoup(html, "html.parser")

    # dining lists have the class `card-list`
    # Usually there is one list for open and one for closed dinings
    dining_lists = soup.find_all("div", class_="card-list")
    if not dining_lists:
        print("No dining lists found.")
        return []

    # Extract and clean-up the dining data
    dinings = []
    for dining_list in dining_lists:
        for dining in dining_list.find_all("div", class_="m-button-card m-card"):
            try:
                new_dining = {}

                new_dining["title"] = dining.get("title", "")
                if new_dining["title"]:
                    new_dining["title"] = new_dining["title"].replace("Learn more about ", "").strip()

                a_tag = dining.find("a")
                new_dining["link"] = a_tag.get("href", "") if a_tag else ""

                img_tag = dining.find("img")
                new_dining["image"] = img_tag.get("src", "") if img_tag else ""

                info_tags = dining.find_all("div", class_="activity-info")
                new_dining["keywords"] = info_tags[0].text.strip() if len(info_tags) > 0 else ""

                type_description = info_tags[1].text.strip() if len(info_tags) > 1 else ""
                type_description = type_description.split(",")
                new_dining["price"] = type_description[0].strip() if type_description else ""
                if len(type_description) > 1:
                    new_dining["nationality"] = type_description[1].strip()

                new_dining["location"] = info_tags[2].text.strip() if len(info_tags) > 2 else ""

                dinings.append(new_dining)
            except (AttributeError, IndexError) as e:
                print(f"Error parsing dining data: {e}")

    print(f"Parsed {len(dinings)} dinings.")
    return dinings


def parse_disneyland_attraction_details(html: str) -> dict:
    """
    Parses the HTML content and extracts detailed attraction data.
    :param html: The HTML content as a string.
    :return: A dictionary containing detailed attraction data.
    """

    # Title class: sc-ac2d3348-6
    # Description class: sc-ac2d3348-7
    # Keyword Class: sc-38eb0625-3
    # Services and Accessibility Description class: sc-279bf40e-2
    # Services and Accessibility List class: sc-12a24b76-0

    soup = BeautifulSoup(html, "html.parser")

    attraction = {}

    # Title
    title_tag = soup.find("h1", class_="sc-ac2d3348-6")
    attraction["title"] = title_tag.text.strip() if title_tag and title_tag.text else ""
    # print(f"Title: {attraction['title']}")

    # Description
    description_tag = soup.find("div", class_="sc-ac2d3348-7")
    attraction["description"] = description_tag.text.strip() if description_tag and description_tag.text else ""
    # print(f"Description: {attraction['description']}")

    # Keywords
    keywords_tags = soup.find_all("p", class_="sc-38eb0625-3")
    attraction["keywords"] = [tag.text.strip() for tag in keywords_tags if tag and tag.text]  # type: ignore
    # print(f"Keywords: {attraction['keywords']}")

    # Services description
    services_description = soup.find("div", class_="sc-279bf40e-2")
    attraction["services_description"] = (
        services_description.text.strip() if services_description and services_description.text else ""
    )
    # print(f"Services description: {attraction['services_description']}")

    # Services list
    services_list_tags = soup.find_all("div", class_="sc-12a24b76-0")
    attraction["services_list"] = [
        tag.find("p").text.strip() for tag in services_list_tags if tag and tag.find("p") and tag.find("p").text
    ]  # type: ignore
    # print(f"Services list: {attraction['services_list']}")

    return attraction
