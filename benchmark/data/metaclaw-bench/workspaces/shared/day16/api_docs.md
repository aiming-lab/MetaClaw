# API Documentation - v2.2.x

## Overview

This document provides comprehensive API documentation for the MetaClaw platform API version 2.2.x. The API follows RESTful principles and returns JSON responses.

## Base URL

```
https://api.metaclaw.io/v2
```

## Authentication

All API requests require authentication using Bearer tokens:

```
Authorization: Bearer YOUR_API_TOKEN
```

## Endpoints

### GET /users

Retrieves a list of users in the system.

**Request:**
```http
GET /users?page=1&limit=20
```

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of results per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "developer",
      "created_at": "2026-03-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45
  }
}
```

**Error Codes:**
- `401`: Unauthorized - Invalid or missing authentication token
- `403`: Forbidden - Insufficient permissions
- `500`: Internal Server Error

### POST /users

Creates a new user in the system.

**Request:**
```http
POST /users
Content-Type: application/json

{
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "role": "developer"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "usr_xyz789",
    "email": "newuser@example.com",
    "name": "Jane Smith",
    "role": "developer",
    "created_at": "2026-04-06T09:15:00Z"
  }
}
```

**Error Codes:**
- `400`: Bad Request - Invalid input data
- `401`: Unauthorized
- `409`: Conflict - User with this email already exists
- `500`: Internal Server Error

### GET /tasks

Retrieves a list of tasks.

**Request:**
```http
GET /tasks?status=active&assignee=usr_abc123
```

**Query Parameters:**
- `status` (optional): Filter by task status (active, completed, archived)
- `assignee` (optional): Filter by assigned user ID
- `page` (optional): Page number
- `limit` (optional): Results per page

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "tsk_001",
      "title": "Implement authentication",
      "description": "Add JWT-based authentication to the API",
      "status": "active",
      "assignee": "usr_abc123",
      "created_at": "2026-04-01T14:20:00Z",
      "due_date": "2026-04-10T17:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 8
  }
}
```

**Error Codes:**
- `401`: Unauthorized
- `500`: Internal Server Error

### PUT /tasks/{task_id}

Updates an existing task.

**Request:**
```http
PUT /tasks/tsk_001
Content-Type: application/json

{
  "status": "completed",
  "notes": "Authentication implementation completed and tested"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "tsk_001",
    "title": "Implement authentication",
    "status": "completed",
    "notes": "Authentication implementation completed and tested",
    "updated_at": "2026-04-06T11:30:00Z"
  }
}
```

**Error Codes:**
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found - Task does not exist
- `500`: Internal Server Error

## Rate Limiting

The API implements rate limiting to ensure fair usage:
- **Free tier**: 100 requests per hour
- **Pro tier**: 1,000 requests per hour
- **Enterprise tier**: 10,000 requests per hour

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Timestamp when the rate limit resets

## Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context about the error"
    }
  }
}
```

## Changelog

### v2.2.3 (2026-03-20)
- Improved error messages for validation failures
- Added support for bulk operations on tasks

### v2.2.2 (2026-03-10)
- Fixed pagination bug in /users endpoint
- Performance improvements for large result sets

### v2.2.1 (2026-02-28)
- Added rate limiting headers
- Enhanced authentication error responses

### v2.2.0 (2026-02-15)
- Initial release of v2.2 API
- New task management endpoints
- Improved user management
