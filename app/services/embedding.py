from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Load once (VERY IMPORTANT)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generate_embedding(text: str) -> list[float]:
    """
    Converts text into a 384-dimension embedding vector.
    """
    if not text:
        return []

    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return []
