from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.database import db
from datetime import datetime
import json
import uuid

router = APIRouter()

# --- MODELS ---
class StatusUpdate(BaseModel):
    status: str       # "Available", "Busy", "In Class", "Away"
    source: str       # "Manual", "Student-QR" (Crowdsourcing)

class FutureCheck(BaseModel):
    datetime: str     # ISO Format: "2024-03-25T14:30:00"

# --- MOCK TIMETABLE (Fallback) ---
MOCK_TIMETABLE = [
    { "day": 'Monday', "start": '09:00', "end": '10:00', "activity": 'Class (CS302)' },
    { "day": 'Monday', "start": '14:00', "end": '16:00', "activity": 'Lab (CS304)' },
    { "day": 'Tuesday', "start": '11:00', "end": '12:00', "activity": 'Office Hours' },
    { "day": 'Wednesday', "start": '09:00', "end": '10:00', "activity": 'Class (CS302)' },
    { "day": 'Friday', "start": '10:00', "end": '11:00', "activity": 'Dept Meeting' },
]

# --- NOTIFICATION HELPER ---
def create_system_notification(tx, user_id, message, type="ALERT"):
    """
    Writes a notification directly to the user's node in Neo4j.
    """
    query = """
    MATCH (u:User {user_id: $uid})
    CREATE (n:Notification {
        id: $nid,
        message: $message,
        type: $type,
        is_read: false,
        created_at: datetime(),
        trigger_role: 'System'
    })
    CREATE (n)-[:NOTIFIES]->(u)
    """
    tx.run(query, uid=user_id, nid=str(uuid.uuid4()), message=message, type=type)

