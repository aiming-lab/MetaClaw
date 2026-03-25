# Project Orion API Reference

Last Updated: April 10, 2026

## Endpoints

### GET /tasks

Retrieve a list of tasks.

**Parameters:**
- `status` (optional): Filter by task status (open, in_progress, completed)
- `assignee` (optional): Filter by assignee user ID
- `limit` (optional): Maximum number of results (default: 50)

**Response:**
```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "Implement user authentication",
      "status": "in_progress",
      "assignee": "user_42",
      "created": "2026-03-15",
      "due": "2026-04-10"
    }
  ],
  "total": 1
}
```

**Error Codes:**
- 400: Invalid parameters
- 401: Unauthorized
- 500: Internal server error

### POST /tasks

Create a new task.

**Request Body:**
```json
{
  "title": "Task title",
  "description": "Task description",
  "assignee": "user_42",
  "due": "2026-04-15"
}
```

**Response:**
```json
{
  "id": "task_002",
  "title": "Task title",
  "status": "open",
  "created": "2026-04-10"
}
```

**Error Codes:**
- 400: Invalid request body
- 401: Unauthorized
- 500: Internal server error

### PUT /tasks/{task_id}

Update an existing task.

**Parameters:**
- `task_id`: Task ID to update

**Request Body:**
```json
{
  "status": "completed",
  "notes": "Task completed successfully"
}
```

**Response:**
```json
{
  "id": "task_001",
  "status": "completed",
  "updated": "2026-04-11"
}
```

**Error Codes:**
- 400: Invalid request body
- 401: Unauthorized
- 404: Task not found
- 500: Internal server error
