---
name: sql-best-practices
description: "Use this skill when writing or reviewing SQL queries including SELECT statements, JOINs, aggregations, window functions, or DDL/DML like CREATE, UPDATE, DELETE. Use when someone asks to 'write a query', 'optimize this SQL', or 'is this query safe'. Enforces column-explicit selects, CTE usage, parameterized queries, transaction wrapping for destructive ops, and EXPLAIN-driven optimization."
---

# SQL Best Practices

**Query quality:**
- Use `SELECT col1, col2` — never `SELECT *` in production code.
- Use CTEs (`WITH`) for readability instead of deeply nested subqueries.
- Filter early: apply `WHERE` before `JOIN` when possible to reduce data scanned.
- Use `EXPLAIN` / `EXPLAIN ANALYZE` to inspect query plans for slow queries.

**Safety:**
- Always use parameterized queries from application code — never string interpolation.
- Wrap destructive operations (`DELETE`, `UPDATE`, `DROP`) in a transaction.
- Test on a staging/dev environment before running on production.

**Naming:** `snake_case` for tables/columns, descriptive names, consistent pluralization.
