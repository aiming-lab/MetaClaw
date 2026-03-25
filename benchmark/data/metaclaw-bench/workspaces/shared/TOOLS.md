# Available Tools

## Command Execution

- **exec** — Run a shell command in the workspace directory and return stdout/stderr

## File Operations

- **read** — Read the contents of a file in the workspace
- **write** — Write or overwrite a file in the workspace
- **exec(ls)** — Execute bash command `ls` to list files in a directory

## Search

- **exec(glob)** — Execute bash command `glob` to match files/directories via wildcards
- **exec(grep)** — Execute bash command `grep` to search text patterns in files

## Usage Notes

- All file paths are relative to the workspace root unless otherwise specified
- Commands are executed with the workspace as the working directory
- Write operations create parent directories automatically if needed
- Binary files are not supported; use text-based formats (JSON, Markdown, Python, CSV, etc.)
