# Guru Setu Backend API

## Overview

Guru Setu is a FastAPI-based backend platform that connects students and faculty in engineering colleges through ML-powered recommendations. Built on a Neo4j graph database, it enables intelligent matching based on skills, interests, research areas, and project experience. The system facilitates cross-departmental collaboration, research opportunity discovery, and streamlined application tracking.

## Core Architecture

### Technology Stack

- **Framework**: FastAPI 0.109.0
- **Database**: Neo4j 5.16 (Graph Database)
- **Authentication**: JWT tokens with bcrypt password hashing
- **ML/Embeddings**: Sentence Transformers (384-dim vectors for future semantic search)
- **Python Version**: 3.11+

### Graph Data Model

**Core Node Types**:

- `User` (dual-labeled as `:User:Student` or `:User:Faculty`)
- `Opening` - Research/project opportunities posted by faculty
- `Concept` - Normalized skills, interests, and domains (lowercase)
- `Work` (dual-labeled as `:Work:Project` or `:Work:Publication`)
- `Notification` - System notifications for users

**Critical Relationships**:

```cypher
(Student)-[:HAS_SKILL]->(Concept)           # Technical skills
(Student)-[:INTERESTED_IN]->(Concept)       # Research interests
(Faculty)-[:INTERESTED_IN]->(Concept)       # Faculty expertise
(Faculty)-[:POSTED]->(Opening)              # Research openings
(Opening)-[:REQUIRES]->(Concept)            # Required skills
(Student)-[:APPLIED_TO {status, applied_at}]->(Opening)  # Applications
(Student)-[:WORKED_ON|COMPLETED]->(Work)    # Student projects
(Faculty)-[:LED_PROJECT|PUBLISHED]->(Work)  # Faculty research
(Work)-[:USED_TECH]->(Concept)              # Technologies used
(Notification)-[:NOTIFIES]->(User)          # User notifications
```

## Key Features & Endpoints

### 1. Authentication & Authorization (`/auth`)

**Endpoints**:

- `POST /auth/register` - Register new user (student/faculty)
  - Input: email, password, name, role, roll_no/employee_id
  - Creates User node with role-based labeling
  
- `POST /auth/login` - JWT token generation
  - Returns: `{access_token, token_type: "bearer"}`
  - Token payload: `{sub: user_id, role: student|faculty, exp: timestamp}`

**Security**:

- Bcrypt password hashing
- JWT tokens required for all protected endpoints
- Role-based access control (RBAC) enforced via `get_current_user()` dependency

### 2. Profile Management (`/users`)

**Student Profile**:

- `GET /users/student/profile/{user_id}` - Fetch student profile with skills, interests, projects, publications
- `PUT /users/student/profile` - Update profile (replaces old skills/interests/projects)
  - Fields: name, phone, department, batch, bio, skills[], interests[], projects[], publications[]
  - Uses `FOREACH` loops to create new relationships
  
**Faculty Profile**:

- `PUT /users/faculty/profile` - Update faculty profile
  - Fields: name, designation, department, office_hours, cabin details (block/floor/number), ug_details[], pg_details[], phd_details[], domain_interests[], previous_work[]

**File Upload**:

- `POST /users/upload-profile-picture` - Upload profile images
  - Stores in `uploads/` directory
  - Returns URL: `http://localhost:8000/uploads/{uuid}.{ext}`

### 3. ML-Powered Recommendations (`/recommend`)

All recommendations use **graph traversal** with match score calculation:

**For Faculty**:

- `GET /recommend/faculty/students` - General student recommendations
  - Formula: `(Shared Skills / Faculty Interests) × 100`
  - Returns: student_id, name, dept, batch, pic, match_score, common_concepts
  
- `GET /recommend/openings/{opening_id}/students` - Candidates for specific opening
  - Formula: `(Matched Skills / Required Skills) × 100`
  - Filters by CGPA threshold and target years

**For Students**:

- `GET /recommend/student/mentors` - Faculty mentor recommendations
  - Logic: Count of shared research interests
  - Returns: faculty_id, name, designation, pic, score, common_concepts
  
- `GET /recommend/student/openings` - Recommended research openings
  - Formula with recency boost:

    ```
    Base Score = (Matched Skills / Total Required) × 100
    Recency Multiplier:
      < 7 days: 1.3x
      7-30 days: 1.0x
      > 30 days: 0.8x
    Final Score = min(Base × Multiplier, 100)
    ```

  - Automatically excludes already-applied openings
  - Returns: opening_id, title, faculty_id, faculty_name, faculty_dept, faculty_pic, skills, match_score

### 4. Opening Management (`/openings`)

**Faculty Operations**:

