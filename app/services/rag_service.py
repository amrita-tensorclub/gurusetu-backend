# import logging
# from neo4j.exceptions import Neo4jError
# from app.core.database import db
# import logging
# from neo4j.exceptions import Neo4jError
# from app.core.database import db
# from app.services.embedding import generate_embedding

# logger = logging.getLogger(__name__)

# # --------------------------------------------------------------------------
# # 1. FACULTY DASHBOARD RECOMMENDATIONS
# # --------------------------------------------------------------------------

# def recommend_students_for_faculty(faculty_id: str, limit: int = 5):
#     """
#     Recommend students based on Faculty's research interests.
#     Used for: Faculty Home Dashboard.
#     Logic: (Shared Skills / Faculty Interests) * 100
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (f:Faculty {user_id: $faculty_id})-[:INTERESTED_IN]->(interest:Concept)
#         WITH f, collect(id(interest)) AS faculty_interests_ids, count(interest) AS total_interests
        
#         MATCH (s:Student)
#         WHERE s.user_id <> $faculty_id
        
#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WHERE id(skill) IN faculty_interests_ids
        
#         WITH s, total_interests, collect(skill.name) AS common_concepts, count(skill) AS shared_count
        
#         WITH s, common_concepts, shared_count,
#              CASE WHEN total_interests = 0 THEN 0
#                   ELSE round((toFloat(shared_count) / total_interests) * 100, 0)
#              END AS match_score

#         ORDER BY match_score DESC
#         LIMIT $limit
        
#         RETURN s.user_id AS student_id,
#                s.name AS name,
#                s.department AS dept,
#                s.batch AS batch,
#                s.profile_picture AS pic,
#                match_score,
#                common_concepts
#         """
#         result = session.run(query, faculty_id=faculty_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_students_for_faculty: {e}")
#         return []
#     finally:
#         session.close()

# def recommend_students_for_opening(opening_id: str, limit: int = 10):
#     """
#     Recommend students for a SPECIFIC job/opening.
#     Used for: Clicking on an Opening to see candidates.
#     Logic: (Student Skills matching Requirements / Total Requirements) * 100
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (o:Opening {id: $opening_id})-[:REQUIRES]->(req:Concept)
#         WITH o, collect(id(req)) AS required_ids, count(req) AS total_req

#         MATCH (s:Student)
#         WHERE (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
#           AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WHERE id(skill) IN required_ids
        
#         WITH s, total_req, collect(skill.name) AS matched_skills, count(skill) AS shared_count
        
#         WITH s, matched_skills,
#              CASE WHEN total_req = 0 THEN 0
#                   ELSE round((toFloat(shared_count) / total_req) * 100, 0)
#              END AS match_score

#         ORDER BY match_score DESC
#         LIMIT $limit
        
#         RETURN s.user_id AS student_id,
#                s.name AS name,
#                s.profile_picture as pic,
#                match_score,
#                matched_skills
#         """
#         result = session.run(query, opening_id=opening_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_students_for_opening: {e}")
#         return []
#     finally:
#         session.close()

# # --------------------------------------------------------------------------
# # 2. STUDENT DASHBOARD RECOMMENDATIONS
# # --------------------------------------------------------------------------

# def recommend_openings_for_student(student_id: str, limit: int = 5):
#     """
#     Recommend Openings based on Student's Skills.
#     Used for: Student Home Dashboard ("92% Match" card).
#     """
#     session = db.get_session()
#     try:
#         # UPDATED QUERY: Returns faculty_id and profile_picture
#         # Also filters out already-applied openings
#         query = """
#         MATCH (s:Student {user_id: $student_id})

#         // Get already-applied openings
#         OPTIONAL MATCH (s)-[:APPLIED]->(applied:Opening)
#         WITH s, collect(id(applied)) AS applied_ids

#         // Get student skills
#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WITH s, applied_ids, collect(id(skill)) AS student_skill_ids

#         MATCH (o:Opening)-[:REQUIRES]->(req:Concept)
#         WHERE NOT id(o) IN applied_ids
#           AND (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
#           AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

