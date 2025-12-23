from neo4j import GraphDatabase
from app.core.config import settings
from neo4j.exceptions import Neo4jError

class Neo4jDriver:
    def __init__(self):
        self._driver = None

    def connect(self):
        if self._driver is not None:
            return  # already connected

        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            self._driver.verify_connectivity()
            print("✅ Connected to Neo4j Graph Database")
        except Neo4jError as e:
            self._driver = None
            raise RuntimeError(f"Failed to connect to Neo4j: {e}") from e

    def close(self):
        if self._driver:
            self._driver.close()
            print("🛑 Disconnected from Neo4j")

    def get_session(self):
        if self._driver is None:
            raise RuntimeError(
                "Database driver is not initialized. Call connect() before get_session()."
            )
        return self._driver.session()


db = Neo4jDriver()