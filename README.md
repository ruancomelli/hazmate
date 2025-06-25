# Take-Home Test for GenAI Positions - IT Hazmat Team

![Project Hero](assets/hero.png)

This project is a take-home test for the GenAI positions at IT Hazmat.

The solution repository is available at https://github.com/ruancomelli/hazmate.

<!-- TODO: make this repo public! -->

<!-- TODO: extend this section -->

<!-- TODO: create more sections for each part of the project -->

## Devlog

### Data Collection

To build the dataset of potential hazmat items, I decided to use MercadoLibre's API.

#### Authorization

<!-- TODO: explain why I preferred the API over scraping; namely: more reliable, allows me to send queries, less complicated, less chance of getting blocked, simpler to implement, etc. -->

This was honestly the single most time-consuming part of the project. I spent a lot of time trying to figure out how to set up the redirect URL to receive the authorization code and manage the authorization code, access tokens, and refresh tokens.

I also ended up using a local server to receive the access token and refresh token.

#### Interacting with the API

To build the dataset, I will send requests to several Meli API endpoints:

- `https://api.mercadolibre.com/products/search`
- `https://api.mercadolibre.com/products/$PRODUCT_ID`
- `https://api.mercadolibre.com/sites/$SITE_ID/categories`
- `https://api.mercadolibre.com/categories/$CATEGORY_ID`
- `https://api.mercadolibre.com/categories/$CATEGORY_ID/attributes`

In order to build type-safe queries, I created a `pydantic` model for each endpoint by first sending sample queries to the API, saving the responses to a file, and then asking Cursor to create the relevant Pydantic models. See the conversation in [`cursor-chats/cursor_create_pydantic_model_for_mercad.md`](cursor-chats/cursor_create_pydantic_model_for_mercad.md).

See [`examples/queries`](examples/queries) for examples of how to use the type-safe queries.

#### Building the dataset

<!--
TODO:

### Inference

### Evaluation

### Deployment

### Updating
-->

<!-- TODO: write the following in a readable and structured way:

I am not much worried about catastrophic forgetting because:

- I am not fine-tuning models
- I am not chaining messages indefinitely (as would happen in a chatbot)
- ...?

 -->

## Feedback

<!-- TODO: give them some feedback on the challenge? -->
