from fastapi import APIRouter, HTTPException, Depends
from app.models.openings import OpeningCreate, OpeningUpdate
from app.core.database import db
from app.core.security import get_current_user
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{opening_id}")
def get_opening(opening_id: str):
    """Get a single opening by ID with faculty info and required skills."""
    session = db.get_session()
    try:
        query = """
        MATCH (f:User)-[:POSTED]->(o:Opening {id: $opening_id})
        OPTIONAL MATCH (o)-[:REQUIRES]->(c:Concept)
        RETURN o.id AS id,
               o.title AS title,
               o.description AS description,
               o.expected_duration AS expected_duration,
               o.target_years AS target_years,
               o.min_cgpa AS min_cgpa,
               o.deadline AS deadline,
               o.status AS status,
               o.created_at AS created_at,
               f.user_id AS faculty_id,
               f.name AS faculty_name,
               f.department AS faculty_department,
               collect(c.name) AS required_skills
        """
        result = session.run(query, opening_id=opening_id).single()

        if not result:
            raise HTTPException(status_code=404, detail="Opening not found")

        return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching opening: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch opening")
    finally:
        session.close()


@router.put("/{opening_id}")
def update_opening(
    opening_id: str,
    update: OpeningUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an opening. Only the faculty who posted it can update."""
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403, detail="Only faculty can update openings")

    session = db.get_session()
    try:
        # Verify ownership
        ownership_query = """
        MATCH (f:User {user_id: $faculty_id})-[:POSTED]->(o:Opening {id: $opening_id})
        RETURN o
        """
        if not session.run(ownership_query, faculty_id=current_user["user_id"], opening_id=opening_id).single():
            raise HTTPException(
                status_code=404, detail="Opening not found or you don't have permission")

        # Build dynamic SET clause for provided fields
        update_data = update.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Handle skills separately (requires relationship update)
        skills = update_data.pop("required_skills", None)

        # Update scalar fields
        if update_data:
            set_clauses = ", ".join(
                [f"o.{k} = ${k}" for k in update_data.keys()])
            update_query = f"""
            MATCH (o:Opening {{id: $opening_id}})
            SET {set_clauses}
            RETURN o.id
            """
            session.run(update_query, opening_id=opening_id, **update_data)

        # Update skills if provided
        if skills is not None:
            skills_query = """
            MATCH (o:Opening {id: $opening_id})
            OPTIONAL MATCH (o)-[r:REQUIRES]->(:Concept)
            DELETE r
            WITH o
            UNWIND $skills AS skill_name
            MERGE (c:Concept {name: toLower(skill_name)})
            MERGE (o)-[:REQUIRES]->(c)
            """
            session.run(skills_query, opening_id=opening_id, skills=skills)

        return {"message": "Opening updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating opening: {e}")
        raise HTTPException(status_code=500, detail="Failed to update opening")
    finally:
        session.close()


@router.delete("/{opening_id}")
def delete_opening(
    opening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an opening. Only the faculty who posted it can delete."""
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403, detail="Only faculty can delete openings")

    session = db.get_session()
    try:
        # Verify ownership and delete (including relationships)
        delete_query = """
        MATCH (f:User {user_id: $faculty_id})-[:POSTED]->(o:Opening {id: $opening_id})
        OPTIONAL MATCH (o)-[r]-()  // All relationships
        OPTIONAL MATCH (n:Notification {trigger_id: $opening_id})
        DETACH DELETE o, n
        RETURN count(o) AS deleted
        """
        result = session.run(
            delete_query, faculty_id=current_user["user_id"], opening_id=opening_id).single()

        if not result or result["deleted"] == 0:
            raise HTTPException(
                status_code=404, detail="Opening not found or you don't have permission")

        return {"message": "Opening deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting opening: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete opening")
    finally:
        session.close()


@router.post("/")
def create_opening(
    opening: OpeningCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can create openings"
        )

    faculty_id = current_user["user_id"]
    session = db.get_session()
    opening_id = str(uuid.uuid4())

    try:
     # ... inside create_opening function ...

        query = """
        MATCH (f:User {user_id: $faculty_id})

        CREATE (o:Opening {
            id: $opening_id,
            title: $title,
            description: $description,
            expected_duration: $expected_duration,
            target_years: $target_years,
            min_cgpa: $min_cgpa,
            deadline: $deadline,
            status: 'Active',  // <--- ADD THIS LINE
            created_at: datetime()
        })

        MERGE (f)-[:POSTED]->(o)

        WITH o
        UNWIND $skills AS skill_name
        MERGE (c:Concept {name: toLower(skill_name)})
        MERGE (o)-[:REQUIRES]->(c)

        RETURN o.id AS id
        """
# ... rest of the file

        session.run(
            query,
            faculty_id=faculty_id,
            opening_id=opening_id,
            title=opening.title,
            description=opening.description,
            skills=opening.required_skills,
            expected_duration=opening.expected_duration,
            target_years=opening.target_years,
            min_cgpa=opening.min_cgpa,
            deadline=opening.deadline
        )

        return {"message": "Opening created!", "opening_id": opening_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