#         WITH o, student_skill_ids, collect(req.name) AS required_skills, count(req) AS total_req
        
#         OPTIONAL MATCH (o)-[:REQUIRES]->(req:Concept)
#         WHERE id(req) IN student_skill_ids
#         WITH o, required_skills, total_req, count(req) AS matched_count
        
#         WITH o, required_skills, matched_count,
#              CASE WHEN total_req = 0 THEN 0
#                   ELSE round((toFloat(matched_count) / total_req) * 100, 0)
#              END AS match_score

#         MATCH (f:Faculty)-[:POSTED]->(o)
        
#         RETURN o.id as opening_id,
#                o.title as title,
#                f.user_id as faculty_id,            
#                f.name as faculty_name,
#                f.department as faculty_dept,
#                f.profile_picture as faculty_pic,   
#                required_skills as skills,
#                match_score
#         ORDER BY match_score DESC
#         LIMIT $limit
#         """
#         result = session.run(query, student_id=student_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_openings_for_student: {e}")
#         return []
#     finally:
#         session.close()

# def recommend_faculty_for_student(student_id: str, limit: int = 5):
#     """
#     Recommend Faculty Mentors based on shared interests.
#     Used for: Student Dashboard.
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (s:Student {user_id: $student_id})-[:INTERESTED_IN]->(interest:Concept)
#         WITH s, collect(id(interest)) AS student_interests_ids
        
#         MATCH (f:Faculty)
#         OPTIONAL MATCH (f)-[:INTERESTED_IN|EXPERT_IN]->(c:Concept)
#         WHERE id(c) IN student_interests_ids
        
#         WITH f, collect(c.name) AS common_concepts, count(c) AS shared_count
        
#         ORDER BY shared_count DESC
#         LIMIT $limit
        
#         RETURN f.user_id AS faculty_id,
#                f.name AS name,
#                f.designation AS designation,
#                f.profile_picture as pic,
#                shared_count as score,
#                common_concepts
#         """
#         result = session.run(query, student_id=student_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_faculty_for_student: {e}")
#         return []
#     finally:
#         session.close()
# logger = logging.getLogger(__name__)

# # --------------------------------------------------------------------------
# # 1. FACULTY DASHBOARD RECOMMENDATIONS
# # --------------------------------------------------------------------------

# def recommend_students_for_faculty(faculty_id: str, limit: int = 5):
#     """
#     Recommend students based on Faculty's research interests.
#     Used for: Faculty Home Dashboard.
#     Logic: (Shared Skills / Faculty Interests) * 100
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (f:Faculty {user_id: $faculty_id})-[:INTERESTED_IN]->(interest:Concept)
#         WITH f, collect(id(interest)) AS faculty_interests_ids, count(interest) AS total_interests
        
#         MATCH (s:Student)
#         WHERE s.user_id <> $faculty_id
        
#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WHERE id(skill) IN faculty_interests_ids
        
#         WITH s, total_interests, collect(skill.name) AS common_concepts, count(skill) AS shared_count
        
#         WITH s, common_concepts, shared_count,
#              CASE WHEN total_interests = 0 THEN 0
#                   ELSE round((toFloat(shared_count) / total_interests) * 100, 0)
#              END AS match_score

#         ORDER BY match_score DESC
#         LIMIT $limit
        
#         RETURN s.user_id AS student_id,
#                s.name AS name,
#                s.department AS dept,
#                s.batch AS batch,
#                s.profile_picture AS pic,
#                match_score,
#                common_concepts
#         """
#         result = session.run(query, faculty_id=faculty_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_students_for_faculty: {e}")
#         return []
#     finally:
#         session.close()

# def recommend_students_for_opening(opening_id: str, limit: int = 10):
#     """
#     Recommend students for a SPECIFIC job/opening.
#     Used for: Clicking on an Opening to see candidates.
#     Logic: (Student Skills matching Requirements / Total Requirements) * 100
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (o:Opening {id: $opening_id})-[:REQUIRES]->(req:Concept)
#         WITH o, collect(id(req)) AS required_ids, count(req) AS total_req

