"""
Setup script to create dummy data for the Enterprise Data Fabric MCP Server.
This creates:
1. SQLite database with sample enterprise data
2. Mock ticket data (used by the API server)
3. ChromaDB collection (optional - takes time on first run)
"""

import sqlite3
import json
import os
from pathlib import Path

# ============================================================================
# 1. SETUP SQLITE DATABASE WITH DUMMY DATA
# ============================================================================

def setup_sqlite_database():
    """Create SQLite database with enterprise tables and sample data."""
    
    db_path = "enterprise.db"
    
    # Remove existing database if it exists (for fresh start)
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Removed existing {db_path}")
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create Users table
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            role TEXT,
            active BOOLEAN
        )
    """)
    
    # Create Transactions table
    cur.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            date TEXT,
            status TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    # Create Enterprise Policies table
    cur.execute("""
        CREATE TABLE policies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_date TEXT,
            last_updated TEXT
        )
    """)
    
    # Insert sample users
    users = [
        (1, "alice@company.com", "Alice Johnson", "Engineering", "Senior Engineer", True),
        (2, "bob@company.com", "Bob Smith", "Sales", "Sales Manager", True),
        (3, "carol@company.com", "Carol Davis", "HR", "HR Manager", True),
        (4, "david@company.com", "David Wilson", "Finance", "Financial Analyst", False),
        (5, "eve@company.com", "Eve Martinez", "Engineering", "DevOps Engineer", True),
    ]
    
    cur.executemany("""
        INSERT INTO users (id, email, name, department, role, active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, users)
    
    # Insert sample transactions
    transactions = [
        (1, 1, 1500.00, "salary", "2026-05-01", "completed"),
        (2, 1, 250.00, "expense", "2026-05-02", "completed"),
        (3, 2, 2000.00, "salary", "2026-05-01", "completed"),
        (4, 3, 1800.00, "salary", "2026-05-01", "completed"),
        (5, 5, 1600.00, "salary", "2026-05-01", "completed"),
        (6, 1, 75.50, "expense", "2026-05-03", "pending"),
    ]
    
    cur.executemany("""
        INSERT INTO transactions (id, user_id, amount, type, date, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, transactions)
    
    # Insert sample policies
    policies = [
        (1, "Remote Work Policy", "Employees in Engineering and Sales can work from home up to 3 days per week.", "HR", "2025-01-15", "2026-04-01"),
        (2, "Data Retention Policy", "All customer data must be retained for minimum 7 years. Personal data is deleted after 3 years of inactivity.", "Legal", "2025-03-20", "2026-02-15"),
        (3, "API Rate Limiting", "Standard API rate limit is 1000 requests per hour. Enterprise accounts get 10000/hour.", "Technical", "2025-06-10", "2026-01-10"),
        (4, "Vacation Policy", "Employees get 20 days vacation per year plus 10 public holidays.", "HR", "2024-12-01", "2025-11-01"),
        (5, "Security Incident Response", "All security incidents must be reported within 24 hours to the security team.", "Security", "2025-02-01", "2026-03-15"),
    ]
    
    cur.executemany("""
        INSERT INTO policies (id, name, description, category, created_date, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, policies)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created SQLite database: {db_path}")
    print(f"  - 5 users in the users table")
    print(f"  - 6 transactions in the transactions table")
    print(f"  - 5 enterprise policies in the policies table")


# ============================================================================
# 2. SETUP CHROMADB WITH SAMPLE POLICIES (Optional)
# ============================================================================

def setup_chromadb():
    """Populate ChromaDB with enterprise policy documents."""
    
    try:
        import chromadb
    except ImportError:
        print("⚠ ChromaDB not installed. Skipping ChromaDB setup.")
        return
    
    print("\n⏳ Setting up ChromaDB (this downloads embedding models on first run)...")
    
    # Create persistent ChromaDB client
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # Get or create collection
    collection = client.get_or_create_collection(name="enterprise_policies")
    
    # Clear existing data if any
    try:
        ids = collection.get()["ids"]
        if ids:
            collection.delete(ids=ids)
    except:
        pass
    
    # Sample policy documents
    documents = [
        "Our remote work policy allows employees in Engineering and Sales to work from home up to 3 days per week. All employees must attend office on Wednesdays for team meetings. Core hours are 10 AM to 3 PM.",
        "Data retention policy: Customer data must be retained for minimum 7 years for compliance. Personal data is deleted after 3 years of inactivity. Sensitive data is encrypted at rest and in transit.",
        "API rate limiting: Standard API rate limit is 1000 requests per hour per API key. Enterprise accounts receive 10000 requests per hour. Additional quotas require VP approval.",
        "Vacation policy: Employees receive 20 days vacation per year plus 10 public holidays. Vacation must be planned 2 weeks in advance. Maximum consecutive vacation is 2 weeks.",
        "Security incident response: All security incidents must be reported within 24 hours to security@company.com. Critical incidents require executive notification within 1 hour.",
        "Cloud infrastructure policy: All production workloads must run on AWS with multi-region redundancy. Development and staging can use single region. DR recovery time objective is 4 hours.",
        "Code review policy: All code changes must be reviewed by at least 2 engineers before merging. PRs require passing automated tests. Merge requires approval from team lead or tech lead.",
    ]
    
    # Metadata for each document
    metadatas = [
        {"category": "HR", "type": "work arrangement", "version": "2.1"},
        {"category": "Legal", "type": "compliance", "version": "3.0"},
        {"category": "Technical", "type": "API", "version": "1.2"},
        {"category": "HR", "type": "benefits", "version": "2.0"},
        {"category": "Security", "type": "incident response", "version": "1.1"},
        {"category": "Technical", "type": "infrastructure", "version": "2.3"},
        {"category": "Engineering", "type": "development", "version": "1.5"},
    ]
    
    # Add documents to collection
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=[f"policy_{i}" for i in range(len(documents))]
    )
    
    print(f"✓ Populated ChromaDB collection with {len(documents)} policy documents")


