"""RAG-based example store for hazmat classification using LangChain and ChromaDB."""

import logging
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing_extensions import Self

from hazmate.agent.hazmat_traits import HazmatTrait, KnownHazmatTrait, OtherHazmatTrait
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.input_datasets.input_items import InputDatasetItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExampleStore:
    """RAG-based store for human-annotated hazmat classification examples.

    This store uses LangChain + ChromaDB to embed `HazmatLabeledItem`s (ground truth examples)
    and provides similarity search to retrieve relevant examples for InputDatasetItems.
    """

    embedding_function: GoogleGenerativeAIEmbeddings
    vector_store: Chroma

    @classmethod
    def from_embedding_model_name_and_persist_directory(
        cls,
        persist_directory: str | Path | None = None,
        embedding_model_name: str = "models/gemini-embedding-exp-03-07",
    ) -> Self:
        """Create an ExampleStore instance from configuration options."""
        embedding_function = GoogleGenerativeAIEmbeddings(
            model=embedding_model_name, task_type="RETRIEVAL_DOCUMENT"
        )

        if persist_directory is not None:
            Path(persist_directory).mkdir(parents=True, exist_ok=True)

        vector_store = Chroma(
            embedding_function=embedding_function,
            persist_directory=str(persist_directory) if persist_directory else None,
        )
        return cls(embedding_function=embedding_function, vector_store=vector_store)

    def _trait_to_string(self, trait: HazmatTrait) -> str:
        """Convert a hazmat trait to its string representation."""
        return trait.trait_str

    def _labeled_item_to_document(self, labeled_item: HazmatLabeledItem) -> Document:
        """Convert a HazmatLabeledItem to a LangChain Document.

        This creates a comprehensive text representation that includes both
        the item content and the human annotation for better RAG performance.
        """
        # Create the main content for embedding
        content_parts = [
            f"Product: {labeled_item.name}",
            f"Domain: {labeled_item.domain_id}",
            f"Family: {labeled_item.family_name}",
        ]

        if labeled_item.description:
            content_parts.append(f"Description: {labeled_item.description}")

        if labeled_item.short_description:
            content_parts.append(f"Short Description: {labeled_item.short_description}")

        if labeled_item.keywords:
            content_parts.append(f"Keywords: {labeled_item.keywords}")

        # Add classification information
        content_parts.append(
            f"Classification: {'HAZMAT' if labeled_item.is_hazmat else 'NOT HAZMAT'}"
        )

        if labeled_item.traits:
            traits_text = ", ".join(
                self._trait_to_string(trait) for trait in labeled_item.traits
            )
            content_parts.append(f"Hazmat Traits: {traits_text}")

        content_parts.append(f"Reason: {labeled_item.reason}")

        page_content = "\n".join(content_parts)

        metadata = {
            "item_id": labeled_item.item_id,
            "name": labeled_item.name,
            "domain_id": labeled_item.domain_id,
            "family_name": labeled_item.family_name,
            "is_hazmat": labeled_item.is_hazmat,
            "traits": ", ".join(
                self._trait_to_string(trait) for trait in labeled_item.traits
            ),
            "reason": labeled_item.reason,
        }

        return Document(page_content=page_content, metadata=metadata)

    def _input_item_to_query(self, input_item: InputDatasetItem) -> str:
        """Convert an InputDatasetItem to a search query."""
        # Create a query that focuses on the key characteristics
        query_parts = [f"Product: {input_item.name}"]

        if input_item.description:
            query_parts.append(f"Description: {input_item.description}")

        if input_item.short_description:
            query_parts.append(f"Short Description: {input_item.short_description}")

        if input_item.keywords:
            query_parts.append(f"Keywords: {input_item.keywords}")

        return "\n".join(query_parts)

    def add(self, labeled_item: HazmatLabeledItem) -> None:
        """Add a new ground truth example to the store.

        Args:
            labeled_item: The human-annotated example to add
        """
        logger.info(f"Adding example for item {labeled_item.item_id}")

        # Convert to Document
        document = self._labeled_item_to_document(labeled_item)

        # Check if item already exists and remove it first
        existing_docs = self.vector_store.get(where={"item_id": labeled_item.item_id})

        if existing_docs["ids"]:
            logger.info(f"Updating existing example for item {labeled_item.item_id}")
            self.vector_store.delete(ids=existing_docs["ids"])

        # Add the new document
        self.vector_store.add_documents([document])

        logger.info(
            f"Successfully added/updated example for item {labeled_item.item_id}"
        )

    def add_batch(self, labeled_items: list[HazmatLabeledItem]) -> None:
        """Add multiple examples in batch for better performance.

        Args:
            labeled_items: List of human-annotated examples to add
        """
        logger.info(f"Adding batch of {len(labeled_items)} examples")

        # Convert all items to documents
        documents = [self._labeled_item_to_document(item) for item in labeled_items]

        # Remove existing documents for items being updated
        for item in labeled_items:
            existing_docs = self.vector_store.get(where={"item_id": item.item_id})
            if existing_docs["ids"]:
                self.vector_store.delete(ids=existing_docs["ids"])

        # Add all documents at once
        self.vector_store.add_documents(documents)

        logger.info(
            f"Successfully added/updated batch of {len(labeled_items)} examples"
        )

    def retrieve(
        self,
        input_item: InputDatasetItem,
        count: int = 5,
    ) -> list[HazmatLabeledItem]:
        """Retrieve the most similar examples for the given input item.

        Args:
            input_item: The item to classify
            count: Number of examples to retrieve (default from config)

        Returns:
            List of similar `HazmatLabeledItem`s, ordered by similarity
        """
        logger.debug(
            f"Retrieving {count} similar examples for item {input_item.item_id}"
        )

        # Create search query
        query = self._input_item_to_query(input_item)

        # Perform similarity search
        docs = self.vector_store.similarity_search(query, k=count)

        # Convert back to HazmatLabeledItem objects
        results = []
        for doc in docs:
            metadata = doc.metadata

            # Reconstruct traits from metadata (stored as comma-separated string)
            traits: list[HazmatTrait] = []
            traits_str = metadata.get("traits", "")
            if traits_str:
                for trait_str in traits_str.split(", "):
                    trait_str = trait_str.strip()
                    if trait_str:
                        # Try to match known traits first
                        try:
                            traits.append(KnownHazmatTrait(trait_str))
                        except ValueError:
                            # If not a known trait, treat as other trait
                            traits.append(OtherHazmatTrait(trait=trait_str))

            labeled_item = HazmatLabeledItem(
                item_id=metadata["item_id"],
                name=metadata["name"],
                domain_id=metadata["domain_id"],
                family_name=metadata["family_name"],
                description="",  # Not stored in metadata for brevity
                short_description="",  # Not stored in metadata for brevity
                keywords="",  # Not stored in metadata for brevity
                is_hazmat=metadata["is_hazmat"],
                traits=traits,
                reason=metadata["reason"],
            )
            results.append(labeled_item)

        logger.debug(f"Retrieved {len(results)} similar examples")
        return results

    def get_stats(self) -> dict[str, int]:
        """Get statistics about the example store."""
        # Get all documents
        all_docs = self.vector_store.get()
        total_count = len(all_docs["ids"])

        # Count hazmat vs non-hazmat
        hazmat_count = sum(
            metadata and metadata.get("is_hazmat", False)
            for metadata in all_docs["metadatas"]
        )
        non_hazmat_count = total_count - hazmat_count

        return {
            "total_examples": total_count,
            "hazmat_examples": hazmat_count,
            "non_hazmat_examples": non_hazmat_count,
        }

    def clear(self) -> None:
        """Clear all examples from the store. Use with caution!"""
        logger.warning("Clearing all examples from the store")

        # Get all document IDs and delete them
        all_docs = self.vector_store.get()
        if all_docs["ids"]:
            self.vector_store.delete(ids=all_docs["ids"])

        logger.info("All examples cleared")
