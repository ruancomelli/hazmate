"""RAG-based example store for hazmat classification using human-annotated examples."""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

import psycopg
import pydantic_core
from openai import AsyncOpenAI
from typing_extensions import Self

from hazmate.agent.hazmat_traits import HazmatTrait, KnownHazmatTrait, OtherHazmatTrait
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.input_datasets.input_items import InputDatasetItem

logger = logging.getLogger(__name__)


@dataclass
class ExampleStoreConfig:
    """Configuration for the ExampleStore."""

    # Database connection
    database_url: str = (
        "postgresql://postgres:postgres@localhost:54320/hazmate_examples"
    )

    # Embedding settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Search settings
    default_retrieve_count: int = 5
    max_retrieve_count: int = 20


class ExampleStore:
    """RAG-based store for human-annotated hazmat classification examples.

    This store embeds `HazmatLabeledItem`s (ground truth examples) and provides
    similarity search to retrieve relevant examples for InputDatasetItems.
    """

    def __init__(
        self,
        config: ExampleStoreConfig | None = None,
        openai_client: AsyncOpenAI | None = None,
    ):
        self.config = config or ExampleStoreConfig()
        self.openai_client = openai_client or AsyncOpenAI()

    @classmethod
    async def create(
        cls,
        config: ExampleStoreConfig | None = None,
        openai_client: AsyncOpenAI | None = None,
        initialize_db: bool = True,
    ) -> Self:
        """Create an ExampleStore instance and optionally initialize the database."""
        store = cls(config, openai_client)

        if initialize_db:
            await store._initialize_database()

        return store

    async def _initialize_database(self) -> None:
        """Initialize the database schema."""
        logger.info("Initializing ExampleStore database")

        # Parse database URL to get server and database name
        # Format: postgresql://user:pass@host:port/dbname
        parts = self.config.database_url.split("/")
        database_name = parts[-1]
        server_url = "/".join(parts[:-1])

        # Create database if it doesn't exist
        async with await psycopg.AsyncConnection.connect(server_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (database_name,),  # type: ignore
                )
                db_exists = await cur.fetchone()
                if not db_exists:
                    # Note: CREATE DATABASE cannot be run in a transaction
                    await conn.rollback()  # End any existing transaction
                    await cur.execute(f"CREATE DATABASE {database_name}")  # type: ignore
                    logger.info(f"Created database: {database_name}")

        # Initialize schema
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(self._get_schema_sql())
            logger.info("Database schema initialized")

    def _get_schema_sql(self) -> str:
        """Get the SQL schema for the examples table."""
        return f"""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS hazmat_examples (
            id SERIAL PRIMARY KEY,
            item_id TEXT NOT NULL UNIQUE,
            is_hazmat BOOLEAN NOT NULL,
            traits JSONB NOT NULL,
            reason TEXT NOT NULL,
            embedding_content TEXT NOT NULL,
            embedding VECTOR({self.config.embedding_dimensions}) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_hazmat_examples_embedding
        ON hazmat_examples USING hnsw (embedding vector_l2_ops);

        CREATE INDEX IF NOT EXISTS idx_hazmat_examples_item_id
        ON hazmat_examples (item_id);

        CREATE INDEX IF NOT EXISTS idx_hazmat_examples_is_hazmat
        ON hazmat_examples (is_hazmat);
        """

    @asynccontextmanager
    async def _get_connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get a database connection."""
        async with await psycopg.AsyncConnection.connect(
            self.config.database_url
        ) as conn:
            yield conn

    async def _create_embedding(self, text: str) -> list[float]:
        """Create an embedding for the given text."""
        logger.debug(f"Creating embedding for text of length {len(text)}")

        response = await self.openai_client.embeddings.create(
            input=text,
            model=self.config.embedding_model,
        )

        if len(response.data) != 1:
            raise ValueError(f"Expected 1 embedding, got {len(response.data)}")

        return response.data[0].embedding

    def _trait_to_string(self, trait: HazmatTrait) -> str:
        """Convert a hazmat trait to its string representation."""
        if isinstance(trait, KnownHazmatTrait):
            return trait.value
        elif isinstance(trait, OtherHazmatTrait):
            return trait.trait
        else:
            return str(trait)

    def _trait_to_dict(self, trait: HazmatTrait) -> dict:
        """Convert a hazmat trait to dictionary for JSON storage."""
        if isinstance(trait, KnownHazmatTrait):
            return {"type": "known", "value": trait.value}
        elif isinstance(trait, OtherHazmatTrait):
            return {"type": "other", "trait": trait.trait}
        else:
            return {"type": "unknown", "value": str(trait)}

    def _output_item_to_embedding_content(self, output_item: HazmatLabeledItem) -> str:
        """Convert an HazmatLabeledItem to text content for embedding.

        This creates a comprehensive text representation that includes both
        the item content and the human annotation, which helps the model
        understand the reasoning patterns.
        """
        content_parts = [
            f"Item ID: {output_item.item_id}",
            f"Classification: {'HAZMAT' if output_item.is_hazmat else 'NOT HAZMAT'}",
        ]

        if output_item.traits:
            traits_text = ", ".join(
                self._trait_to_string(trait) for trait in output_item.traits
            )
            content_parts.append(f"Hazmat Traits: {traits_text}")

        content_parts.append(f"Reason: {output_item.reason}")

        return "\n".join(content_parts)

    def _input_item_to_embedding_content(self, input_item: InputDatasetItem) -> str:
        """Convert an InputDatasetItem to text content for embedding."""
        # Use the existing XML representation method
        return input_item.get_all_text_content_as_xml(
            include_item_id=False,  # Don't include item_id in embedding
            include_attributes=True,
        )

    async def add(self, output_item: HazmatLabeledItem) -> None:
        """Add a new ground truth example to the store.

        Args:
            output_item: The human-annotated example to add
        """
        logger.info(f"Adding example for item {output_item.item_id}")

        # Create embedding content
        embedding_content = self._output_item_to_embedding_content(output_item)

        # Generate embedding
        embedding = await self._create_embedding(embedding_content)
        embedding_json = pydantic_core.to_json(embedding).decode()

        # Store in database
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                # Convert traits to JSON
                traits_json = pydantic_core.to_json(
                    [self._trait_to_dict(trait) for trait in output_item.traits]
                ).decode()

                await cur.execute(
                    """
                    INSERT INTO hazmat_examples (item_id, is_hazmat, traits, reason, embedding_content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (item_id)
                    DO UPDATE SET
                        is_hazmat = EXCLUDED.is_hazmat,
                        traits = EXCLUDED.traits,
                        reason = EXCLUDED.reason,
                        embedding_content = EXCLUDED.embedding_content,
                        embedding = EXCLUDED.embedding,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (
                        output_item.item_id,
                        output_item.is_hazmat,
                        traits_json,
                        output_item.reason,
                        embedding_content,
                        embedding_json,
                    ),
                )

        logger.info(
            f"Successfully added/updated example for item {output_item.item_id}"
        )

    async def add_batch(self, output_items: list[HazmatLabeledItem]) -> None:
        """Add multiple examples in batch for better performance.

        Args:
            output_items: List of human-annotated examples to add
        """
        logger.info(f"Adding batch of {len(output_items)} examples")

        # Create embeddings for all items
        embedding_tasks = []
        for item in output_items:
            content = self._output_item_to_embedding_content(item)
            embedding_tasks.append(self._create_embedding(content))

        embeddings = await asyncio.gather(*embedding_tasks)

        # Insert all items
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                for output_item, embedding in zip(output_items, embeddings):
                    embedding_content = self._output_item_to_embedding_content(
                        output_item
                    )
                    embedding_json = pydantic_core.to_json(embedding).decode()
                    traits_json = pydantic_core.to_json(
                        [self._trait_to_dict(trait) for trait in output_item.traits]
                    ).decode()

                    await cur.execute(
                        """
                        INSERT INTO hazmat_examples (item_id, is_hazmat, traits, reason, embedding_content, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (item_id)
                        DO UPDATE SET
                            is_hazmat = EXCLUDED.is_hazmat,
                            traits = EXCLUDED.traits,
                            reason = EXCLUDED.reason,
                            embedding_content = EXCLUDED.embedding_content,
                            embedding = EXCLUDED.embedding,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        (
                            output_item.item_id,
                            output_item.is_hazmat,
                            traits_json,
                            output_item.reason,
                            embedding_content,
                            embedding_json,
                        ),
                    )

        logger.info(f"Successfully added/updated batch of {len(output_items)} examples")

    async def retrieve(
        self,
        input_item: InputDatasetItem,
        count: int | None = None,
    ) -> list[HazmatLabeledItem]:
        """Retrieve the most similar examples for the given input item.

        Args:
            input_item: The item to classify
            count: Number of examples to retrieve (default from config)

        Returns:
            List of similar `HazmatLabeledItem`s, ordered by similarity
        """
        if count is None:
            count = self.config.default_retrieve_count

        count = min(count, self.config.max_retrieve_count)

        logger.debug(
            f"Retrieving {count} similar examples for item {input_item.item_id}"
        )

        # Create embedding for input item
        input_content = self._input_item_to_embedding_content(input_item)
        input_embedding = await self._create_embedding(input_content)
        input_embedding_json = pydantic_core.to_json(input_embedding).decode()

        # Query for similar examples
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT item_id, is_hazmat, traits, reason, embedding <-> %s AS distance
                    FROM hazmat_examples
                    ORDER BY embedding <-> %s
                    LIMIT %s
                    """,
                    (input_embedding_json, input_embedding_json, count),
                )
                rows = await cur.fetchall()

        # Convert results back to `HazmatLabeledItem`s
        results = []
        for row in rows:
            # Parse traits from JSON
            traits_data = pydantic_core.from_json(row[2])  # traits column
            traits: list[HazmatTrait] = []
            for trait_data in traits_data:
                if trait_data.get("type") == "known":
                    traits.append(KnownHazmatTrait(trait_data["value"]))
                elif trait_data.get("type") == "other":
                    traits.append(OtherHazmatTrait(trait=trait_data["trait"]))
                else:
                    # Fallback for unknown format
                    traits.append(OtherHazmatTrait(trait=str(trait_data)))

            output_item = HazmatLabeledItem(
                item_id=row[0],  # item_id
                is_hazmat=row[1],  # is_hazmat
                traits=traits,
                reason=row[3],  # reason
            )
            results.append(output_item)

        logger.debug(f"Retrieved {len(results)} similar examples")
        return results

    async def get_stats(self) -> dict[str, int]:
        """Get statistics about the example store."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM hazmat_examples")
                total_result = await cur.fetchone()
                total_count = total_result[0] if total_result else 0

                await cur.execute(
                    "SELECT COUNT(*) FROM hazmat_examples WHERE is_hazmat = true"
                )
                hazmat_result = await cur.fetchone()
                hazmat_count = hazmat_result[0] if hazmat_result else 0

                non_hazmat_count = total_count - hazmat_count

        return {
            "total_examples": total_count,
            "hazmat_examples": hazmat_count,
            "non_hazmat_examples": non_hazmat_count,
        }

    async def clear(self) -> None:
        """Clear all examples from the store. Use with caution!"""
        logger.warning("Clearing all examples from the store")
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM hazmat_examples")
        logger.info("All examples cleared")