# ==========================================
# 1. SEEDING
# ==========================================
@router.post("/seed")
def seed_locator_data():
    """
    Migrates the provided SQL/JSON map data into Neo4j.
    Creates (:Cabin) nodes and links (:Faculty) to them.
    """
    session = db.get_session()
    try:
        # 1. Cabin Data
        cabins = [
            {'code': 'AP 9', 'block': 'Block A', 'coords': '{"top": 85, "left": 70}', 'dir': 'Block A (South).'},
            {'code': 'AP 12', 'block': 'Block A', 'coords': '{"top": 85, "left": 65}', 'dir': 'Block A (South).'},
            {'code': 'AP 8', 'block': 'Block A', 'coords': '{"top": 85, "left": 75}', 'dir': 'Block A (South).'},
            {'code': 'AP 13', 'block': 'Block A', 'coords': '{"top": 82, "left": 80}', 'dir': 'Block A.'},
            {'code': 'AP 14', 'block': 'Block A', 'coords': '{"top": 82, "left": 75}', 'dir': 'Block A.'},
            {'code': 'AP 15', 'block': 'Block A', 'coords': '{"top": 82, "left": 70}', 'dir': 'Block A.'},
            {'code': 'AP 1', 'block': 'Block A', 'coords': '{"top": 85, "left": 80}', 'dir': 'Block A (South).'},
            {'code': 'AP 19', 'block': 'Block A', 'coords': '{"top": 80, "left": 65}', 'dir': 'Block A.'},
            {'code': 'AP 20', 'block': 'Block A', 'coords': '{"top": 80, "left": 60}', 'dir': 'Block A.'},
            {'code': 'AP 18', 'block': 'Block A', 'coords': '{"top": 80, "left": 70}', 'dir': 'Block A.'},
            {'code': 'AP 17', 'block': 'Block A', 'coords': '{"top": 80, "left": 75}', 'dir': 'Block A.'},
            {'code': 'AP 16', 'block': 'Block A', 'coords': '{"top": 80, "left": 80}', 'dir': 'Block A.'},
            {'code': 'P 2', 'block': 'Center Block', 'coords': '{"top": 50, "left": 45}', 'dir': 'Center Block.'},
            {'code': 'P 3', 'block': 'Center Block', 'coords': '{"top": 50, "left": 40}', 'dir': 'Center Block.'},
            {'code': 'P 4', 'block': 'Center Block', 'coords': '{"top": 50, "left": 55}', 'dir': 'Center Block.'},
            {'code': 'P 5', 'block': 'Center Block', 'coords': '{"top": 50, "left": 60}', 'dir': 'Center Block.'},
            {'code': 'P 1', 'block': 'Center Block', 'coords': '{"top": 50, "left": 50}', 'dir': 'Center Block.'},
            {'code': 'VICE CHAIR', 'block': 'Admin', 'coords': '{"top": 90, "left": 45}', 'dir': 'Vice Chairperson Office.'},
            {'code': 'PRINCIPAL', 'block': 'Admin', 'coords': '{"top": 90, "left": 50}', 'dir': 'Principal Office.'},
        ]

        # 2. Faculty Assignments
        faculty_assignments = [
            {'name': 'Dr. Bagavathi C', 'cabin': 'AP 9', 'status': 'Available'},
            {'name': 'Deepika T', 'cabin': 'AP 12', 'status': 'Busy'},
            {'name': 'Dr. Dhanya M Dhanyalakshmy', 'cabin': 'AP 8', 'status': 'Available'},
            {'name': 'Dr. Vandana S', 'cabin': 'AP 13', 'status': 'In Class'},
            {'name': 'Sujee R', 'cabin': 'AP 14', 'status': 'Available'},
            {'name': 'Dr. J Uma', 'cabin': 'AP 15', 'status': 'Busy'},
            {'name': 'Arjun PK', 'cabin': 'AP 1', 'status': 'Available'},
            {'name': 'Prajna Dora', 'cabin': 'AP 19', 'status': 'Away'},
            {'name': 'Govindarajan J', 'cabin': 'AP 20', 'status': 'Available'},
            {'name': 'Malathi P', 'cabin': 'AP 18', 'status': 'Available'},
            {'name': 'Prathilothamai M', 'cabin': 'AP 17', 'status': 'Available'},
            {'name': 'Bharati D', 'cabin': 'AP 16', 'status': 'Busy'},
            {'name': 'Thangavelu S', 'cabin': 'P 2', 'status': 'Available'},
            {'name': 'Padmavathi S', 'cabin': 'P 3', 'status': 'In Class'},
            {'name': 'Rajathilagam B', 'cabin': 'P 4', 'status': 'Available'},
            {'name': 'Radhika N', 'cabin': 'P 5', 'status': 'Busy'},
            {'name': 'Gireesh Kumar T', 'cabin': 'P 1', 'status': 'Available'},
            {'name': 'Vice Chairperson', 'cabin': 'VICE CHAIR', 'status': 'Available'},
            {'name': 'Principal', 'cabin': 'PRINCIPAL', 'status': 'Busy'},
        ]

        # Query 1: Create Cabins
        cabin_query = """
        UNWIND $cabins AS c
        MERGE (n:Cabin {code: c.code})
        SET n.block = c.block,
            n.coordinates = c.coords,
            n.directions = c.dir
        """
        session.run(cabin_query, cabins=cabins)

        # Query 2: Link Faculty to Cabins
        assign_query = """
        UNWIND $assignments AS a
        MATCH (f:Faculty {name: a.name}) 
        MATCH (c:Cabin {code: a.cabin})
        MERGE (f)-[:LOCATED_AT]->(c)
        SET f.current_status = a.status,
            f.status_source = 'Initial Seed',
            f.last_status_updated = datetime()
        """
        session.run(assign_query, assignments=faculty_assignments)

        return {"message": "Map data seeded successfully! 🚀"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ==========================================
# 2. LOCATOR & MAP ENDPOINTS
# ==========================================

@router.get("/faculty/{faculty_id}/location")
def get_faculty_location(faculty_id: str):
    """
    Returns data for the Red Dot Locator: coordinates, directions, and status.
    """
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $fid})
        OPTIONAL MATCH (f)-[:LOCATED_AT]->(c:Cabin)
        RETURN f.name as name, 
               f.current_status as status, 
               f.status_source as source, 
               f.last_status_updated as last_updated,
               c.code as cabin_code,
               c.block as block,
               c.coordinates as coords,
               c.directions as directions
        """
        result = session.run(query, fid=faculty_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Faculty not found")
        
        # Parse coordinates JSON string back to object
        coords = json.loads(result['coords']) if result['coords'] else None
        
        return {
            "name": result['name'],
            "status": {
                "current": result['status'] or "Available",
                "source": result['source'] or "Manual",
                "last_updated": result['last_updated'].isoformat() if result['last_updated'] else None
            },
            "location": {
                "cabin_code": result['cabin_code'],
                "block": result['block'],
                "directions": result['directions'],
                "coordinates": coords
            }
        }
    finally:
        session.close()


# ==========================================
# 3. AVAILABILITY & CROWDSOURCING
# ==========================================

@router.put("/faculty/{faculty_id}/status")
def update_status(faculty_id: str, update: StatusUpdate):
    """
    Updates status.
    Source can be 'Manual' (Professor) or 'Student-QR' (Crowdsourced "I'm at the cabin").
    """
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $fid})
        SET f.current_status = $status,
            f.status_source = $source,
            f.last_status_updated = datetime()
        RETURN f.name as name
        """
        result = session.run(query, fid=faculty_id, status=update.status, source=update.source).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Faculty not found")
            
        return {"message": f"Status updated to {update.status} via {update.source}"}
    finally:
        session.close()

