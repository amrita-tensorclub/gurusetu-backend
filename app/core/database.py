from neo4j import GraphDatabase
from app.core.config import settings

class Neo4jDriver:
    def __init__(self):
        self._driver = None

    def connect(self):
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        # Check if actually connected
        self._driver.verify_connectivity()
        print("✅ Connected to Neo4j Graph Database!")

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


# Create a single instance to use everywhere
db = Neo4jDriver()