#         MATCH (s:Student)
#         WHERE (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
#           AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WHERE id(skill) IN required_ids
        
#         WITH s, total_req, collect(skill.name) AS matched_skills, count(skill) AS shared_count
        
#         WITH s, matched_skills,
#              CASE WHEN total_req = 0 THEN 0
#                   ELSE round((toFloat(shared_count) / total_req) * 100, 0)
#              END AS match_score

#         ORDER BY match_score DESC
#         LIMIT $limit
        
#         RETURN s.user_id AS student_id,
#                s.name AS name,
#                s.profile_picture as pic,
#                match_score,
#                matched_skills
#         """
#         result = session.run(query, opening_id=opening_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_students_for_opening: {e}")
#         return []
#     finally:
#         session.close()

# # --------------------------------------------------------------------------
# # 2. STUDENT DASHBOARD RECOMMENDATIONS
# # --------------------------------------------------------------------------

# def recommend_openings_for_student(student_id: str, limit: int = 5):
#     """
#     Recommend Openings based on Student's Skills.
#     Used for: Student Home Dashboard ("92% Match" card).
#     """
#     session = db.get_session()
#     try:
#         # UPDATED QUERY: Returns faculty_id and profile_picture
#         # Also filters out already-applied openings
#         query = """
#         MATCH (s:Student {user_id: $student_id})

#         // Get already-applied openings
#         OPTIONAL MATCH (s)-[:APPLIED]->(applied:Opening)
#         WITH s, collect(id(applied)) AS applied_ids

#         // Get student skills
#         OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
#         WITH s, applied_ids, collect(id(skill)) AS student_skill_ids

#         MATCH (o:Opening)-[:REQUIRES]->(req:Concept)
#         WHERE NOT id(o) IN applied_ids
#           AND (o.min_cgpa IS NULL OR s.cgpa >= o.min_cgpa)
#           AND (size(o.target_years) = 0 OR s.batch IN o.target_years)

#         WITH o, student_skill_ids, collect(req.name) AS required_skills, count(req) AS total_req
        
#         OPTIONAL MATCH (o)-[:REQUIRES]->(req:Concept)
#         WHERE id(req) IN student_skill_ids
#         WITH o, required_skills, total_req, count(req) AS matched_count
        
#         WITH o, required_skills, matched_count,
#              CASE WHEN total_req = 0 THEN 0
#                   ELSE round((toFloat(matched_count) / total_req) * 100, 0)
#              END AS match_score

#         MATCH (f:Faculty)-[:POSTED]->(o)
        
#         RETURN o.id as opening_id,
#                o.title as title,
#                f.user_id as faculty_id,            
#                f.name as faculty_name,
#                f.department as faculty_dept,
#                f.profile_picture as faculty_pic,   
#                required_skills as skills,
#                match_score
#         ORDER BY match_score DESC
#         LIMIT $limit
#         """
#         result = session.run(query, student_id=student_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_openings_for_student: {e}")
#         return []
#     finally:
#         session.close()

# def recommend_faculty_for_student(student_id: str, limit: int = 5):
#     """
#     Recommend Faculty Mentors based on shared interests.
#     Used for: Student Dashboard.
#     """
#     session = db.get_session()
#     try:
#         query = """
#         MATCH (s:Student {user_id: $student_id})-[:INTERESTED_IN]->(interest:Concept)
#         WITH s, collect(id(interest)) AS student_interests_ids
        
#         MATCH (f:Faculty)
#         OPTIONAL MATCH (f)-[:INTERESTED_IN|EXPERT_IN]->(c:Concept)
#         WHERE id(c) IN student_interests_ids
        
#         WITH f, collect(c.name) AS common_concepts, count(c) AS shared_count
        
#         ORDER BY shared_count DESC
#         LIMIT $limit
        
#         RETURN f.user_id AS faculty_id,
#                f.name AS name,
#                f.designation AS designation,
#                f.profile_picture as pic,
#                shared_count as score,
#                common_concepts
#         """
#         result = session.run(query, student_id=student_id, limit=limit)
#         return [record.data() for record in result]
#     except Exception as e:
#         logger.error(f"Error in recommend_faculty_for_student: {e}")
#         return []
#     finally:
#         session.close()



