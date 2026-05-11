# Enterprise Data Fabric MCP Server

A production-grade Model Context Protocol (MCP) server providing secure access to enterprise data sources. This server implements three powerful tools for querying databases, searching policies, and fetching tickets from external APIs.

**Status:** Production Ready | **Latest Version:** 1.0.0

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Server](#running-the-server)
6. [Tools Reference](#tools-reference)
7. [Sample Queries](#sample-queries)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [License](#license)

---

## Features

### Tool 1: Query Read-Only Database
- **Secure SQL execution** on PostgreSQL or SQLite
- **SQL Injection Protection**: Only SELECT queries allowed (INSERT/UPDATE/DELETE/DROP/ALTER rejected)
- Real-time query results returned as clean JSON
- Automatic error handling for connection failures and syntax errors
- Supports both SQLite (development) and PostgreSQL (production)

### Tool 2: Semantic Knowledge Search
- **Vector-based semantic search** using ChromaDB
- Search enterprise policies, documentation, and knowledge bases
- Find conceptually similar documents (not just keyword matches)
- Configurable result count and metadata filtering
- Local persistent storage at `./chroma_db`

### Tool 3: Fetch Live Tickets
- **External REST API integration** for ticket systems (JIRA, Linear, Zendesk, etc.)
- Graceful error handling for 404s, 5xx errors, timeouts
- Real-time ticket status, assignee, priority, and metadata
- Configurable API endpoints and authentication tokens
- Default mock server included for testing

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Claude or MCP Client                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   FastMCP Server (stdio transport)       │
├─────────────────────────────────────────┤
│ ├─ query_read_only_database (SQLite/PG) │
│ ├─ semantic_knowledge_search (ChromaDB)  │
│ └─ fetch_live_ticket (REST API)          │
└──────────┬──────────────────────────────┘
           │
      ┌────┴────┬──────────┬──────────┐
      ▼         ▼          ▼          ▼
   SQLite   ChromaDB   Mock API   PostgreSQL
   (Dev)     (Local)   (Test)     (Production)
```

---

## Installation

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Step 1: Clone & Setup Environment

```bash
# Navigate to project directory
cd mcp-server-1

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install python-dotenv psycopg2-binary chromadb httpx flask mcp
```

**Package Details:**
- `mcp` - Model Context Protocol framework
- `python-dotenv` - Environment variable management
- `httpx` - HTTP client for REST API calls
- `chromadb` - Vector database for semantic search
- `psycopg2-binary` - PostgreSQL adapter
- `flask` - Mock API server

### Step 3: Create Test Data

```bash
python setup_dummy_data.py
```

This creates:
- SQLite database (`enterprise.db`) with sample data
- Mock ticket JSON (`mock_tickets.json`)
- ChromaDB collection (optional)

---

## Configuration

### Environment Variables (`.env` file)

```bash
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# For SQLite (development/testing):
DATABASE_URL=sqlite:///enterprise.db

# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost:5432/enterprise_db

# ============================================================================
# TICKET API CONFIGURATION
# ============================================================================

# Local mock API server (testing):
TICKET_API_BASE=http://localhost:5000/v1

# Production API:
# TICKET_API_BASE=https://api.example-company.com/v1
# TICKET_API_TOKEN=your_api_token_here
```

---

## Running the Server

### Option 1: Development Mode (3 Terminals)

**Terminal 1 - Start Mock API Server:**
```bash
python mock_api_server.py
```
Output:
```
2026-05-11 15:27:45,044 - INFO - STARTING MOCK TICKET API SERVER
2026-05-11 15:27:45,044 - INFO - Available endpoints:
2026-05-11 15:27:45,044 - INFO -   GET  http://localhost:5000/v1/tickets/<ticket_id>
2026-05-11 15:27:45,044 - INFO - Server running on http://localhost:5000
```

**Terminal 2 - Start MCP Server:**
```bash
python main.py
```
The server runs on stdio transport, ready to receive MCP requests.

**Terminal 3 - Test the Server:**
```bash
curl http://localhost:5000/v1/tickets/ENG-104
```

### Option 2: Production Mode

```bash
# With Claude Desktop - add to claude_desktop_config.json:
{
  "mcpServers": {
    "enterprise-data-fabric": {
      "command": "python",
      "args": ["/path/to/main.py"]
    }
  }
}
```

---

## Tools Reference

### Tool 1: `query_read_only_database`

**Purpose:** Execute SELECT queries against SQLite or PostgreSQL

**Parameters:**
- `sql_query` (string): SELECT SQL query (required)

**Returns:**
```json
{
  "success": true,
  "database_type": "sqlite",
  "data": [
    {"id": 1, "email": "alice@company.com", "name": "Alice Johnson"},
    {"id": 2, "email": "bob@company.com", "name": "Bob Smith"}
  ],
  "row_count": 2
}
```

**Security:**
- Only SELECT queries allowed
- INSERT, UPDATE, DELETE, DROP, ALTER queries rejected
- Regex validation on all queries

**Example Queries:**
```sql
SELECT * FROM users LIMIT 5;
SELECT id, email FROM users WHERE department = 'Engineering';
SELECT COUNT(*) as total FROM transactions WHERE status = 'completed';
SELECT * FROM policies WHERE category = 'HR';
```

---

### Tool 2: `semantic_knowledge_search`

**Purpose:** Search enterprise knowledge base using semantic similarity

**Parameters:**
- `query` (string): Search query (e.g., "remote work policy")
- `n_results` (int, optional): Number of results to return (default: 3)

**Returns:**
```json
{
  "success": true,
  "query": "remote work policy",
  "count": 3,
  "results": [
    {
      "text": "Our remote work policy allows employees...",
      "metadata": {"category": "HR", "type": "work arrangement"},
      "distance": 0.15
    }
  ]
}
```

**Example Searches:**
- "How do we handle customer data?"
- "Remote work approval process"
- "API rate limits"
- "Incident response procedure"

---

### Tool 3: `fetch_live_ticket`

**Purpose:** Fetch ticket details from external ticket management system

**Parameters:**
- `ticket_id` (string): Ticket identifier (e.g., "ENG-104")

**Returns:**
```json
{
  "success": true,
  "ticket_id": "ENG-104",
  "status_code": 200,
  "data": {
    "id": "ENG-104",
    "title": "Implement OAuth2 authentication",
    "status": "in_progress",
    "priority": "high",
    "assignee": "Alice Johnson"
  }
}
```

**Error Handling:**
- ✅ 404: Ticket not found
- ✅ 5xx: API offline
- ✅ Timeout: Request too slow
- ✅ Connection refused: API unreachable

**Test Tickets:**
```
ENG-104   - OAuth2 authentication (high priority)
BUG-2389  - Memory leak fix (critical)
INFRA-15  - Kubernetes upgrade (medium)
FEATURE-89 - Dark mode dashboard (low)
SUPPORT-445 - Customer API downtime (high)
```

---

## Sample Queries

### Database Queries

**1. Get all active users:**
```sql
SELECT * FROM users WHERE active = true;
```

**2. Count transactions by type:**
```sql
SELECT type, COUNT(*) as count, SUM(amount) as total 
FROM transactions 
GROUP BY type;
```

**3. Get HR policies:**
```sql
SELECT id, name, description FROM policies WHERE category = 'HR';
```

**4. Find pending expenses:**
```sql
SELECT u.name, t.amount, t.date 
FROM transactions t 
JOIN users u ON t.user_id = u.id 
WHERE t.type = 'expense' AND t.status = 'pending';
```

### Insert Sample Data

```sql
-- Add new user
INSERT INTO users (email, name, department, role, active) 
VALUES ('frank@company.com', 'Frank Chen', 'Product', 'Product Manager', 1);

-- Add new transaction
INSERT INTO transactions (user_id, amount, type, date, status) 
VALUES (1, 500.00, 'bonus', '2026-05-11', 'pending');

-- Add new policy
INSERT INTO policies (name, description, category, created_date, last_updated) 
VALUES ('Work from Anywhere', 'Employees can work from any location with internet', 'HR', '2026-05-01', '2026-05-11');
```

### Ticket Queries

```bash
# Fetch single ticket
curl http://localhost:5000/v1/tickets/ENG-104

# List all tickets
curl http://localhost:5000/v1/tickets

# Filter by status
curl "http://localhost:5000/v1/tickets?status=in_progress"

# Health check
curl http://localhost:5000/v1/health
```

---

## Testing

### Unit Testing with cURL

```bash
# Test 1: Database query
curl -X POST http://localhost:5000/v1/tickets/ENG-104 \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users LIMIT 3"}'

# Test 2: Fetch existing ticket
curl http://localhost:5000/v1/tickets/ENG-104

# Test 3: Fetch non-existent ticket (404)
curl http://localhost:5000/v1/tickets/INVALID-999

# Test 4: Health check
curl http://localhost:5000/v1/health
```

### Integration Testing

```bash
# Start all servers
terminal1: python mock_api_server.py
terminal2: python main.py

# Run MCP client tests
# (Use Claude Desktop or custom MCP client)
```

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    role TEXT,
    active BOOLEAN
);SUCCESSFUL QUERIES
```

### Transactions Table
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    amount REAL,
    type TEXT,
    date TEXT,
    status TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

### Policies Table
```sql
CREATE TABLE policies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    created_date TEXT,
    last_updated TEXT
);
```

---

## 🌐 API Endpoints (Mock Server)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/tickets/<ticket_id>` | Fetch single ticket |
| GET | `/v1/tickets` | List all tickets |
| GET | `/v1/tickets?status=X` | Filter by status |
| POST | `/v1/tickets` | Create new ticket |
| GET | `/v1/health` | Health check |

---

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Cloud Deployment (Azure, AWS, GCP)

1. Build Docker image
2. Push to container registry
3. Deploy as serverless function or container service
4. Configure environment variables
5. Enable firewall rules for API access

---

## 📂 Project Structure

```
mcp-server-1/
├── main.py                    # Main MCP server with 3 tools
├── mock_api_server.py         # Flask mock ticket API
├── setup_dummy_data.py        # Initialize test data
├── .env                       # Environment configuration
├── .gitignore                 # Git ignore file
├── enterprise.db              # SQLite database (generated)
├── mBLOCKED QUERIES (Security Feature)data (generated)
├── chroma_db/                 # ChromaDB storage (generated)
├── README.md                  # Th file
├── requirements.txt           # Python dependencies
└── LICENSE                    # License file
```

---

## 📋 Requirements

See `requirements.txt`:

```
mcp==0.1.0
python-dotenv==1.2.2
psycopg2-binary==2.9.12
chromadb==1.5.9
httpx==0.28.1
flask==3.0.0
```

---

## 🔐 Security Considerations

### ✅ Implemented
- SQL injection protection (SELECT-only queries)
- Input validation on all parameter
- Error messages don't expose sensitive data
- Database connection strings from environment
- Timeout protection for external API calls
- HTTPS-ready for production deployment

### ⚠️ Before Production
1. Use strong PostgreSQL passwords
2. Enable HTTPS/TLS for API endpoints
3. Implement rate limiting
4. Add authentication/authorization
5. Rotate API tokens regularly
6. Monitor and log all queries
7. Set up backup strategy for datase
8. Use secrets management (AWS Secrets Manager, etc.)

---

## 🐛 Troubleshooting

### Issue: "DATABASE_URL environment variable not set"
**Solution:** Create `.env` file with `DATABASE_URL=sqlite:///enterprise.db`

### Issue: "Failed to connect to the ticket API"
**Solution:** Ensure `python mock_api_server.py` is running on port 5000

### Issue: "chromadb library not italled"
**Solution:** Run `pip install chromadb`

### Issue: ChromaDB downloading large models
**Solution:** Models are cached in `~/.cache/chroma/`. First run takes 1-2 minutes.

### Issue: "Query rejected" error
**Solution:** Only SELECT queries are allowed. Use `SELECT` instead of `INSERT`, `UPDATE`, `DELETE`, etc.

---

## 📚 Example Workflows

### Workflow 1: Find HR Policy and Create Action Item

```
Successful: SELECT queries work perfectly
Successful: JOINs work perfectly
Successful: GROUP BY works perfectly
Blocked: INSERT queries rejected
Blocked: UPDATE queries rejected
Blocked: DELETE queries rejected
Blocked: DROP queries rejected
Blocked: ALTER queries rejected


```
1. User: "Fetch ticket ENG-104"
2. Tool: fetch_live_ticket("ENG-104")
3. Server: Returns ticket with assignee "Alice Johnson"
4. User: "Show me Alice's pending transactions"
5. Tool: query_read_only_database(
     "SELECT * FROM transactions WHERE user_id IN 
      (SELECT id FROM users WHERE name = 'Alice Johnson') 
      AND status = 'pending'"
   )
6. Server: Returns pending transactions
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📧 Support

For issues, questions, or suggestions:
- O an GitHub Issue
- Create a Discussion
- Contact: utkarshgaur@company.com

---

## 🎯 Roadmap

- [ ] Add Python type hints
- [ ] Implement query result caching
- [ ] Add Prometheus metrics
- [ ] Support for MongoDB
- [ ] GraphQL support
- [ ] Rate limiting middleware
- [ ] Database connection pooling
- [ ] Multi-tenant support

---

**Made with ❤️ for Enterprise Data Integration**

Last Updated: May 11, 2026
