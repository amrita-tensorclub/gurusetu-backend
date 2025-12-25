import logging
from neo4j.exceptions import Neo4jError
from app.core.database import db

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. FACULTY DASHBOARD RECOMMENDATIONS
# --------------------------------------------------------------------------

def recommend_students_for_faculty(faculty_id: str, limit: int = 5):
    """
    Recommend students based on Faculty's research interests.
    Used for: Faculty Home Dashboard.
    Logic: (Shared Skills / Faculty Interests) * 100
    """
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $faculty_id})-[:INTERESTED_IN]->(interest:Concept)
        WITH f, collect(id(interest)) AS faculty_interests_ids, count(interest) AS total_interests
        
        MATCH (s:Student)
        WHERE s.user_id <> $faculty_id
        
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WHERE id(skill) IN faculty_interests_ids
        
        WITH s, total_interests, collect(skill.name) AS common_concepts, count(skill) AS shared_count
        
        WITH s, common_concepts, shared_count,
             CASE WHEN total_interests = 0 THEN 0
                  ELSE round((toFloat(shared_count) / total_interests) * 100, 0)
             END AS match_score

        ORDER BY match_score DESC
        LIMIT $limit
        
        RETURN s.user_id AS student_id,
               s.name AS name,
               s.department AS dept,
               s.batch AS batch,
               s.profile_picture AS pic,
               match_score,
               common_concepts
        """
        result = session.run(query, faculty_id=faculty_id, limit=limit)
        return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Error in recommend_students_for_faculty: {e}")
        return []
    finally:
        session.close()

def recommend_students_for_opening(opening_id: str, limit: int = 10):
    """
    Recommend students for a SPECIFIC job/opening.
    Used for: Clicking on an Opening to see candidates.
    Logic: (Student Skills matching Requirements / Total Requirements) * 100
    """
    session = db.get_session()
    try:
        query = """
        MATCH (o:Opening {id: $opening_id})-[:REQUIRES]->(req:Concept)
        WITH o, collect(id(req)) AS required_ids, count(req) AS total_req

        MATCH (s:Student)
        WHERE (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
          AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WHERE id(skill) IN required_ids
        
        WITH s, total_req, collect(skill.name) AS matched_skills, count(skill) AS shared_count
        
        WITH s, matched_skills,
             CASE WHEN total_req = 0 THEN 0
                  ELSE round((toFloat(shared_count) / total_req) * 100, 0)
             END AS match_score

        ORDER BY match_score DESC
        LIMIT $limit
        
        RETURN s.user_id AS student_id,
               s.name AS name,
               s.profile_picture as pic,
               match_score,
               matched_skills
        """
        result = session.run(query, opening_id=opening_id, limit=limit)
        return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Error in recommend_students_for_opening: {e}")
        return []
    finally:
        session.close()

# --------------------------------------------------------------------------
# 2. STUDENT DASHBOARD RECOMMENDATIONS
# --------------------------------------------------------------------------

def recommend_openings_for_student(student_id: str, limit: int = 5):
    """
    Recommend Openings based on Student's Skills.
    Used for: Student Home Dashboard ("92% Match" card).

    NEW: Applies recency boost:
    - Posted < 7 days ago: 1.3x multiplier
    - Posted 7-30 days ago: 1.0x (no change)
    - Posted > 30 days ago: 0.8x multiplier
    """
    session = db.get_session()
    try:
        # UPDATED QUERY: Returns faculty_id and profile_picture
        # Also filters out already-applied openings
        query = """
        MATCH (s:Student {user_id: $student_id})

        // Get already-applied openings
        OPTIONAL MATCH (s)-[:APPLIED]->(applied:Opening)
        WITH s, collect(id(applied)) AS applied_ids

        // Get student skills
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WITH s, applied_ids, collect(id(skill)) AS student_skill_ids

        MATCH (o:Opening)-[:REQUIRES]->(req:Concept)
        WHERE NOT id(o) IN applied_ids
          AND (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
          AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

        WITH o, student_skill_ids, collect(req.name) AS required_skills, count(req) AS total_req

        OPTIONAL MATCH (o)-[:REQUIRES]->(req:Concept)
        WHERE id(req) IN student_skill_ids
        WITH o, required_skills, total_req, count(req) AS matched_count

        // Base match score
        WITH o, required_skills, matched_count,
             CASE WHEN total_req = 0 THEN 0
                  ELSE round((toFloat(matched_count) / total_req) * 100, 0)
             END AS base_score

        // Recency boost calculation
        WITH o, required_skills, base_score,
             duration.inDays(o.created_at, datetime()).days AS days_old

        WITH o, required_skills, base_score, days_old,
             CASE
                 WHEN days_old < 7 THEN 1.3
                 WHEN days_old <= 30 THEN 1.0
                 ELSE 0.8
             END AS recency_multiplier

        // Apply boost to score
        WITH o, required_skills,
             round(base_score * recency_multiplier, 0) AS match_score

        MATCH (f:Faculty)-[:POSTED]->(o)

        RETURN o.id as opening_id,
               o.title as title,
               f.user_id as faculty_id,
               f.name as faculty_name,
               f.department as faculty_dept,
               f.profile_picture as faculty_pic,
               required_skills as skills,
               match_score
        ORDER BY match_score DESC
        LIMIT $limit
        """
        result = session.run(query, student_id=student_id, limit=limit)
        return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Error in recommend_openings_for_student: {e}")
        return []
    finally:
        session.close()

def recommend_faculty_for_student(student_id: str, limit: int = 5):
    """
    Recommend Faculty Mentors based on shared interests.
    Used for: Student Dashboard.
    """
    session = db.get_session()
    try:
        query = """
        MATCH (s:Student {user_id: $student_id})-[:INTERESTED_IN]->(interest:Concept)
        WITH s, collect(id(interest)) AS student_interests_ids
        
        MATCH (f:Faculty)
        OPTIONAL MATCH (f)-[:INTERESTED_IN|EXPERT_IN]->(c:Concept)
        WHERE id(c) IN student_interests_ids
        
        WITH f, collect(c.name) AS common_concepts, count(c) AS shared_count
        
        ORDER BY shared_count DESC
        LIMIT $limit
        
        RETURN f.user_id AS faculty_id,
               f.name AS name,
               f.designation AS designation,
               f.profile_picture as pic,
               shared_count as score,
               common_concepts
        """
        result = session.run(query, student_id=student_id, limit=limit)
        return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Error in recommend_faculty_for_student: {e}")
        return []
    finally:
        session.close()