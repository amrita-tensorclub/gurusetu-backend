import logging
from typing import List, Dict
from app.core.database import db

logger = logging.getLogger(__name__)

# STUDENT → FACULTY MATCHING

def recommend_faculty_for_student(student_id: str, limit: int = 5) -> List[Dict]:
    """
    Recommend faculty members for a given student using GraphRAG logic
    """

    session = db.get_session()

    try:
        query = """
        MATCH (s:User:Student {user_id: $student_id})

        // Student skills & interests
        OPTIONAL MATCH (s)-[:HAS_SKILL|INTERESTED_IN]->(c:Concept)
        WITH s, collect(DISTINCT c) AS student_concepts

        // Student project technologies
        OPTIONAL MATCH (s)-[:COMPLETED|AUTHORED]->(:Work)-[:USED_TECH]->(tc:Concept)
        WITH s, student_concepts + collect(DISTINCT tc) AS all_student_concepts

        // Faculty interests
        MATCH (f:User:Faculty)
        OPTIONAL MATCH (f)-[:INTERESTED_IN]->(fc:Concept)

        WITH s, f,
             apoc.coll.intersection(all_student_concepts, collect(DISTINCT fc)) AS common_concepts

        WITH f,
             size(common_concepts) AS score,
             [c IN common_concepts | c.name] AS matched_tags

        WHERE score > 0
        RETURN
            f.user_id AS faculty_id,
            f.name AS faculty_name,
            score AS match_score,
            matched_tags
        ORDER BY score DESC
        LIMIT $limit
        """

        results = session.run(
            query,
            student_id=student_id,
            limit=limit,
        )

        recommendations = []
        for record in results:
            recommendations.append({
                "faculty_id": record["faculty_id"],
                "faculty_name": record["faculty_name"],
                "match_score": record["match_score"],
                "matched_concepts": record["matched_tags"],
            })

        return recommendations

    except Exception:
        logger.exception("Faculty recommendation failed")
        return []
    finally:
        session.close()


# OPENING → STUDENT MATCHING (FOR FACULTY)

def recommend_students_for_opening(opening_id: str, limit: int = 5) -> List[Dict]:
    """
    Recommend students for a given opening
    """

    session = db.get_session()

    try:
        query = """
        MATCH (o:Opening {id: $opening_id})
        MATCH (o)-[:REQUIRES]->(rc:Concept)

        MATCH (s:User:Student)

        OPTIONAL MATCH (s)-[:HAS_SKILL|INTERESTED_IN]->(sc:Concept)
        OPTIONAL MATCH (s)-[:COMPLETED|AUTHORED]->(:Work)-[:USED_TECH]->(tc:Concept)

        WITH s, o,
             collect(DISTINCT rc) AS required,
             collect(DISTINCT sc) + collect(DISTINCT tc) AS student_stack

        WITH s,
             apoc.coll.intersection(required, student_stack) AS matched

        WITH s,
             size(matched) AS score,
             [c IN matched | c.name] AS matched_skills

        WHERE score > 0
        RETURN
            s.user_id AS student_id,
            s.name AS student_name,
            score AS match_score,
            matched_skills
        ORDER BY score DESC
        LIMIT $limit
        """

        results = session.run(
            query,
            opening_id=opening_id,
            limit=limit,
        )

        students = []
        for record in results:
            students.append({
                "student_id": record["student_id"],
                "student_name": record["student_name"],
                "match_score": record["match_score"],
                "matched_skills": record["matched_skills"],
            })

        return students

    except Exception:
        logger.exception("Student recommendation failed")
        return []
    finally:
        session.close()
