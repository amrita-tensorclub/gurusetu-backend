import logging
from app.core.database import db
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def recommend_faculty_for_student(student_id: str, limit: int = 5):
    """
    Recommend faculty members for a given student using
    Vector similarity + Graph boost (shared skills)
    """
    session = db.get_session()

    try:
        query = """
        MATCH (s:Student {user_id: $student_id})

        CALL db.index.vector.queryNodes(
            'user_embedding_index',
            $limit,
            s.embedding
        )
        YIELD node AS f, score
        WHERE f:Faculty

        OPTIONAL MATCH (s)-[:HAS_SKILL]->(c)<-[:EXPERT_IN]-(f)
        WITH f, score, COUNT(c) AS shared_concepts, collect(DISTINCT c.name) AS common_skills

        RETURN
            f.user_id AS faculty_id,
            f.name AS name,
            round((score + shared_concepts * 0.1) * 100, 2) AS match_percentage,
            common_skills
        ORDER BY match_percentage DESC
        LIMIT $limit
        """

        result = session.run(
            query,
            student_id=student_id,
            limit=limit,
        )

        return [record.data() for record in result]

    except Exception:
        logger.exception("Failed to generate faculty recommendations")
        raise HTTPException(status_code=500, detail="Recommendation failed")

    finally:
        session.close()


def recommend_students_for_opening(opening_id: str, limit: int = 10):
    """
    Recommend students for a specific opening (faculty view)
    """
    session = db.get_session()

    try:
        query = """
        MATCH (o:Opening {opening_id: $opening_id})

        CALL db.index.vector.queryNodes(
            'user_embedding_index',
            $limit,
            o.embedding
        )
        YIELD node AS s, score
        WHERE s:Student

        OPTIONAL MATCH (s)-[:HAS_SKILL]->(c)<-[:REQUIRES]-(o)
        WITH s, score, COUNT(c) AS matched_skills, collect(DISTINCT c.name) AS matching_skills

        RETURN
            s.user_id AS student_id,
            s.name AS name,
            round((score + matched_skills * 0.15) * 100, 2) AS match_percentage,
            matching_skills
        ORDER BY match_percentage DESC
        LIMIT $limit
        """

        result = session.run(
            query,
            opening_id=opening_id,
            limit=limit,
        )

        return [record.data() for record in result]

    except Exception:
        logger.exception("Failed to generate student recommendations")
        raise HTTPException(status_code=500, detail="Recommendation failed")

    finally:
        session.close()
