from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store the model (Lazy Loading)
# Initially it is None, so it takes 0 RAM at startup.
model = None

def get_model():
    """
    Loads the model only when it is first requested.
    This prevents the app from crashing during deployment on low-RAM servers.
    """
    global model
    if model is None:
        logger.info("⏳ Loading AI Model (Lazy Load)... This may take a moment.")
        try:
            # We use 'all-MiniLM-L6-v2' because it is small and efficient
            model = SentenceTransformer('all-MiniLM-L6-v2') 
            logger.info("✅ AI Model Loaded Successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load AI Model: {e}")
            raise e
    return model

def generate_embedding(text: str):
    """
    Generates an embedding for the given text.
    Safe to call even if model isn't loaded yet.
    """
    try:
        if not text or not isinstance(text, str):
            return []
            
        # Get the model (loads it NOW if it wasn't loaded before)
        ai_model = get_model()
        
        # Generate embedding
        embedding = ai_model.encode(text)
        
        # Convert numpy array to list for JSON serialization
        return embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return an empty list as fallback to prevent crash
        return []