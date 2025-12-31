from fastapi import APIRouter, HTTPException, Depends
from app.core.database import db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/")
def get_notifications(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    session = db.get_session()
    try:
        # Match notifications linked to the current user (Student OR Faculty)
        query = """
        MATCH (n:Notification)-[:NOTIFIES]->(u:User {user_id: $uid})
        RETURN n.id as id, n.message as message, n.type as type, 
               n.is_read as is_read, n.created_at as date
        ORDER BY n.created_at DESC LIMIT 20
        """
        results = session.run(query, uid=user_id)

        notifs = []
        for r in results:
            notifs.append({
                "id": r["id"],
                "message": r["message"],
                "type": r["type"],
                "is_read": r["is_read"],
                "date": r["date"].isoformat() if r["date"] else ""
            })
        return notifs
    finally:
        session.close()


@router.put("/{notif_id}/read")
def mark_notification_read(notif_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = """
        MATCH (n:Notification {id: $nid})-[:NOTIFIES]->(u:User {user_id: $uid}) 
        SET n.is_read = true
        """
        session.run(query, nid=notif_id, uid=current_user["user_id"])
        return {"message": "Marked as read"}
    finally:
        session.close()


@router.put("/read-all")
def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read for the current user."""
    session = db.get_session()
    try:
        query = """
        MATCH (n:Notification)-[:NOTIFIES]->(u:User {user_id: $uid})
        WHERE n.is_read = false
        SET n.is_read = true
        RETURN count(n) AS marked_count
        """
        result = session.run(query, uid=current_user["user_id"]).single()
        count = result["marked_count"] if result else 0
        return {"message": f"Marked {count} notifications as read"}
    finally:
        session.close()
