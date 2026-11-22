import shutil
import threading
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.normalization import (
    normalize_project_name,
    validate_project_name,
    ProjectNameDuplicateError,
)
from app.models.project import Project, ProjectFile
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self):
        self._lock = threading.Lock()

    def find_project_by_normalized_name(
        self, db: Session, name: str, exclude_project_id: Optional[str] = None
    ) -> Optional[Project]:
        """
        Finds an existing project matching the given name after normalization.
        Normalizes by trimming whitespace and comparing case-insensitively.
        Optionally excludes a specific project ID (used during rename/edit).
        """
        norm = normalize_project_name(name)
        if not norm:
            return None

        query = select(Project).where(
            or_(
                Project.normalized_name == norm,
                func.lower(func.trim(Project.name)) == norm,
            )
        )
        if exclude_project_id:
            query = query.where(Project.id != exclude_project_id)

        return db.execute(query).scalars().first()

    def create_project(self, db: Session, data: ProjectCreate) -> Project:
        """
        Creates a new project with strict duplicate name protection:
        - Rejects empty, whitespace-only, or invalid names.
        - Checks if the normalized name already exists across all projects regardless of language.
        - Preserves user display capitalization.
        - Thread-safe concurrency control.
        """
        clean_name = validate_project_name(data.name)
        norm_name = normalize_project_name(clean_name)

        with self._lock:
            # Duplicate name protection across all projects
            existing = self.find_project_by_normalized_name(db, norm_name)
            if existing:
                logger.warning(
                    f"Rejected duplicate project name '{clean_name}' (normalized: '{norm_name}'). "
                    f"Conflicts with existing project '{existing.name}' ({existing.id}, language={existing.language})"
                )
                raise ProjectNameDuplicateError(
                    "Project name already exists. Choose a different project name.",
                    conflict_name=clean_name,
                )

            project = Project(
                name=clean_name,
                normalized_name=norm_name,
                description=data.description,
                language=data.language,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

        # Initialize physical workspace directory
        workspace_dir = settings.get_workspace_dir(project.id)
        logger.info(f"Created project '{project.name}' ({project.id}) with workspace at {workspace_dir}")

        return project

    def get_projects(self, db: Session, search: Optional[str] = None) -> List[Project]:
        query = select(Project)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(or_(Project.name.ilike(term), Project.description.ilike(term)))

        # Sort by updated_at descending
        query = query.order_by(Project.updated_at.desc())
        projects = db.execute(query).scalars().all()
        return list(projects)

    def get_project(self, db: Session, project_id: str) -> Optional[Project]:
        query = select(Project).where(Project.id == project_id)
        return db.execute(query).scalar_one_or_none()

    def update_project(self, db: Session, project_id: str, data: ProjectUpdate) -> Optional[Project]:
        """
        Updates an existing project with duplicate name protection:
        - If name is unchanged (same normalized name as current project), it is allowed.
        - If renamed to match another project's normalized name, raises ProjectNameDuplicateError.
        - Language updates cannot bypass duplicate name protection.
        - Thread-safe concurrency control.
        """
        with self._lock:
            project = self.get_project(db, project_id)
            if not project:
                return None

            if data.name is not None:
                clean_name = validate_project_name(data.name)
                norm_name = normalize_project_name(clean_name)

                # Check if another project already uses this normalized name
                existing = self.find_project_by_normalized_name(db, norm_name, exclude_project_id=project_id)
                if existing:
                    logger.warning(
                        f"Rejected duplicate rename for project {project_id} to '{clean_name}'. "
                        f"Conflicts with project '{existing.name}' ({existing.id})"
                    )
                    raise ProjectNameDuplicateError(
                        "Project name already exists. Choose a different project name.",
                        conflict_name=clean_name,
                    )

                project.name = clean_name
                project.normalized_name = norm_name

            if data.description is not None:
                project.description = data.description
            if data.language is not None:
                project.language = data.language

            db.commit()
            db.refresh(project)
        logger.info(f"Updated project '{project.name}' ({project.id})")
        return project

    def delete_project(self, db: Session, project_id: str) -> bool:
        project = self.get_project(db, project_id)
        if not project:
            return False

        # Remove physical workspace directory
        try:
            workspace_dir = settings.get_workspace_dir(project_id)
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir, ignore_errors=True)
                logger.info(f"Removed physical workspace directory for project {project_id}")
        except Exception as e:
            logger.error(f"Error removing workspace directory for project {project_id}: {e}")

        # Delete from database (cascades to project_files)
        db.delete(project)
        db.commit()
        logger.info(f"Deleted project '{project.name}' ({project.id})")
        return True

    def get_project_file_count(self, db: Session, project_id: str) -> int:
        query = select(func.count(ProjectFile.id)).where(
            ProjectFile.project_id == project_id,
            ProjectFile.is_directory.is_(False)
        )
        return db.execute(query).scalar() or 0

    def audit_duplicate_projects(self, db: Session) -> Dict[str, Any]:
        """
        Audits all projects in the database to detect and report existing duplicate normalized names.
        Safe: preserves all records and does not alter project IDs or files.
        """
        projects = db.execute(select(Project).order_by(Project.created_at.asc())).scalars().all()
        groups: Dict[str, List[Project]] = {}
        for p in projects:
            norm = p.normalized_name or normalize_project_name(p.name)
            groups.setdefault(norm, []).append(p)

        duplicate_groups = {norm: projs for norm, projs in groups.items() if len(projs) > 1}
        return {
            "total_projects": len(projects),
            "total_duplicate_groups": len(duplicate_groups),
            "total_duplicate_projects": sum(len(projs) for projs in duplicate_groups.values()),
            "groups": duplicate_groups,
        }


project_service = ProjectService()
