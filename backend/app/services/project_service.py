import shutil
from typing import List, Optional
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.project import Project, ProjectFile
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def create_project(self, db: Session, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name,
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
        project = self.get_project(db, project_id)
        if not project:
            return None

        if data.name is not None:
            project.name = data.name
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


project_service = ProjectService()
