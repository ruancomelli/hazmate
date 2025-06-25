# Take-Home Test for GenAI Positions - IT Hazmat Team

![Project Hero](assets/hero.png)

## Overview

## Feedback

## Devlog

### Data Collection

To build the dataset of potential hazmat items, I decided to use MercadoLibre's API.

#### Authorization

<!-- TODO: explain why I preferred the API over scraping; namely: more reliable, allows me to send queries, less complicated, less chance of getting blocked, simpler to implement, etc. -->

This was honestly the single most time-consuming part of the project. I spent a lot of time trying to figure out how to set up the redirect URL to receive the authorization code and manage the authorization code, access tokens, and refresh tokens.

I also ended up using a local server to receive the access token and refresh token.

#### Interacting with the API

To build the dataset, I will send requests to two Meli API endpoints:

- `https://api.mercadolibre.com/products/search`
- `https://api.mercadolibre.com/products/$PRODUCT_ID`

In order to build type-safe queries, I created a `pydantic` model for each endpoint by first sending sample queries to the API, saving the responses to a file, and then asking Cursor to create the relevant Pydantic models. See the conversation in [`cursor-chats/cursor_create_pydantic_model_for_mercad.md`](cursor-chats/cursor_create_pydantic_model_for_mercad.md).

See [`examples/search_query.py`](examples/search_query.py) and [`examples/search_query_paginated.py`](examples/search_query_paginated.py) for examples of how to use the type-safe search query.

#### Building the dataset

<!-- TODO -->