- `POST /openings/` - Create research/project opening
  - Input: title, description, required_skills[], expected_duration, target_years[], min_cgpa, deadline
  - Creates Opening node with `:REQUIRES` relationships to Concept nodes
  - Sets status: 'Active' by default

### 5. Application Tracking (`/applications`)

**Student Operations**:

- `POST /applications/apply/{opening_id}` - Submit application
  - Validates eligibility (CGPA, target year)
  - Prevents duplicate applications
  - Creates `(Student)-[:APPLIED_TO {application_id, status: 'Pending', applied_at}]->(Opening)`
  - Sends notification to faculty

**Faculty Operations**:

- `PUT /applications/status` - Update application status
  - Input: opening_id, student_id, status ('Shortlisted'|'Rejected')
  - Updates relationship status property
  - Creates `:SHORTLISTED` relationship if accepted
  - Sends notification to student

### 6. Dashboard Endpoints (`/dashboard`)

**Faculty Dashboard**:

- `GET /dashboard/faculty/home` - Faculty home screen
  - Returns: user_info, unread_count, recommended_students[], faculty_collaborations[], active_openings[]
  - Supports filtering by skills/department
  
- `GET /dashboard/faculty/menu` - Sidebar navigation data
- `GET /dashboard/faculty/all-students` - Browse all students with filters (search, department, batch)
- `GET /dashboard/faculty/collaborations` - Cross-faculty collaboration opportunities
- `GET /dashboard/faculty/student-profile/{student_id}` - View student public profile
- `GET /dashboard/faculty/projects` - Faculty's posted openings with applicant counts
- `GET /dashboard/faculty/projects/{project_id}/applicants` - View applicants for specific opening
- `GET /dashboard/faculty/projects/{project_id}/shortlisted` - View shortlisted students

**Student Dashboard**:

- `GET /dashboard/student/home` - Student home screen
  - Returns: user_info, unread_count, recommended_openings[], all_openings[]
  - Includes match scores and deadline dates
  
- `GET /dashboard/student/menu` - Sidebar navigation data
- `GET /dashboard/student/all-faculty` - Browse all faculty with filters (search, department, domain)
- `GET /dashboard/student/faculty-profile/{faculty_id}` - View faculty public profile
- `GET /dashboard/student/applications` - Track application status

**Interaction Endpoints**:

- `POST /dashboard/shortlist/{student_id}` - Faculty shortlist student for opening
- `POST /dashboard/express-interest/{project_id}` - Student express interest in project

### 7. Notifications (`/notifications`)

- `GET /notifications/` - Fetch user notifications (last 20, sorted by date)
  - Returns: id, message, type, is_read, date
  
- `PUT /notifications/{notif_id}/read` - Mark notification as read

**Notification Triggers**:

- Student applies to opening → Faculty notified
- Faculty updates application status → Student notified
- Student expresses interest in collaboration → Faculty notified
- Faculty shortlists student → Student notified

### 8. Portfolio Management

**Student Projects** (`/student-projects`):

- `POST /student-projects/` - Add student project/publication
  - Creates `:Work:Project` or `:Work:Publication` node
  - Links via `(Student)-[:COMPLETED|AUTHORED]->(Work)`
  - Creates `(Work)-[:USED_TECH]->(Concept)` for each tool

**Faculty Research** (`/faculty-projects`):

- `POST /faculty-projects/` - Add faculty research work
  - Supports dual types: 'publication' | 'project'
  - Duplicate check by title
  - Creates `(Faculty)-[:PUBLISHED|LED_PROJECT]->(Work)`
  - Optional collaboration_type field for cross-faculty projects
  
- `GET /faculty-projects/my-projects` - List faculty's openings with applicant/shortlisted counts
- `GET /faculty-projects/my-projects/{project_id}/applicants` - View applicants
- `GET /faculty-projects/my-projects/{project_id}/shortlisted` - View shortlisted students

## Development Setup

### Prerequisites

- Python 3.11+
- Neo4j 5.16+ (Community or Enterprise)
- pip package manager

### Installation

1. **Clone Repository**:

```bash
git clone https://github.com/amrita-tensorclub/gurusetu-backend.git
cd gurusetu-backend
```

1. **Install Dependencies**:

```bash
pip install -r requirements.txt
```

1. **Configure Environment**:
Create `.env` file in root directory:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

JWT_SECRET_KEY=your_secure_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Optional
OPENAI_API_KEY=your_openai_key
```

1. **Initialize Database Schema**:

```bash
python -m app.scripts.create_constraints
```

This creates:

- Uniqueness constraints (user_id, email, opening_id, etc.)
- Vector similarity indexes for future semantic search

1. **Run Development Server**:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API docs at: `http://localhost:8000/docs`

