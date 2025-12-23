from app.core.database import db
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_constraints():
    """
    Runs the initial schema setup for Guru Setu.
    Applies uniqueness constraints and creates vector indexes.
    """
    session = db.get_session()
    logger.info("🚧 Starting Database Schema Setup...")

    # List of all Cypher commands to run
    queries = [
        # --- 1. Uniqueness Constraints ---
        "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
        "CREATE CONSTRAINT student_roll_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.roll_no IS UNIQUE",
        "CREATE CONSTRAINT faculty_emp_unique IF NOT EXISTS FOR (f:Faculty) REQUIRE f.employee_id IS UNIQUE",
        "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",

        # --- 2. Vector Indexes (Critical for AI Recommendations) ---
        # Note: 384 dimensions matches 'all-MiniLM-L6-v2' model
        """
        CREATE VECTOR INDEX student_bio_index IF NOT EXISTS
        FOR (s:Student) ON (s.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """,
        """
        CREATE VECTOR INDEX faculty_research_index IF NOT EXISTS
        FOR (f:Faculty) ON (f.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """
    ]

    for q in queries:
        try:
            # We strip whitespace to make logs cleaner
            clean_query = " ".join(q.split())
            session.run(q)
            logger.info(f"✅ Success: {clean_query[:50]}...")
        except Exception as e:
            logger.error(f"❌ Error running query: {e}")

    session.close()
    logger.info("🎉 Database Setup Complete!")

if __name__ == "__main__":
    # Initialize the DB connection, run setup, then close
    db.connect()
    create_constraints()
    db.close()