# '''
#     sematinc search for students
# '''

# def semantic_search_students(query: str, limit: int = 5):
#     """
#     Semantic similarity search for students using vector embeddings.
#     Used for: Search bar, advanced faculty discovery.
#     """
#     session = db.get_session()
#     embedding = generate_embedding(query)

#     try:
#         cypher = """
#         CALL db.index.vector.queryNodes(
#           'student_bio_index',
#           $limit,
#           $embedding
#         )
#         YIELD node, score
#         RETURN node.user_id AS student_id,
#                node.name AS name,
#                node.department AS dept,
#                node.batch AS batch,
#                node.profile_picture AS pic,
#                round(score * 100, 2) AS similarity_score
#         ORDER BY similarity_score DESC
#         """
#         result = session.run(
#             cypher,
#             embedding=embedding,
#             limit=limit
#         )
#         return [r.data() for r in result]
#     except Exception as e:
#         logger.error(f"Error in semantic_search_students: {e}")
#         return []
#     finally:
#         session.close()


# '''
#     SEMANTICS SEARCH FOR FACULTY
# '''

# def semantic_search_faculty(query: str, limit: int = 5):
#     """
#     Semantic similarity search for faculty based on research profile.
#     """
#     session = db.get_session()
#     embedding = generate_embedding(query)

#     try:
#         cypher = """
#         CALL db.index.vector.queryNodes(
#           'faculty_research_index',
#           $limit,
#           $embedding
#         )
#         YIELD node, score
#         RETURN node.user_id AS faculty_id,
#                node.name AS name,
#                node.department AS dept,
#                node.designation AS designation,
#                node.profile_picture AS pic,
#                round(score * 100, 2) AS similarity_score
#         ORDER BY similarity_score DESC
#         """
#         result = session.run(
#             cypher,
#             embedding=embedding,
#             limit=limit
#         )
#         return [r.data() for r in result]
#     except Exception as e:
#         logger.error(f"Error in semantic_search_faculty: {e}")
#         return []
#     finally:
#         session.close()

import logging
from app.core.database import db
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

# ============================================================================
# 1. FACULTY DASHBOARD RECOMMENDATIONS (GRAPH-BASED)
# ============================================================================

