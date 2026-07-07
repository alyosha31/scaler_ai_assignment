from __future__ import annotations

from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from scaler_script_pipeline.core.models import ScriptProject, utcnow


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "script_projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectRepository:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite:///"):
            db_path = database_url.removeprefix("sqlite:///")
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)

    def create(self, project: ScriptProject) -> ScriptProject:
        with self._session() as session:
            record = ProjectRecord(
                id=project.id,
                payload=project.model_dump_json(),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            session.add(record)
        return project

    def get(self, project_id: str) -> ScriptProject | None:
        with self._session() as session:
            record = session.get(ProjectRecord, project_id)
            if record is None:
                return None
            return ScriptProject.model_validate_json(record.payload)

    def save(self, project: ScriptProject) -> ScriptProject:
        project.touch()
        with self._session() as session:
            record = session.get(ProjectRecord, project.id)
            if record is None:
                record = ProjectRecord(
                    id=project.id,
                    payload=project.model_dump_json(),
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
                session.add(record)
            else:
                record.payload = project.model_dump_json()
                record.updated_at = utcnow()
        return project

    def list(self) -> list[ScriptProject]:
        with self._session() as session:
            records = session.scalars(select(ProjectRecord).order_by(ProjectRecord.updated_at.desc()))
            return [ScriptProject.model_validate_json(record.payload) for record in records]

    def _session(self) -> Session:
        return _SessionContext(self.session_factory())


class _SessionContext:
    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()

