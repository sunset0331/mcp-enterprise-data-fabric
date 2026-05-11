"""
Mock Ticket API Server for testing the MCP enterprise server locally.

This Flask server simulates a real ticket management API with endpoints for:
- GET /v1/tickets/{ticket_id} - Fetch a specific ticket
- GET /v1/tickets - List all tickets
- Error handling for 404, 500, etc.

Run this in a separate terminal: python mock_api_server.py
"""

import json
import logging
from pathlib import Path
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load mock tickets data
TICKETS_FILE = "mock_tickets.json"

def load_tickets():
    """Load mock tickets from JSON file."""
    if not Path(TICKETS_FILE).exists():
        logger.error(f"Tickets file not found: {TICKETS_FILE}")
        return {}
    
    with open(TICKETS_FILE, "r") as f:
        return json.load(f)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route("/v1/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """
    Fetch a specific ticket by ID.
    
    Returns:
        - 200: Ticket found with full details
        - 404: Ticket not found
        - 500: Server error (10% chance for testing error handling)
    """
    import random
    
    # Simulate occasional server errors (10% chance)
    if random.random() < 0.1:
        logger.warning(f"Simulated 500 error for ticket {ticket_id}")
        return jsonify({"error": "Internal server error"}), 500
    
    tickets = load_tickets()
    
    if ticket_id in tickets:
        logger.info(f"✓ Ticket retrieved: {ticket_id}")
        return jsonify(tickets[ticket_id]), 200
    else:
        logger.warning(f"✗ Ticket not found: {ticket_id}")
        return jsonify({"error": f"Ticket {ticket_id} not found"}), 404


@app.route("/v1/tickets", methods=["GET"])
def list_tickets():
    """
    List all tickets with optional filtering.
    
    Query Parameters:
        - status: Filter by ticket status (in_progress, completed, etc.)
        - priority: Filter by priority (critical, high, medium, low)
    
    Returns:
        - 200: List of tickets matching criteria
    """
    tickets = load_tickets()
    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")
    
    filtered = tickets.copy()
    
    if status_filter:
        filtered = {k: v for k, v in filtered.items() if v.get("status") == status_filter}
    
    if priority_filter:
        filtered = {k: v for k, v in filtered.items() if v.get("priority") == priority_filter}
    
    logger.info(f"✓ Listed {len(filtered)} tickets (total: {len(tickets)})")
    return jsonify(list(filtered.values())), 200


@app.route("/v1/tickets", methods=["POST"])
def create_ticket():
    """
    Create a new ticket (mock implementation).
    
    Returns:
        - 201: Ticket created successfully
        - 400: Invalid ticket data
    """
    data = request.get_json()
    
    if not data or "title" not in data:
        return jsonify({"error": "Missing required field: title"}), 400
    
    ticket = {
        "id": f"NEW-{len(load_tickets()) + 1}",
        "title": data.get("title"),
        "description": data.get("description", ""),
        "status": "new",
        "priority": data.get("priority", "medium"),
        "assignee": data.get("assignee", "Unassigned"),
        "created_date": "2026-05-11",
        "updated_date": "2026-05-11"
    }
    
    logger.info(f"✓ Ticket created: {ticket['id']}")
    return jsonify(ticket), 201


@app.route("/v1/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "mock-ticket-api"}), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("="*70)
    logger.info("STARTING MOCK TICKET API SERVER")
    logger.info("="*70)
    logger.info("Available endpoints:")
    logger.info("  GET  http://localhost:5000/v1/tickets/<ticket_id>")
    logger.info("  GET  http://localhost:5000/v1/tickets")
    logger.info("  POST http://localhost:5000/v1/tickets")
    logger.info("  GET  http://localhost:5000/v1/health")
    logger.info("\nExample tickets to test:")
    
    tickets = load_tickets()
    for ticket_id in list(tickets.keys())[:3]:
        logger.info(f"  curl http://localhost:5000/v1/tickets/{ticket_id}")
    
    logger.info("\nServer running on http://localhost:5000")
    logger.info("="*70 + "\n")
    
    app.run(host="localhost", port=5000, debug=True, use_reloader=False)