# ============================================================================
# 3. SETUP MOCK TICKET DATA
# ============================================================================

def setup_mock_tickets():
    """Create mock ticket data for the API server."""
    
    tickets_file = "mock_tickets.json"
    
    mock_tickets = {
        "ENG-104": {
            "id": "ENG-104",
            "title": "Implement OAuth2 authentication",
            "description": "Add OAuth2 support to the API for third-party integrations",
            "status": "in_progress",
            "priority": "high",
            "assignee": "Alice Johnson",
            "created_date": "2026-04-15",
            "updated_date": "2026-05-10"
        },
        "BUG-2389": {
            "id": "BUG-2389",
            "title": "Fix memory leak in background worker",
            "description": "Background worker is consuming excessive memory after 24 hours",
            "status": "in_progress",
            "priority": "critical",
            "assignee": "Eve Martinez",
            "created_date": "2026-05-08",
            "updated_date": "2026-05-10"
        },
        "INFRA-15": {
            "id": "INFRA-15",
            "title": "Upgrade Kubernetes cluster to 1.30",
            "description": "Update production Kubernetes cluster from 1.28 to 1.30",
            "status": "planned",
            "priority": "medium",
            "assignee": "Eve Martinez",
            "created_date": "2026-04-20",
            "updated_date": "2026-05-05"
        },
        "FEATURE-89": {
            "id": "FEATURE-89",
            "title": "Add dark mode to dashboard",
            "description": "Implement dark mode theme toggle in the web dashboard",
            "status": "completed",
            "priority": "low",
            "assignee": "Bob Smith",
            "created_date": "2026-04-01",
            "updated_date": "2026-05-09"
        },
        "SUPPORT-445": {
            "id": "SUPPORT-445",
            "title": "Customer reports API downtime",
            "description": "Customer unable to connect to API endpoint for 2 hours yesterday",
            "status": "resolved",
            "priority": "high",
            "assignee": "Carol Davis",
            "created_date": "2026-05-09",
            "updated_date": "2026-05-10"
        },
    }
    
    with open(tickets_file, "w") as f:
        json.dump(mock_tickets, f, indent=2)
    
    print(f"✓ Created mock tickets file: {tickets_file}")
    print(f"  Available tickets: {', '.join(mock_tickets.keys())}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SETTING UP ENTERPRISE DATA FABRIC TEST ENVIRONMENT")
    print("="*70 + "\n")
    
    setup_sqlite_database()
    print()
    setup_mock_tickets()
    print()
    
    # Optional: setup_chromadb()
    # Uncomment the line below if you want to enable semantic search
    # (first run takes 1-2 minutes to download embedding models)
    # setup_chromadb()
    
    print("\n" + "="*70)
    print("✓ SETUP COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Start the mock API server in a separate terminal:")
    print("     python mock_api_server.py")
    print("\n  2. Run the MCP server:")
    print("     python main.py")
    print("\n  3. Test with these sample queries:")
    print("     - SELECT * FROM users LIMIT 5")
    print("     - SELECT * FROM policies")
    print("     - Fetch ticket: ENG-104, BUG-2389, INFRA-15")
    print("\n  (Optional) To enable semantic search, uncomment setup_chromadb() in this script")
    print("="*70 + "\n")

