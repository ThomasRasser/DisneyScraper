# Data aggregation and clean-up for ASE project

**Project:**
Optimized routing through amusement park

This should have been a simple script to gather the data
from APIs or via simple web-scraping, however it escalated quite quickly.

After a successful creation of all data files as json,
they should be added into the Postgres Database

## Disney Scraper
Disneyland Paris does not offer an API to its data, therefore we have to scrape their website.
The hot-spots we need are the following:
- [Entertainment](https://www.disneylandparis.com/en-gb/entertainment/)
- [Dining](https://www.disneylandparis.com/en-gb/dining/)
- [Attractions](https://www.disneylandparis.com/en-gb/attractions/)

These attractions also offer additional information on their detailed page,
but the html is not consistent, and would therefore need quite work-intensive parsing,
but contrary to common belief, I do have a personal life, so I threw this idea out the window.

Note:
I might try to straight up download the whole html and let it run through a LLM,
to gather the data for each individual ride - but lets focus on the basics for now.

## OpenStreetMap (OSM)
OpenStreetMap has an API, at lets me download all [Disneyland Paris](https://www.openstreetmap.org/way/205732748) related data at once.
The nodes are either of type way, or of type node and have additional tags.

Unfortunately the attractions and restaurants do not have a one-to-one mapping,
therefore some manual labour is needed to find the correct node for each attraction.


## Nodes
Since we want to solve the TSP we don't need every node, but only those which lead to a junction.
All intermediate nodes can be compressed by adding the distance to the TSP neighbor.

## Queue
Queue

## Weather





