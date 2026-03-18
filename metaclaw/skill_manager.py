"""
Skill Manager for conversation-mode RL training.

Loads skills from a directory of skill subdirectories (SKILL.md format):

    memory_data/skills/
        skill-name/
            SKILL.md           <- YAML frontmatter + markdown body
        another-skill/
            SKILL.md

Each SKILL.md must have YAML frontmatter with at least `name` and `description`:

    ---
    name: debug-systematically
    description: Use when diagnosing a bug...
    ---

    # Debug Systematically
    ...

Optional frontmatter field:
  category: coding             <- defaults to "general" if omitted

Valid categories: general, coding, research, data_analysis, security,
                  communication, automation, agentic, productivity, common_mistakes
"""

import glob
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")

# ------------------------------------------------------------------ #
# Conversation task-type keywords                                      #
# ------------------------------------------------------------------ #
_CONV_TASK_TYPES = {
    "coding": [
        "code", "debug", "implement", "function", "class", "bug", "error",
        "python", "java", "javascript", "typescript", "c++", "rust", "sql",
        "api", "library", "framework", "algorithm", "refactor", "test",
        "unittest", "lint", "compile", "build", "deploy", "dockerfile",
        "git", "commit", "pull request", "review",
    ],
    "research": [
        "research", "paper", "arxiv", "study", "literature", "source",
        "cite", "academic", "journal", "publication", "evidence", "survey",
        "review", "meta-analysis", "find information", "look up",
    ],
    "data_analysis": [
        "data", "dataset", "csv", "dataframe", "pandas", "sql query",
        "analytics", "metric", "dashboard", "visualize", "chart", "plot",
        "statistics", "aggregate", "pipeline", "etl", "schema", "database",
        "table", "column", "row", "query", "duckdb", "spark",
    ],
    "productivity": [
        "task", "plan", "schedule", "project", "workflow", "automate",
        "organize", "deadline", "priority", "todo", "agenda", "meeting",
        "goal", "milestone", "track progress", "manage",
    ],
    "security": [
        "security", "vulnerability", "exploit", "auth", "authentication",
        "authorization", "password", "token", "api key", "secret",
        "encrypt", "decrypt", "ssl", "tls", "injection", "xss", "csrf",
        "audit", "penetration", "threat", "permission", "access control",
    ],
    "communication": [
        "email", "message", "slack", "notify", "announcement", "draft",
        "write to", "reply", "response", "newsletter", "outreach",
        "communicate", "update", "report to", "summarize for",
    ],
    "automation": [
        "automate", "script", "cron", "scheduled", "pipeline", "batch",
        "ci/cd", "workflow", "trigger", "webhook", "bot", "scrape",
        "selenium", "playwright", "headless", "background job",
    ],
    "agentic": [
        "agent", "multi-agent", "sub-agent", "orchestrate", "spawn",
        "delegate", "autonomous", "long-running", "tool use", "mcp",
        "memory", "context window", "session", "agentic",
    ],
}


# ------------------------------------------------------------------ #
# Frontmatter parser                                                   #
# ------------------------------------------------------------------ #

