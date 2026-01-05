from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = None

def get_model():
    global model
    if model is None:
        # ✅ SWAPPING TO LIGHTWEIGHT MODEL
        # paraphrase-albert-small-v2 is 90% smaller than MiniLM
        logger.info("⏳ Loading Lightweight AI Model: paraphrase-albert-small-v2")
        try:
            model = SentenceTransformer('sentence-transformers/paraphrase-albert-small-v2') 
            logger.info("✅ Lightweight Model Loaded Successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load AI Model: {e}")
            raise e
    return model

def generate_embedding(text: str):
    try:
        if not text or not isinstance(text, str):
            return []
            
        ai_model = get_model()
        embedding = ai_model.encode(text)
        return embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []