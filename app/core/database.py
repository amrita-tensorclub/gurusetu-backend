from neo4j import GraphDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Neo4jDriver:
    def __init__(self):
        self._driver = None

    def connect(self):
        if self._driver is not None:
            return

        try:
            # Added configuration specifically for unstable networks/AuraDB
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=300,  # Refresh connection every 5 mins
                keep_alive=True,              # Send pings to keep connection open
                connection_acquisition_timeout=60 # Wait up to 60s for a connection
            )
            self._driver.verify_connectivity()
            print("✅ Connected to Neo4j Graph Database")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()
            print("Disconnected from Neo4j")

    def get_session(self):
        # Auto-reconnect if driver died
        if self._driver is None:
            print("⚠️ Driver was dead, reconnecting...")
            self.connect()
        
        # Verify again before giving session
        try:
            self._driver.verify_connectivity()
        except Exception:
            print("⚠️ Connection lost, reconnecting...")
            self.close()
            self.connect()

        return self._driver.session()

db = Neo4jDriver()