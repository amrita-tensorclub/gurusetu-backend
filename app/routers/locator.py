from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import db
from app.core.security import get_current_user
import uuid
import json
from datetime import datetime

router = APIRouter(tags=["Locator"])

# ==========================================
# 0. MODELS & DATA
# ==========================================

class StatusUpdate(BaseModel):
    status: str       # "Available", "Busy", "In Class", "Away"
    source: str       # "Manual", "Student-QR"

class FutureCheck(BaseModel):
    datetime: str     # ISO Format: "2024-03-25T14:30:00.000Z"

# Mock Timetable (Fallback when DB is empty)
MOCK_TIMETABLE = [
    { "day": 'Monday', "start": '09:00', "end": '10:00', "activity": 'Class (CS302)' },
    { "day": 'Monday', "start": '14:00', "end": '16:00', "activity": 'Lab (CS304)' },
    { "day": 'Tuesday', "start": '11:00', "end": '12:00', "activity": 'Office Hours' },
    { "day": 'Wednesday', "start": '09:00', "end": '10:00', "activity": 'Class (CS302)' },
    { "day": 'Friday', "start": '10:00', "end": '11:00', "activity": 'Dept Meeting' },
]

# --- Helper: Notification ---
def create_system_notification(tx, target_uid, message, type="ALERT"):
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
    tx.run(query, uid=target_uid, nid=str(uuid.uuid4()), message=message, type=type)

# ==========================================
# 1. SEEDING (Run once to setup Map)
# ==========================================
@router.post("/seed")
def seed_locator_data():
    session = db.get_session()
    try:
        # 1. Clean up old connections to prevent duplicates
        session.run("MATCH (f:Faculty)-[r:LOCATED_AT]->() DELETE r")

        # 2. Define Data
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

        # 3. Create Nodes
        session.run("""
        UNWIND $cabins AS c
        MERGE (n:Cabin {code: c.code})
        SET n.block = c.block, n.coordinates = c.coords, n.directions = c.dir
        """, cabins=cabins)

        # 4. Link & Update Status
        session.run("""
        UNWIND $assignments AS a
        MATCH (f:Faculty {name: a.name}) 
        MATCH (c:Cabin {code: a.cabin})
        MERGE (f)-[:LOCATED_AT]->(c)
        SET f.current_status = a.status,
            f.status_source = 'Initial Seed',
            f.last_status_updated = datetime()
        """, assignments=faculty_assignments)

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
        
        # Edge Case: Handle Missing/Bad JSON Coordinates
        coords = None
        if result['coords']:
            try:
                coords = json.loads(result['coords'])
            except json.JSONDecodeError:
                print(f"❌ Error decoding coords for {result['name']}")
                coords = None 
        
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
def update_status(faculty_id: str, update: StatusUpdate, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        # Check permissions handled by `get_current_user` mostly, but logic:
        # If Manual -> Must be Faculty themselves
        # If Student-QR -> Must be Student at location
        
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
            
        return {"message": f"Status updated to {update.status}"}
    finally:
        session.close()

@router.post("/faculty/{faculty_id}/request-update")
def request_update(faculty_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fixed: Now requires Login (current_user) so random people can't spam.
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
        target_uid = result['uid']
        
        response_msg = "Request counted. Waiting for more students."
        
        # 2. Check Threshold (3 Requests)
        if count >= 3:
            print(f"🚨 ALERT: 3 students are looking for Prof. {name}!")
            
            # Send notification
            session.write_transaction(
                create_system_notification, 
                target_uid, 
                f"⚠️ 3+ Students are at your cabin requesting an update.", 
                "ALERT"
            )
            
            response_msg = f"Notification sent to Prof. {name}!"
            
            # Reset Count
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
    try:
        # 1. Edge Case Fix: Remove 'Z' (UTC marker) to prevent Python crash
        clean_date = check.datetime.replace("Z", "")
        
        dt = datetime.fromisoformat(clean_date)
        day_name = dt.strftime("%A")   # e.g., 'Monday'
        time_str = dt.strftime("%H:%M") # e.g., '14:30'

        status = "Available"
        message = "Free according to timetable"
        found_conflict = False

        # 2. Priority 1: Check against Mock Timetable (Specific Events)
        for slot in MOCK_TIMETABLE:
            if slot['day'] == day_name:
                # String comparison works for ISO times: "09:00" <= "14:30" < "16:00"
                if slot['start'] <= time_str < slot['end']:
                    status = "In Class"  # Or "Busy"
                    message = slot['activity']
                    found_conflict = True
                    break
        
        # 3. Priority 2: General Availability (Only if NO Class was found)
        # If they are free from class, check if they are actually at home (Weekend/After Hours)
        if not found_conflict:
            # Fix: Use 'in list' instead of 'or string'
            if day_name in ['Saturday', 'Sunday']:
                status = "Busy"
                message = "At Home (Weekend)"
            
            # Fix: Check office hours (e.g., 9 AM to 4 PM)
            elif time_str < "09:00" or time_str > "16:00":
                status = "Busy"
                message = "At Home (After Hours)"

        return {
            "query_time": f"{day_name}, {time_str}",
            "status": status,
            "message": message
        }

    except ValueError as e:
         print(f"Date Error: {e}")
         raise HTTPException(status_code=400, detail="Invalid Date Format. Use ISO (YYYY-MM-DDTHH:MM:SS)")