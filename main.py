import json
import re
import os
from datetime import datetime
from typing import Optional, Any, Dict, List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the FastMCP server with stdio transport
mcp = FastMCP("Enterprise-Data-Fabric-Server")

# ============================================================================
# TOOL 1: query_read_only_database (PostgreSQL)
# ============================================================================

@mcp.tool()
def query_read_only_database(sql_query: str) -> str:
    """
    Executes a READ-ONLY SQL query against a SQLite or PostgreSQL database and returns results as JSON.
    
    SECURITY NOTICE:
    - Only SELECT queries are permitted. All INSERT, UPDATE, DELETE, DROP, and ALTER 
      queries are automatically rejected to prevent accidental data modification.
    - The query is validated using regex to ensure it only begins with SELECT (case-insensitive).
    
    Database Support:
    - SQLite: If DATABASE_URL is not set, uses local 'enterprise.db' (for testing/development)
    - PostgreSQL: If DATABASE_URL starts with 'postgresql://', connects to remote PostgreSQL server
    
    Args:
        sql_query (str): A SELECT SQL query string. Must start with SELECT (case-insensitive).
                         Do NOT include INSERT, UPDATE, DELETE, DROP, or ALTER operations.
                         Example: "SELECT id, name FROM users WHERE active = true LIMIT 10"
    
    Returns:
        str: A JSON-formatted string containing:
             - "success": bool indicating whether the query executed successfully
             - "data": list of result rows (each row is a dict) if successful
             - "error": error message if the query failed or was rejected
             - "row_count": number of rows returned
             - "database_type": "sqlite" or "postgresql"
    
    Raises:
        Returns error JSON if:
        - Query does not begin with SELECT
        - Database connection fails
        - Query execution fails (syntax error, table not found, etc.)
    
    Examples:
        - "SELECT * FROM policies LIMIT 5"
        - "SELECT id, email FROM users WHERE department = 'Engineering'"
        - "SELECT COUNT(*) as total FROM transactions WHERE status = 'completed'"
    """
    
    # SECURITY CHECK: Validate that query only starts with SELECT
    # This prevents accidental INSERT, UPDATE, DELETE, DROP, ALTER operations
    sql_stripped = sql_query.strip()
    select_pattern = r"^\s*SELECT\s"
    if not re.match(select_pattern, sql_stripped, re.IGNORECASE):
        return json.dumps({
            "success": False,
            "error": "Query rejected. Only SELECT queries are allowed. "
                     "INSERT, UPDATE, DELETE, DROP, and ALTER operations are not permitted."
        })
    
    # Retrieve database connection URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    try:
        # SQLITE PATH (default for testing)
        if not database_url or database_url.startswith("sqlite"):
            db_path = database_url.replace("sqlite:///", "") if database_url else "enterprise.db"
            
            if not os.path.exists(db_path):
                return json.dumps({
                    "success": False,
                    "error": f"SQLite database not found: {db_path}. "
                             "Run setup_dummy_data.py first to create it."
                })
            
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dicts
            cur = conn.cursor()
            
            # Execute query
            cur.execute(sql_query)
            results = cur.fetchall()
            row_count = len(results)
            
            # Convert to list of dicts
            data = [dict(row) for row in results]
            
            cur.close()
            conn.close()
            
            return json.dumps({
                "success": True,
                "database_type": "sqlite",
                "database_path": db_path,
                "data": data,
                "row_count": row_count
            })
        
        # POSTGRESQL PATH
        elif database_url.startswith("postgresql"):
            try:
                import psycopg2
                import psycopg2.extras
            except ImportError:
                return json.dumps({
                    "success": False,
                    "error": "psycopg2 library not installed for PostgreSQL. Run: pip install psycopg2-binary"
                })
            
            conn = psycopg2.connect(database_url)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Execute query
            cur.execute(sql_query)
            results = cur.fetchall()
            row_count = len(results)
            
            # Convert to list of dicts
            data = [dict(row) for row in results]
            
            cur.close()
            conn.close()
            
            return json.dumps({
                "success": True,
                "database_type": "postgresql",
                "data": data,
                "row_count": row_count
            })
        
        else:
            return json.dumps({
                "success": False,
                "error": "DATABASE_URL must start with 'sqlite' or 'postgresql'. "
                         "Example: sqlite:///enterprise.db or postgresql://user:pass@host/db"
            })
    
    except sqlite3.Error as e:
        return json.dumps({
            "success": False,
            "database_type": "sqlite",
            "error": f"SQLite error: {str(e)}"
        })
    except Exception as e:
        error_msg = str(e)
        db_type = "postgresql" if "psycopg2" in str(type(e)) else "unknown"
        return json.dumps({
            "success": False,
            "database_type": db_type,
            "error": f"Database error: {error_msg}"
        })