### Docker Deployment

**Current Status**: Placeholder files exist (`Dockerfile`, `docker-compose.yml`) but are empty.

**Recommended Production Setup**:

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml** (for local testing):

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - neo4j

  neo4j:
    image: neo4j:5.16-community
    ports:
      - "7474:7474"  # Browser UI
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

**Production Considerations**:

- Use managed Neo4j (Neo4j Aura) for scalability
- Enable HTTPS/TLS: `neo4j+s://` URI scheme
- Reduce token expiry: `ACCESS_TOKEN_EXPIRE_MINUTES=15`
- Add health check endpoint
- Configure CORS properly for frontend domain

## API Design Patterns

### Database Session Management

**Critical Pattern** - Sessions are NOT context managers:

```python
session = db.get_session()
try:
    result = session.run(query, param1=value1)
    return [record.data() for record in result]
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=500, detail="Error message")
finally:
    session.close()  # MUST close in finally block
```

### Concept Normalization

All skills/interests stored as **lowercase** to prevent duplicates:

```cypher
MERGE (c:Concept {name: toLower($skill_name)})
MERGE (user)-[:HAS_SKILL]->(c)
```

### Profile Update Pattern

1. Use `SET` with `COALESCE()` to preserve unmodified fields
2. Delete old relationships: `MATCH (user)-[r:HAS_SKILL]->() DELETE r`
3. Use `FOREACH` loops to create new relationships from arrays

### Parameterized Queries

**Always use parameters** - Never f-strings:

```python
session.run(query, user_id=value)  # ✅ Correct
session.run(f"MATCH (u {{id: '{value}'}})...")  # ❌ SQL injection risk
```

## Testing & Validation

**Verify Database Schema**:

```cypher
SHOW CONSTRAINTS
SHOW INDEXES
```

**Test Auth Flow**:

1. `POST /auth/register` with student/faculty data
2. `POST /auth/login` to get JWT token
3. Include in headers: `Authorization: Bearer <token>`

**Sample Student Registration**:

```json
POST /auth/register
{
  "email": "student@example.com",
  "password": "securepass123",
  "name": "John Doe",
  "role": "student",
  "roll_no": "AM.EN.U4CSE20001"
}
```

**Sample Faculty Login**:

```json
POST /auth/login
{
  "email": "faculty@example.com",
  "password": "securepass123"
}
```

## Troubleshooting

**Neo4j Connection Issues**:

- Verify Neo4j is running: `http://localhost:7474`
- Check credentials in `.env` file
- Ensure Bolt port 7687 is accessible

**Authentication Errors**:

- Verify JWT_SECRET_KEY is set
- Check token expiry (default 60 minutes)
- Ensure Bearer token format: `Authorization: Bearer <token>`

**Duplicate Concept Nodes**:

- Run concept normalization script if old data exists
- Ensure `toLower()` is used in all MERGE operations

## Project Structure

```
gurusetu-backend/
├── app/
│   ├── main.py                 # FastAPI app initialization, CORS, router registration
│   ├── core/
│   │   ├── config.py           # Environment settings (Neo4j, JWT)
│   │   ├── database.py         # Neo4j driver singleton
│   │   └── security.py         # JWT token creation/validation, password hashing
│   ├── models/
│   │   ├── auth.py             # UserRegister, UserLogin, Token
│   │   ├── user.py             # Profile update models
│   │   ├── openings.py         # OpeningCreate
│   │   └── project.py          # StudentWorkCreate (for projects/publications)
│   ├── routers/
│   │   ├── auth.py             # Registration, login
│   │   ├── users.py            # Profile CRUD, file upload
│   │   ├── openings.py         # Create openings
│   │   ├── recommendations.py  # ML-powered matching
│   │   ├── applications.py     # Application submission, status updates
│   │   ├── dashboard.py        # Home screens, lists, public profiles
│   │   ├── notifications.py    # Notification management
│   │   ├── student_projects.py # Student portfolio management
│   │   └── faculty_projects.py # Faculty research management
│   ├── services/
│   │   ├── auth_service.py     # Registration/login business logic
│   │   ├── rag_service.py      # Recommendation algorithms
│   │   ├── graph_service.py    # (Placeholder for future features)
│   │   └── embedding.py        # (Placeholder for vector embeddings)
│   └── scripts/
│       ├── create_constraints.py  # Database schema initialization
│       └── sync_db.py             # (Utility scripts)
├── uploads/                    # User-uploaded files (profile pictures)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in repo)
├── Dockerfile                  # (Empty - needs implementation)
├── docker-compose.yml          # (Empty - needs implementation)
└── README.md                   # This file
```


