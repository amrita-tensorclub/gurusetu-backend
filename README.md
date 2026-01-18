

# GuruSetu Backend API 🚀

> **The AI-powered engine behind GuruSetu: Bridging the gap between Student Potential and Faculty Innovation.**

## 📖 Overview

This repository houses the server-side logic for **GuruSetu**, an academic talent marketplace. It leverages **Graph RAG (Retrieval-Augmented Generation)**, **Vector Embeddings**, and **Knowledge Graphs** to automate mentor-mentee matching. Unlike traditional keyword search, this backend understands the *semantic context* of research skills to connect students with the right professors.

## 🏗 Architecture

The backend is built on a **FastAPI** micro-framework architecture designed for high concurrency and low latency.

* **Core API:** Handles HTTP requests, authentication, and routing.
* **AI Services:** Dedicated modules for generating embeddings and running RAG queries.
* **Data Layer:** Hybrid approach using **PostgreSQL** (for relational data) and **Neo4j** (for the Knowledge Graph).

## 🛠 Tech Stack

* **Framework:** FastAPI (Python)
* **Database:** PostgreSQL (User/Project Data), Neo4j (Graph Connections)
* **AI/ML:** Sentence Transformers (`all-MiniLM-L6-v2`), LangChain (RAG)
* **Authentication:** OAuth2 with JWT Bearer
* **Deployment:** Uvicorn / Gunicorn

---

## 📂 Project Structure

```bash
backend/
├── app/
│   ├── core/              # Config, DB connections, Security protocols
│   ├── models/            # Pydantic models & DB Schemas (Auth, Projects, Openings)
│   ├── routers/           # API Endpoints (Faculty, Student, Dashboard, Recommendations)
│   ├── services/          # Business Logic & AI Engines
│   │   ├── embedding.py   # Vector embedding generation
│   │   ├── graph_service.py # Neo4j Knowledge Graph interactions
│   │   ├── rag_service.py # RAG pipeline for context-aware queries
│   │   └── auth_service.py # User authentication logic
│   └── main.py            # Application entry point
├── scripts/               # Database migration & utility scripts
├── uploads/               # Static file storage for resumes/docs
└── requirements.txt       # Python dependencies

```

---

## ⚡ Key Features & Services

### 1. Intelligent Matching Engine (`/services/embedding.py`)

Automatically converts student profiles and faculty research descriptions into high-dimensional vectors using **Sentence Transformers**.

* **Algorithm:** Cosine Similarity
* **Outcome:** Matches "Deep Learning" with "Neural Networks" even if exact keywords differ.

### 2. Graph RAG Service (`/services/rag_service.py`)

Combines vector search with graph traversal. It retrieves context from the **Neo4j** knowledge graph to answer queries like *"Who is the best student for a Computer Vision project who also knows PyTorch?"*

### 3. Knowledge Graph Integration (`/services/graph_service.py`)

Maintains dynamic nodes and relationships:

* `(Student)-[:HAS_SKILL]->(Skill)`
* `(Faculty)-[:PUBLISHED]->(Paper)`
* `(Paper)-[:RELATED_TO]->(Topic)`

---

## 🚀 Getting Started

### Prerequisites

* Python 3.9+
* Neo4j Database (Local or AuraDB)
* PostgreSQL

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/gurusetu-backend.git
cd gurusetu-backend

```


2. **Create a Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```


3. **Install Dependencies:**
```bash
pip install -r requirements.txt

```


4. **Environment Configuration:**
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost/gurusetu
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256

```



### Running the Server

Start the development server with hot-reload enabled:

```bash
uvicorn app.main:app --reload

```

The API will be available at `http://localhost:8000`.

---

## 📚 API Documentation

FastAPI automatically generates interactive API documentation.

* **Swagger UI:** Visit `http://localhost:8000/docs` to test endpoints.
* **ReDoc:** Visit `http://localhost:8000/redoc` for alternative documentation.

### Key Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/auth/login` | Authenticate user & return JWT |
| `GET` | `/dashboard/faculty` | Get faculty dashboard stats |
| `GET` | `/recommendations/match` | **(AI)** Get top student matches for a project |
| `POST` | `/projects/create` | Create a new research opening |

---

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Built with ❤️ by Team GuruSetu*
