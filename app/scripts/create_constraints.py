from app.core.database import db
import logging
import sys
from neo4j.exceptions import Neo4jError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_constraints():
    """
    Runs the initial schema setup for Guru Setu.
    Applies uniqueness constraints and creates vector indexes.
    """
    session = None
    logger.info("🚧 Starting Database Schema Setup...")

    queries = [
        # --- 1. Uniqueness Constraints ---
        "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
        "CREATE CONSTRAINT student_roll_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.roll_no IS UNIQUE",
        "CREATE CONSTRAINT faculty_emp_unique IF NOT EXISTS FOR (f:Faculty) REQUIRE f.employee_id IS UNIQUE",
        "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",

        # --- 2. Vector Indexes ---
        """
        CREATE VECTOR INDEX student_bio_index IF NOT EXISTS
        FOR (s:Student) ON (s.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
            }
        }
        """,
        """
        CREATE VECTOR INDEX faculty_research_index IF NOT EXISTS
        FOR (f:Faculty) ON (f.embedding)
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
            }
        }
        """
    ]

    try:
        session = db.get_session()

        for q in queries:
            clean_query = " ".join(q.split())
            try:
                session.run(q)
                logger.info(f"✅ Success: {clean_query[:60]}...")
            except Neo4jError:
                logger.exception(
                    f"❌ Neo4j error while running query: {clean_query[:200]}..."
                )
                # Fail fast — schema must be consistent
                raise

        logger.info("🎉 Database Schema Setup Completed Successfully!")

    finally:
        if session is not None:
            session.close()
            logger.info("🔒 Database session closed.")


if __name__ == "__main__":
    try:
        db.connect()
        create_constraints()
    except Exception:
        logger.exception("💥 Database schema setup failed. Aborting.")
        sys.exit(1)
    finally:
        db.close()
