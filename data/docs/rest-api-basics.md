# REST API Basics

## What is REST

REST is an architectural style for web APIs. A client sends an HTTP request to a URL that identifies a resource, and the server replies with a representation of that resource, usually JSON. Each request is stateless, so the server keeps no session between calls.

## HTTP Methods

GET reads a resource and never changes data. POST creates a new resource. PUT replaces a resource completely. PATCH changes part of a resource. DELETE removes a resource. GET, PUT and DELETE are idempotent, which means repeating the call has the same effect as making it once.

## Status Codes

2xx means success, for example 200 OK, 201 Created and 204 No Content. 4xx means the client made a mistake, for example 400 Bad Request, 401 Unauthorized, 404 Not Found and 429 Too Many Requests. 5xx means the server failed, for example 500 Internal Server Error and 503 Service Unavailable.

## Pagination

Large collections are returned in pages. Offset pagination uses limit and offset parameters and is simple but slow on big tables. Cursor pagination returns an opaque token for the next page and stays fast and stable while data changes.

## Versioning

Put the version in the URL, such as /v1/users, or in a header. Never change the meaning of an existing field inside a version. Add new fields freely and remove old ones only in a new version.