# ============================================================================
# TOOL 2: semantic_knowledge_search (ChromaDB)
# ============================================================================

@mcp.tool()
def semantic_knowledge_search(query: str, n_results: int = 3) -> str:
    """
    Performs semantic (vector-based) search against an enterprise knowledge base stored in ChromaDB.
    Uses embeddings to find conceptually similar documents, not just keyword matches.
    
    This tool connects to a local persistent ChromaDB instance that stores enterprise policies,
    documentation, and knowledge base articles. Results are ranked by semantic similarity.
    
    Args:
        query (str): The search query describing what information you need.
                     Examples: "remote work policy", "data retention rules", "security requirements"
        n_results (int, optional): Maximum number of matching documents to return. Defaults to 3.
                                   Increase to get more results, decrease for only top matches.
    
    Returns:
        str: A JSON-formatted string containing:
             - "success": bool indicating whether the search executed successfully
             - "results": list of matching documents with:
                 - "text": the document content
                 - "metadata": associated metadata (source, date, category, etc.)
                 - "distance": semantic similarity score (lower is more similar)
             - "query": the original query string
             - "count": number of results returned
             - "error": error message if the search failed
    
    Raises:
        Returns error JSON if:
        - ChromaDB library is not installed
        - ChromaDB connection fails
        - Collection does not exist
        - Query is empty or invalid
    
    Examples:
        - query: "How do we handle customer data?" → finds privacy policies, GDPR docs, etc.
        - query: "Remote work approval process" → finds HR policies and guidelines
        - query: "API rate limits" → finds technical documentation and SLAs
        - query: "What's our incident response procedure?", n_results: 5
    """
    try:
        import chromadb
    except ImportError:
        return json.dumps({
            "success": False,
            "error": "chromadb library not installed. Run: pip install chromadb"
        })
    
    try:
        if not query or not query.strip():
            return json.dumps({
                "success": False,
                "error": "Query string cannot be empty. Please provide a search query."
            })
        
        # Connect to local persistent ChromaDB client
        # Stores data in ./chroma_db directory
        client = chromadb.PersistentClient(path="./chroma_db")
        
        # Get or create the enterprise_policies collection
        collection = client.get_or_create_collection(name="enterprise_policies")
        
        # Perform semantic search using embeddings
        search_results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results for LLM consumption
        formatted_results = []
        if search_results and search_results["documents"]:
            for i, doc_text in enumerate(search_results["documents"][0]):
                result_item = {
                    "text": doc_text,
                    "distance": search_results["distances"][0][i] if search_results["distances"] else None
                }
                # Include metadata if available
                if search_results.get("metadatas") and search_results["metadatas"][0]:
                    result_item["metadata"] = search_results["metadatas"][0][i]
                formatted_results.append(result_item)
        
        return json.dumps({
            "success": True,
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Semantic search failed: {str(e)}. "
                     "Ensure ChromaDB is properly installed and ./chroma_db directory exists."
        })


# ============================================================================
# TOOL 3: fetch_live_ticket (External REST API)
# ============================================================================

