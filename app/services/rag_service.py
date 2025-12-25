import logging
from neo4j.exceptions import Neo4jError
from app.core.database import db

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. FACULTY DASHBOARD RECOMMENDATIONS
# --------------------------------------------------------------------------

def recommend_students_for_faculty(faculty_id: str, limit: int = 5):
    """
    Recommend students for a faculty member based on overlap between the faculty's interest concepts and students' skills.
    
    match_score is the percentage (0–100) of the faculty's interests that each student has (rounded to the nearest integer). Students with higher match_score appear first.
    
    Parameters:
        faculty_id (str): The faculty user's identifier (user_id) to base recommendations on.
        limit (int): Maximum number of student recommendations to return.
    
    Returns:
        list[dict]: A list of recommendation records. Each record contains:
            - student_id (str): Student's user_id.
            - name (str): Student's name.
            - dept (str): Student's department.
            - batch (str|int): Student's batch/year.
            - pic (str|None): URL or identifier of the student's profile picture.
            - match_score (int): Percentage score (0–100) representing overlap with faculty interests.
            - common_concepts (list[str]): Names of concepts/skills shared between the faculty and the student.
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
    Recommend students for a specific opening by scoring each student on the percentage of the opening's required skills they possess.
    
    Parameters:
        opening_id (str): ID of the Opening to match candidates against.
        limit (int): Maximum number of student records to return.
    
    Returns:
        list[dict]: A list of student recommendation records ordered by descending match score. Each record contains:
            - student_id (str): Student's user ID.
            - name (str): Student's name.
            - pic: Student's profile picture URL or value stored in the profile.
            - match_score (int): Percentage (0–100) of the opening's required skills that the student has.
            - matched_skills (list[str]): Names of the required skills the student possesses.
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
    Recommend openings for a student based on the student's skills and eligibility.
    
    Filters out openings the student has already applied to and enforces opening-specific CGPA and target-year constraints; results are ordered by skill match percentage.
    
    Parameters:
        student_id (str): The student's user ID to compute recommendations for.
        limit (int): Maximum number of openings to return.
    
    Returns:
        List[dict]: Each dict contains:
            - opening_id: Opening identifier.
            - title: Opening title.
            - faculty_id: Posting faculty's user ID.
            - faculty_name: Posting faculty's name.
            - faculty_dept: Posting faculty's department.
            - faculty_pic: Posting faculty's profile picture URL or path.
            - skills: List of required skill names for the opening.
            - match_score: Integer percentage (0–100) of required skills the student has.
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
        
        WITH o, required_skills, matched_count,
             CASE WHEN total_req = 0 THEN 0
                  ELSE round((toFloat(matched_count) / total_req) * 100, 0)
             END AS match_score

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