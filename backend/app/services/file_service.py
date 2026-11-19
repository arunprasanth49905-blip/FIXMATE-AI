import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.project import Project, ProjectFile
from app.schemas.file import FileTreeItem, FileContentResponse


class FileService:
    def sanitize_and_resolve_path(self, project_id: str, relative_path: str) -> Tuple[Path, str]:
        """
        Strictly sanitizes the requested relative path and resolves it against
        the project's physical workspace root.
        
        Guarantees that path traversal ('..', leading slashes, drive letters, etc.)
        cannot escape the project workspace.
        """
        if not relative_path or not relative_path.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File path cannot be empty"
            )

        # Check for null bytes and drive letters
        if "\0" in relative_path or ":" in relative_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in file path"
            )

        # Normalize slashes and strip leading/trailing slashes
        normalized = relative_path.replace("\\", "/").strip().strip("/")
        parts = normalized.split("/")

        # Disallow empty segments or path traversal segments
        if any(part == ".." or part == "." or not part for part in parts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal or invalid path format detected"
            )

        clean_rel_path = "/".join(parts)
        workspace_dir = settings.get_workspace_dir(project_id).resolve()
        target_path = (workspace_dir / clean_rel_path).resolve()

        # Enforce boundary check
        if not target_path.is_relative_to(workspace_dir):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: Path is outside project workspace"
            )

        return target_path, clean_rel_path

    def validate_extension(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext and ext not in settings.ALLOWED_EXTENSIONS:
            # Allow common dotfiles or extensionless files like Dockerfile, Makefile
            stem = Path(filename).name.lower()
            allowed_special = {"dockerfile", "makefile", "license", "readme", ".gitignore"}
            if stem not in allowed_special and not stem.startswith(".env"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File extension '{ext}' is not supported in this workspace"
                )
        return ext

    def create_file_or_dir(
        self,
        db: Session,
        project_id: str,
        path: str,
        content: str = "",
        is_directory: bool = False
    ) -> ProjectFile:
        # Check project exists
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        target_path, clean_rel_path = self.sanitize_and_resolve_path(project_id, path)
        name = target_path.name
        ext = "" if is_directory else self.validate_extension(name)

        # Check if record already exists
        existing = db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == clean_rel_path)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An item at path '{clean_rel_path}' already exists"
            )

        # Also ensure parent directories are in database and on disk
        parent_parts = clean_rel_path.split("/")[:-1]
        current_parent = ""
        for part in parent_parts:
            current_parent = f"{current_parent}/{part}" if current_parent else part
            parent_target, _ = self.sanitize_and_resolve_path(project_id, current_parent)
            parent_target.mkdir(parents=True, exist_ok=True)
            parent_db = db.execute(
                select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == current_parent)
            ).scalar_one_or_none()
            if not parent_db:
                new_parent = ProjectFile(
                    project_id=project_id,
                    path=current_parent,
                    name=parent_target.name,
                    is_directory=True,
                    size=0,
                    extension="",
                )
                db.add(new_parent)

        if is_directory:
            target_path.mkdir(parents=True, exist_ok=True)
            size = 0
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            raw_bytes = content.encode("utf-8")
            if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size ({settings.MAX_UPLOAD_SIZE_BYTES} bytes)"
                )
            target_path.write_bytes(raw_bytes)
            size = len(raw_bytes)

        file_record = ProjectFile(
            project_id=project_id,
            path=clean_rel_path,
            name=name,
            is_directory=is_directory,
            size=size,
            extension=ext,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        logger.info(f"Created {'directory' if is_directory else 'file'} '{clean_rel_path}' in project {project_id}")
        return file_record

    def get_file(self, db: Session, project_id: str, file_id: str) -> ProjectFile:
        file_record = db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.id == file_id)
        ).scalar_one_or_none()
        if not file_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_record

    def get_file_content(self, db: Session, project_id: str, file_id: str) -> FileContentResponse:
        file_record = self.get_file(db, project_id, file_id)
        if file_record.is_directory:
            return FileContentResponse(
                id=file_record.id,
                project_id=file_record.project_id,
                path=file_record.path,
                name=file_record.name,
                is_directory=True,
                size=0,
                extension="",
                content=None,
                is_binary=False,
                created_at=file_record.created_at,
                updated_at=file_record.updated_at,
            )

        target_path, _ = self.sanitize_and_resolve_path(project_id, file_record.path)
        if not target_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")

        content = ""
        is_binary = False
        try:
            content = target_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # File contains binary data (e.g. image, compiled file)
            is_binary = True
            content = "[Binary or unsupported encoding. Preview unavailable in text editor.]"

        return FileContentResponse(
            id=file_record.id,
            project_id=file_record.project_id,
            path=file_record.path,
            name=file_record.name,
            is_directory=False,
            size=file_record.size,
            extension=file_record.extension,
            content=content,
            is_binary=is_binary,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )

    def save_file_content(self, db: Session, project_id: str, file_id: str, content: str) -> ProjectFile:
        file_record = self.get_file(db, project_id, file_id)
        if file_record.is_directory:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot write content to a directory")

        target_path, _ = self.sanitize_and_resolve_path(project_id, file_record.path)
        raw_bytes = content.encode("utf-8")
        if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size ({settings.MAX_UPLOAD_SIZE_BYTES} bytes)"
            )

        target_path.write_bytes(raw_bytes)
        file_record.size = len(raw_bytes)
        db.commit()
        db.refresh(file_record)

        logger.info(f"Saved file '{file_record.path}' ({len(raw_bytes)} bytes) in project {project_id}")
        return file_record

    def rename_or_move_file(
        self,
        db: Session,
        project_id: str,
        file_id: str,
        new_path: str
    ) -> ProjectFile:
        file_record = self.get_file(db, project_id, file_id)
        old_target, old_rel = self.sanitize_and_resolve_path(project_id, file_record.path)
        new_target, new_rel = self.sanitize_and_resolve_path(project_id, new_path)

        if old_rel == new_rel:
            return file_record

        # Check destination does not already exist
        if db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == new_rel)
        ).scalar_one_or_none() or new_target.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Target path '{new_rel}' already exists"
            )

        if not file_record.is_directory:
            self.validate_extension(new_target.name)

        new_target.parent.mkdir(parents=True, exist_ok=True)
        if old_target.exists():
            shutil.move(str(old_target), str(new_target))

        # If it was a directory, also update all descendants' paths
        if file_record.is_directory:
            descendants = db.execute(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path.startswith(f"{old_rel}/")
                )
            ).scalars().all()
            for desc in descendants:
                desc.path = f"{new_rel}" + desc.path[len(old_rel):]

        file_record.path = new_rel
        file_record.name = new_target.name
        file_record.extension = "" if file_record.is_directory else new_target.suffix.lower()

        db.commit()
        db.refresh(file_record)
        logger.info(f"Renamed/moved '{old_rel}' to '{new_rel}' in project {project_id}")
        return file_record

    def delete_file_or_dir(self, db: Session, project_id: str, file_id: str) -> bool:
        file_record = self.get_file(db, project_id, file_id)
        target_path, rel_path = self.sanitize_and_resolve_path(project_id, file_record.path)

        # If directory, also delete all descendant records
        if file_record.is_directory:
            descendants = db.execute(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path.startswith(f"{rel_path}/")
                )
            ).scalars().all()
            for desc in descendants:
                db.delete(desc)

            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
        else:
            if target_path.exists():
                try:
                    target_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to unlink file {target_path}: {e}")

        db.delete(file_record)
        db.commit()
        logger.info(f"Deleted '{rel_path}' from project {project_id}")
        return True

    def get_project_files(self, db: Session, project_id: str) -> List[ProjectFile]:
        query = select(ProjectFile).where(ProjectFile.project_id == project_id).order_by(
            ProjectFile.is_directory.desc(),
            ProjectFile.path.asc()
        )
        return list(db.execute(query).scalars().all())

    def get_project_file_tree(self, db: Session, project_id: str) -> List[FileTreeItem]:
        files = self.get_project_files(db, project_id)
        
        # Build hierarchical tree from paths
        node_map: Dict[str, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []

        # Sort so directories and parent paths are processed first
        for f in files:
            node = {
                "id": f.id,
                "path": f.path,
                "name": f.name,
                "is_directory": f.is_directory,
                "size": f.size,
                "extension": f.extension,
                "children": [] if f.is_directory else None,
            }
            node_map[f.path] = node

        for f in files:
            node = node_map[f.path]
            parts = f.path.split("/")
            if len(parts) == 1:
                roots.append(node)
            else:
                parent_path = "/".join(parts[:-1])
                parent_node = node_map.get(parent_path)
                if parent_node and parent_node["children"] is not None:
                    parent_node["children"].append(node)
                else:
                    # In case parent record wasn't registered, add to roots
                    roots.append(node)

        # Convert dict tree to FileTreeItem models
        def to_tree_item(item: Dict[str, Any]) -> FileTreeItem:
            children = None
            if item["children"] is not None:
                # Sort: directories first, then alphabetical by name
                sorted_children = sorted(
                    item["children"],
                    key=lambda x: (not x["is_directory"], x["name"].lower())
                )
                children = [to_tree_item(child) for child in sorted_children]
            return FileTreeItem(
                id=item["id"],
                path=item["path"],
                name=item["name"],
                is_directory=item["is_directory"],
                size=item["size"],
                extension=item["extension"],
                children=children,
            )

        sorted_roots = sorted(roots, key=lambda x: (not x["is_directory"], x["name"].lower()))
        return [to_tree_item(r) for r in sorted_roots]

    async def upload_files(
        self,
        db: Session,
        project_id: str,
        files: List[UploadFile],
        paths: Optional[List[str]] = None
    ) -> Tuple[List[ProjectFile], List[str]]:
        uploaded_records: List[ProjectFile] = []
        errors: List[str] = []

        for idx, upload in enumerate(files):
            try:
                # Determine relative path: prefer client-provided path if given (preserving directory structure)
                rel_path = (paths[idx] if paths and idx < len(paths) and paths[idx] else upload.filename) or "untitled.txt"
                content_bytes = await upload.read()

                if len(content_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
                    errors.append(f"{rel_path}: File exceeds {settings.MAX_UPLOAD_SIZE_BYTES} bytes limit")
                    continue

                target_path, clean_rel = self.sanitize_and_resolve_path(project_id, rel_path)
                ext = self.validate_extension(target_path.name)

                # Ensure parents exist
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content_bytes)

                # Update or create db record
                existing = db.execute(
                    select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == clean_rel)
                ).scalar_one_or_none()

                if existing:
                    existing.size = len(content_bytes)
                    existing.extension = ext
                    db.commit()
                    db.refresh(existing)
                    uploaded_records.append(existing)
                else:
                    new_file = ProjectFile(
                        project_id=project_id,
                        path=clean_rel,
                        name=target_path.name,
                        is_directory=False,
                        size=len(content_bytes),
                        extension=ext,
                    )
                    db.add(new_file)
                    db.commit()
                    db.refresh(new_file)
                    uploaded_records.append(new_file)

            except Exception as e:
                errors.append(f"{upload.filename}: {str(e)}")

        return uploaded_records, errors


file_service = FileService()
