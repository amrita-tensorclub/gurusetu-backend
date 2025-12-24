import logging
from neo4j.exceptions import Neo4jError
from app.core.database import db

logger = logging.getLogger(__name__)


def recommend_students_for_faculty(faculty_id: str, limit: int = 10):
    """
    Recommend students to a faculty based on shared interests & skills.
    Used for Faculty Dashboard (NOT opening-specific).
    """
    session = db.get_session()

    try:
        query = """
        MATCH (f:User {user_id: $faculty_id})-[:INTERESTED_IN]->(c:Concept)
        MATCH (s:User {role: 'student'})-[:HAS_SKILL|INTERESTED_IN]->(c)

        WITH s, COUNT(DISTINCT c) AS score,
             collect(DISTINCT c.name) AS common_concepts

        ORDER BY score DESC
        LIMIT $limit

        RETURN s.user_id AS student_id,
               s.name AS name,
               score,
               common_concepts
        """

        result = session.run(
            query,
            faculty_id=faculty_id,
            limit=limit
        )

        return [
            {
                "student_id": r["student_id"],
                "name": r["name"],
                "match_score": r["score"],
                "common_concepts": r["common_concepts"],
            }
            for r in result
        ]

    except Neo4jError:
        logger.exception("Faculty dashboard recommendation failed")
        raise
    finally:
        session.close()
def recommend_students_for_opening(
    opening_id: str,
    faculty_id: str,
    limit: int = 10,
):
    """
    Recommend students for a specific opening.
    Faculty ownership is enforced.
    """
    session = db.get_session()

    try:
        query = """
        MATCH (f:User {user_id: $faculty_id})-[:POSTED]->(o:Opening {id: $opening_id})
        MATCH (o)-[:REQUIRES]->(c:Concept)
        MATCH (s:User {role: 'student'})-[:HAS_SKILL]->(c)

        WITH s, COUNT(DISTINCT c) AS score,
             collect(DISTINCT c.name) AS matched_skills

        ORDER BY score DESC
        LIMIT $limit

        RETURN s.user_id AS student_id,
               s.name AS name,
               score,
               matched_skills
        """

        result = session.run(
            query,
            faculty_id=faculty_id,
            opening_id=opening_id,
            limit=limit,
        )

        return [
            {
                "student_id": r["student_id"],
                "name": r["name"],
                "match_score": r["score"],
                "matched_skills": r["matched_skills"],
            }
            for r in result
        ]

    except Neo4jError:
        logger.exception("Opening-based student recommendation failed")
        raise
    finally:
        session.close()


def recommend_faculty_for_student(student_id: str, limit: int = 10):
    """
    Recommend faculty to a student based on shared interests & skills.
    Used for Student Dashboard (NOT opening-specific).
    """
    session = db.get_session()

    try:
        query = """
        MATCH (s:User {user_id: $student_id})-[:HAS_SKILL|INTERESTED_IN]->(c:Concept)
        MATCH (f:User {role: 'faculty'})-[:INTERESTED_IN]->(c)

        WITH f,
             COUNT(DISTINCT c) AS score,
             collect(DISTINCT c.name) AS common_concepts

        ORDER BY score DESC
        LIMIT $limit

        RETURN
            f.user_id AS faculty_id,
            f.name AS name,
            f.designation AS designation,
            score,
            common_concepts
        """

        result = session.run(
            query,
            student_id=student_id,
            limit=limit
        )

        return [
            {
                "faculty_id": r["faculty_id"],
                "name": r["name"],
                "designation": r["designation"],
                "match_score": r["score"],
                "common_concepts": r["common_concepts"],
            }
            for r in result
        ]

    except Neo4jError:
        logger.exception("Student dashboard faculty recommendation failed")
        raise
    finally:
        session.close()