def _parse_skill_md(path: str) -> Optional[Dict[str, Any]]:
    """
    Parse a SKILL.md file (directory-based skills format).

    Returns a dict with keys: name, description, category, content.
    Returns None if the file is missing required fields or has no frontmatter.
    ``category`` defaults to "general" when not present in frontmatter.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        logger.warning("[SkillManager] could not read %s: %s", path, e)
        return None

    if not raw.startswith("---"):
        return None

    end_idx = raw.find("\n---", 3)
    if end_idx == -1:
        return None

    fm_text = raw[3:end_idx].strip()
    body = raw[end_idx + 4:].strip()

    fm: Dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()

    name = fm.get("name", "").strip()
    description = fm.get("description", "").strip()
    category = fm.get("category", "general").strip()  # optional, defaults to "general"

    if not name or not description:
        logger.warning("[SkillManager] skipping %s — missing name or description", path)
        return None

    return {
        "name": name,
        "description": description,
        "category": category,
        "content": body,
    }


# ------------------------------------------------------------------ #
# SkillManager                                                         #
# ------------------------------------------------------------------ #

class SkillManager:
    """
    Retrieves skills from a directory of Markdown skill files (Claude skills format).

    Supports two retrieval modes:
      * ``"template"`` – keyword-based task-type detection, zero latency
      * ``"embedding"`` – cosine similarity via SentenceTransformer
    """

    def __init__(
        self,
        skills_dir: str,
        retrieval_mode: str = "template",
        embedding_model_path: Optional[str] = None,
        task_specific_top_k: Optional[int] = None,
    ):
        if retrieval_mode not in ("template", "embedding"):
            raise ValueError(
                f"retrieval_mode must be 'template' or 'embedding', got '{retrieval_mode}'"
            )
        if not os.path.isdir(skills_dir):
            raise FileNotFoundError(f"Skills directory not found: {skills_dir}")

        self._skills_dir = skills_dir
        self.retrieval_mode = retrieval_mode
        self.embedding_model_path = embedding_model_path or "Qwen/Qwen3-Embedding-0.6B"
        self.task_specific_top_k = task_specific_top_k

        self._embedding_model = None
        self._skill_embeddings_cache: Optional[Dict] = None

        # Monotonically-increasing counter. Incremented each time new skills are
        # successfully added via add_skills(). Used by the RL trainer to discard
        # training samples collected before a skill evolution (MAML support/query
        # separation: samples that triggered evolution are not reused for RL updates).
        self.generation: int = 0

        self.skills = self._load_skills()

        n_gen = len(self.skills.get("general_skills", []))
        n_task = sum(len(v) for v in self.skills.get("task_specific_skills", {}).values())
        n_mistakes = len(self.skills.get("common_mistakes", []))
        logger.info(
            "[SkillManager] loaded %d general + %d task-specific + %d mistakes "
            "from %s | mode=%s",
            n_gen, n_task, n_mistakes, skills_dir, retrieval_mode,
        )

        if retrieval_mode == "embedding":
            self._compute_skill_embeddings()

    # ------------------------------------------------------------------ #
    # Loading                                                              #
    # ------------------------------------------------------------------ #

    def _load_skills(self) -> Dict[str, Any]:
        """Scan skills_dir for */SKILL.md files and parse each into the internal dict."""
        result: Dict[str, Any] = {
            "general_skills": [],
            "task_specific_skills": {},
            "common_mistakes": [],
        }

        paths = sorted(glob.glob(os.path.join(self._skills_dir, "*", "SKILL.md")))
        if not paths:
            logger.warning("[SkillManager] no SKILL.md files found in %s", self._skills_dir)
            return result

        for path in paths:
            skill = _parse_skill_md(path)
            if skill is None:
                continue
            cat = skill["category"]
            if cat == "general":
                result["general_skills"].append(skill)
            elif cat == "common_mistakes":
                result["common_mistakes"].append(skill)
            else:
                result.setdefault("task_specific_skills", {}).setdefault(cat, []).append(skill)

        return result

    def reload(self) -> None:
        """Re-scan the skills directory and rebuild the internal skill bank."""
        self.skills = self._load_skills()
        self._skill_embeddings_cache = None
        if self.retrieval_mode == "embedding":
            self._compute_skill_embeddings()
        logger.info("[SkillManager] reloaded skills from %s", self._skills_dir)

    # ------------------------------------------------------------------ #
    # Task-type detection                                                  #
    # ------------------------------------------------------------------ #

    def _detect_task_type(self, task_description: str) -> str:
        desc = task_description.lower()
        task_specific = self.skills.get("task_specific_skills", {})
        for task_type, keywords in _CONV_TASK_TYPES.items():
            if task_type in task_specific and any(kw in desc for kw in keywords):
                return task_type
        return next(iter(task_specific), "general")

    # ------------------------------------------------------------------ #
    # Embedding helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embedding retrieval. "
                    "Install with: pip install sentence-transformers"
                )
            logger.info("[SkillManager] loading embedding model: %s", self.embedding_model_path)
            self._embedding_model = SentenceTransformer(self.embedding_model_path)
        return self._embedding_model

    @staticmethod
    def _skill_to_text(skill: Dict[str, Any]) -> str:
        parts = [
            skill.get("name", "").strip(),
            skill.get("description", "").strip(),
        ]
        content = skill.get("content", "").strip()
        if content:
            parts.append(content[:200])
        return ". ".join(p for p in parts if p)

    def _compute_skill_embeddings(self) -> Dict:
        if self._skill_embeddings_cache is not None:
            return self._skill_embeddings_cache

        import numpy as np

        general_items = [
            ("general", None, s) for s in self.skills.get("general_skills", [])
        ]
        task_items = [
            ("task_specific", tt, s)
            for tt, skills in self.skills.get("task_specific_skills", {}).items()
            for s in skills
        ]
        all_items = general_items + task_items
        texts = [self._skill_to_text(it[2]) for it in all_items]

        model = self._get_embedding_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        self._skill_embeddings_cache = {
            "items": all_items,
            "embeddings": embeddings,
            "n_general": len(general_items),
        }
        logger.info("[SkillManager] cached %d skill embeddings", len(all_items))
        return self._skill_embeddings_cache

    def _embedding_retrieve(
        self, task_description: str, top_k_general: int, top_k_task: int
    ) -> tuple[list[dict], list[dict]]:
        import numpy as np

        cache = self._compute_skill_embeddings()
        model = self._get_embedding_model()
        query_emb = model.encode(
            [task_description],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )[0]

        sims = cache["embeddings"] @ query_emb
        n_gen = cache["n_general"]

        gen_idx = list(reversed(sorted(range(n_gen), key=lambda i: sims[i])))[:top_k_general]
        task_idx = list(reversed(sorted(range(n_gen, len(sims)), key=lambda i: sims[i])))[
            :top_k_task
        ]
        general_skills = [cache["items"][i][2] for i in gen_idx]
        task_skills = [cache["items"][i][2] for i in task_idx]
        return general_skills, task_skills

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def retrieve(self, task_description: str, top_k: int = 6) -> list[dict]:
        """Retrieve relevant skills for *task_description*."""
        common_mistakes = self.skills.get("common_mistakes", [])[:5]

        if self.retrieval_mode == "embedding":
            ts_top_k = self.task_specific_top_k if self.task_specific_top_k is not None else top_k
            general, task_skills = self._embedding_retrieve(task_description, top_k, ts_top_k)
        else:
            task_type = self._detect_task_type(task_description)
            general = self.skills.get("general_skills", [])[:top_k]
            all_task = self.skills.get("task_specific_skills", {}).get(task_type, [])
            task_skills = (
                all_task[: self.task_specific_top_k]
                if self.task_specific_top_k is not None
                else all_task
            )

        return general + task_skills + common_mistakes

    def format_for_conversation(self, skills: list[dict]) -> str:
        """Format skill dicts into a block for insertion into a system prompt."""
        if not skills:
            return ""
        lines = ["## Active Skills"]
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            content = skill.get("content", "")
            lines.append(f"\n### {name}")
            if description:
                lines.append(f"_{description}_")
            if content:
                lines.append("")
                lines.append(content)
        return "\n".join(lines)

    def add_skill(self, skill: dict) -> bool:
        """
        Add a new skill to the in-memory bank and write its SKILL.md file.

        Returns True if the skill was added, False if it already exists.
        """
        name = skill.get("name", "").strip()
        if not name:
            logger.warning("[SkillManager] add_skill called with missing name")
            return False
        if not _SAFE_NAME_RE.match(name):
            logger.warning("[SkillManager] rejected invalid skill name: %s", name)
            return False

        existing = self._get_all_skill_names()
        if name in existing:
            logger.info("[SkillManager] skipping duplicate skill: %s", name)
            return False

        cat = skill.get("category", "general").strip()
        if cat == "general":
            self.skills.setdefault("general_skills", []).append(skill)
        elif cat == "common_mistakes":
            self.skills.setdefault("common_mistakes", []).append(skill)
        else:
            (
                self.skills.setdefault("task_specific_skills", {})
                .setdefault(cat, [])
                .append(skill)
            )

        self._skill_embeddings_cache = None
        self._write_skill_md(skill)
        logger.info("[SkillManager] added skill: %s", name)
        return True

    def add_skills(self, new_skills: list[dict], category: str = "general") -> int:
        """Add multiple skills; returns count actually added.

        Increments ``self.generation`` when at least one skill is successfully
        added, signalling the RL trainer to discard pre-evolution samples.
        """
        added = 0
        for skill in new_skills:
            if "category" not in skill:
                skill = {**skill, "category": category}
            if self.add_skill(skill):
                added += 1
        if added > 0:
            self.generation += 1
        return added

    def _write_skill_md(self, skill: dict) -> None:
        """Persist a single skill to its SKILL.md file inside a subdirectory of skills_dir."""
        name = skill.get("name", "unknown")
        skill_dir = os.path.join(self._skills_dir, name)
        canonical = os.path.realpath(skill_dir)
        if not canonical.startswith(os.path.realpath(self._skills_dir) + os.sep):
            logger.warning("[SkillManager] blocked path traversal in skill name: %s", name)
            return
        os.makedirs(skill_dir, exist_ok=True)
        path = os.path.join(skill_dir, "SKILL.md")
        description = skill.get("description", "")
        category = skill.get("category", "general")
        content = skill.get("content", "")
        # Only write category to frontmatter when it's not the default "general"
        fm_lines = [f"name: {name}", f"description: {description}"]
        if category and category != "general":
            fm_lines.append(f"category: {category}")
        fm = "\n".join(fm_lines)
        text = f"---\n{fm}\n---\n\n{content}\n"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info("[SkillManager] wrote skill file: %s", path)
        except OSError as e:
            logger.warning("[SkillManager] could not write %s: %s", path, e)

    def save(self, path: Optional[str] = None) -> None:
        """
        Persist all in-memory skills back to .md files.

        ``path`` is ignored (kept for backward compatibility); files are always
        written to skills_dir.
        """
        all_skills = (
            self.skills.get("general_skills", [])
            + [s for cat in self.skills.get("task_specific_skills", {}).values() for s in cat]
            + self.skills.get("common_mistakes", [])
        )
        for skill in all_skills:
            self._write_skill_md(skill)
        logger.info("[SkillManager] saved %d skills to %s", len(all_skills), self._skills_dir)

    def _get_all_skill_names(self) -> set:
        names: set = set()
        for s in self.skills.get("general_skills", []):
            if s.get("name"):
                names.add(s["name"])
        for task_skills in self.skills.get("task_specific_skills", {}).values():
            for s in task_skills:
                if s.get("name"):
                    names.add(s["name"])
        for s in self.skills.get("common_mistakes", []):
            if s.get("name"):
                names.add(s["name"])
        return names

    def get_skill_count(self) -> dict:
        return {
            "general": len(self.skills.get("general_skills", [])),
            "task_specific": sum(
                len(v) for v in self.skills.get("task_specific_skills", {}).values()
            ),
            "common_mistakes": len(self.skills.get("common_mistakes", [])),
        }