@router.post("/faculty/{faculty_id}/request-update")
def request_update(faculty_id: str):
    """
    Spam Protection Logic:
    Increments a counter. Notification is only sent if count reaches 3.
    """
    session = db.get_session()
    try:
        # 1. Increment Count
        query = """
        MATCH (f:Faculty {user_id: $fid})
        SET f.request_count = coalesce(f.request_count, 0) + 1
        RETURN f.request_count as count, f.name as name, f.user_id as uid
        """
        result = session.run(query, fid=faculty_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Faculty not found")
            
        count = result['count']
        name = result['name']
        uid = result['uid']
        
        response_msg = "Request counted. Waiting for more students."
        
        # 2. Check Threshold (3 Requests)
        if count >= 3:
            # --- REAL NOTIFICATION LOGIC ---
            print(f"🚨 ALERT: 3 students are looking for Prof. {name}! Sending notification...")
            
            # Send the notification to Neo4j
            session.write_transaction(
                create_system_notification, 
                uid, 
                "⚠️ 3+ Students are requesting your status update.", 
                "ALERT"
            )
            
            response_msg = f"Notification sent to Prof. {name}!"
            
            # 3. Reset Count
            session.run("MATCH (f:Faculty {user_id: $fid}) SET f.request_count = 0", fid=faculty_id)
            count = 0 
            
        return {"message": response_msg, "current_requests": count}
    finally:
        session.close()


# ==========================================
# 4. FUTURE AVAILABILITY CHECKER
# ==========================================

@router.post("/faculty/{faculty_id}/future")
def check_future_availability(faculty_id: str, check: FutureCheck):
    """
    Checks the MOCK_TIMETABLE for conflicts at a specific future date/time.
    """
    try:
        # 1. Parse Input Date
        dt = datetime.fromisoformat(check.datetime)
        day_name = dt.strftime("%A")  # e.g., 'Monday'
        time_str = dt.strftime("%H:%M") # e.g., '14:30'

        status = "Available"
        message = "Free according to timetable"

        # 2. Check against Mock Timetable
        for slot in MOCK_TIMETABLE:
            if slot['day'] == day_name:
                if slot['start'] <= time_str < slot['end']:
                    status = "Busy"
                    message = slot['activity'] # e.g., "Class (CS302)"
                    break
        
        return {
            "query_time": f"{day_name}, {time_str}",
            "status": status,
            "message": message
        }
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid Date Format. Use ISO (YYYY-MM-DDTHH:MM:SS)")