@mcp.tool()
def fetch_live_ticket(ticket_id: str) -> str:
    """
    Fetches live ticket details from an external REST API ticket management system.
    Supports enterprise ticketing systems like JIRA, Zendesk, Linear, or custom APIs.
    
    This tool makes HTTP requests to retrieve real-time ticket status, assignee information,
    priority, description, and other metadata. Handles common HTTP errors gracefully.
    
    Args:
        ticket_id (str): The unique identifier of the ticket to fetch.
                         Format typically matches your ticketing system (e.g., "ENG-104", "TICKET-12345").
                         Examples: "ENG-104", "BUG-2389", "INFRA-15"
    
    Returns:
        str: A JSON-formatted string containing:
             - "success": bool indicating whether the request was successful
             - "ticket_id": the requested ticket ID
             - "data": full ticket details (status, assignee, priority, description, etc.)
             - "error": human-readable error message if the request failed
             - "status_code": HTTP status code from the API
    
    Raises:
        Returns error JSON if:
        - Ticket not found (HTTP 404)
        - API server is offline (HTTP 5xx)
        - Invalid ticket ID format
        - Network timeout or connection refused
        - API rate limit exceeded
    
    Error Scenarios:
        - 404: "Ticket not found" - the requested ticket does not exist
        - 5xx: "API offline or experiencing issues" - server-side error
        - Network error: "Failed to connect to API" - connectivity problem
        - Timeout: "Request timed out" - API took too long to respond
    
    Examples:
        - ticket_id: "ENG-104" → returns ticket with status, assignee, priority
        - ticket_id: "BUG-2389" → returns bug report details
        - ticket_id: "INVALID" → returns error if ticket doesn't exist or format is wrong
    
    Notes:
        - Default API Endpoint: http://localhost:5000/v1/tickets/{ticket_id}
        - Configure TICKET_API_BASE env var to change endpoint
        - Uses the HTTPX library for reliable HTTP requests with timeouts
        - Automatically handles redirects and retries for transient failures
    """
    try:
        import httpx
    except ImportError:
        return json.dumps({
            "success": False,
            "ticket_id": ticket_id,
            "error": "httpx library not installed. Run: pip install httpx"
        })
    
    try:
        if not ticket_id or not ticket_id.strip():
            return json.dumps({
                "success": False,
                "ticket_id": ticket_id,
                "error": "Ticket ID cannot be empty. Please provide a valid ticket ID."
            })
        
        # Placeholder API endpoint (defaults to local mock server)
        api_base = os.getenv(
            "TICKET_API_BASE",
            "http://localhost:5000/v1"
        )
        api_endpoint = f"{api_base}/tickets/{ticket_id}"
        
        # Get optional API token from environment for authentication
        api_token = os.getenv("TICKET_API_TOKEN")
        headers = {}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        # Make HTTP request with timeout
        with httpx.Client(timeout=10.0) as client:
            response = client.get(api_endpoint, headers=headers)
        
        # Handle HTTP 404 - Ticket not found
        if response.status_code == 404:
            return json.dumps({
                "success": False,
                "ticket_id": ticket_id,
                "status_code": 404,
                "error": f"Ticket '{ticket_id}' not found. Please verify the ticket ID is correct."
            })
        
        # Handle HTTP 5xx - Server errors
        elif response.status_code >= 500:
            return json.dumps({
                "success": False,
                "ticket_id": ticket_id,
                "status_code": response.status_code,
                "error": "API server is offline or experiencing issues. Please try again later."
            })
        
        # Handle other HTTP errors
        elif not response.is_success:
            return json.dumps({
                "success": False,
                "ticket_id": ticket_id,
                "status_code": response.status_code,
                "error": f"Failed to fetch ticket: HTTP {response.status_code}. {response.text}"
            })
        
        # Success - parse and return ticket data
        ticket_data = response.json()
        return json.dumps({
            "success": True,
            "ticket_id": ticket_id,
            "status_code": response.status_code,
            "data": ticket_data
        })
    
    except httpx.TimeoutException:
        return json.dumps({
            "success": False,
            "ticket_id": ticket_id,
            "error": "Request timed out. The API took too long to respond. Please try again."
        })
    except httpx.ConnectError:
        return json.dumps({
            "success": False,
            "ticket_id": ticket_id,
            "error": "Failed to connect to the ticket API. Check network connectivity and API endpoint configuration."
        })
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "ticket_id": ticket_id,
            "error": "API returned invalid JSON response. The API may be misconfigured."
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "ticket_id": ticket_id,
            "error": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# Run the server
# ============================================================================

if __name__ == "__main__":
    # FastMCP automatically handles the stdio event loop
    mcp.run()