def recommend_students_for_faculty(faculty_id: str, limit: int = 5):
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $faculty_id})-[:INTERESTED_IN]->(interest:Concept)
        WITH collect(id(interest)) AS interest_ids, count(interest) AS total

        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(c:Concept)
        WHERE id(c) IN interest_ids

        WITH s, total, collect(c.name) AS common, count(c) AS shared
        WITH s, common,
             CASE WHEN total = 0 THEN 0
                  ELSE round((toFloat(shared)/total)*100, 0)
             END AS match_score

        ORDER BY match_score DESC
        LIMIT $limit

        RETURN s.user_id AS student_id,
               s.name AS name,
               s.department AS dept,
               s.batch AS batch,
               s.profile_picture AS pic,
               match_score,
               common
        """
        return [r.data() for r in session.run(query, faculty_id=faculty_id, limit=limit)]
    except Exception as e:
        logger.error(f"recommend_students_for_faculty error: {e}")
        return []
    finally:
        session.close()


def recommend_students_for_opening(opening_id: str, limit: int = 10):
    session = db.get_session()
    try:
        query = """
        MATCH (o:Opening {id: $opening_id})-[:REQUIRES]->(req:Concept)
        WITH collect(id(req)) AS req_ids, count(req) AS total

        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(c:Concept)
        WHERE id(c) IN req_ids

        WITH s, total, collect(c.name) AS matched, count(c) AS shared
        WITH s, matched,
             CASE WHEN total = 0 THEN 0
                  ELSE round((toFloat(shared)/total)*100, 0)
             END AS match_score

        ORDER BY match_score DESC
        LIMIT $limit

        RETURN s.user_id AS student_id,
               s.name AS name,
               s.profile_picture AS pic,
               match_score,
               matched
        """
        return [r.data() for r in session.run(query, opening_id=opening_id, limit=limit)]
    except Exception as e:
        logger.error(f"recommend_students_for_opening error: {e}")
        return []
    finally:
        session.close()


# ============================================================================
# 2. STUDENT DASHBOARD RECOMMENDATIONS (GRAPH-BASED)
# ============================================================================

def recommend_openings_for_student(student_id: str, limit: int = 5):
    session = db.get_session()
    try:
        query = """
        MATCH (s:Student {user_id: $student_id})
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WITH s, collect(id(skill)) AS skill_ids

        MATCH (o:Opening)-[:REQUIRES]->(req:Concept)
        WITH o, skill_ids, collect(id(req)) AS req_ids

        WITH o,
             size([x IN req_ids WHERE x IN skill_ids]) AS matched,
             size(req_ids) AS total

        WITH o,
             CASE WHEN total = 0 THEN 0
                  ELSE round((toFloat(matched)/total)*100, 0)
             END AS match_score

        MATCH (f:Faculty)-[:POSTED]->(o)

        RETURN o.id AS opening_id,
               o.title AS title,
               f.name AS faculty_name,
               f.profile_picture AS faculty_pic,
               match_score
        ORDER BY match_score DESC
        LIMIT $limit
        """
        return [r.data() for r in session.run(query, student_id=student_id, limit=limit)]
    except Exception as e:
        logger.error(f"recommend_openings_for_student error: {e}")
        return []
    finally:
        session.close()


def recommend_faculty_for_student(student_id: str, limit: int = 5):
    session = db.get_session()
    try:
        query = """
        MATCH (s:Student {user_id: $student_id})-[:INTERESTED_IN]->(c:Concept)
        WITH collect(id(c)) AS ids

        MATCH (f:Faculty)
        OPTIONAL MATCH (f)-[:INTERESTED_IN|EXPERT_IN]->(c:Concept)
        WHERE id(c) IN ids

        WITH f, collect(c.name) AS common, count(c) AS shared
        ORDER BY shared DESC
        LIMIT $limit

        RETURN f.user_id AS faculty_id,
               f.name AS name,
               f.designation AS designation,
               f.profile_picture AS pic,
               shared,
               common
        """
        return [r.data() for r in session.run(query, student_id=student_id, limit=limit)]
    except Exception as e:
        logger.error(f"recommend_faculty_for_student error: {e}")
        return []
    finally:
        session.close()


# ============================================================================
# 3. SEMANTIC SEARCH (VECTOR-BASED)
# ============================================================================

def semantic_search_students(query: str, limit: int = 5):
    embedding = generate_embedding(query)
    if not embedding:
        return []

    session = db.get_session()
    try:
        cypher = """
        CALL db.index.vector.queryNodes(
            'student_bio_index',
            $limit,
            $embedding
        )
        YIELD node, score
        RETURN node.user_id AS student_id,
               node.name AS name,
               node.department AS dept,
               node.profile_picture AS pic,
               round(score * 100, 2) AS similarity_score
        ORDER BY similarity_score DESC
        """
        return [r.data() for r in session.run(cypher, embedding=embedding, limit=limit)]
    except Exception as e:
        logger.error(f"semantic_search_students error: {e}")
        return []
    finally:
        session.close()


def semantic_search_faculty(query: str, limit: int = 5):
    embedding = generate_embedding(query)
    if not embedding:
        return []

    session = db.get_session()
    try:
        cypher = """
        CALL db.index.vector.queryNodes(
            'faculty_research_index',
            $limit,
            $embedding
        )
        YIELD node, score
        RETURN node.user_id AS faculty_id,
               node.name AS name,
               node.department AS dept,
               node.designation AS designation,
               node.profile_picture AS pic,
               round(score * 100, 2) AS similarity_score
        ORDER BY similarity_score DESC
        """
        return [r.data() for r in session.run(cypher, embedding=embedding, limit=limit)]
    except Exception as e:
        logger.error(f"semantic_search_faculty error: {e}")
        return []
    finally:
        session.close()
