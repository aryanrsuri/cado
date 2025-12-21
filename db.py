import os

from sqlalchemy import Column, Integer, text
from sqlmodel import Field, Session, SQLModel, UniqueConstraint, create_engine


class projects(SQLModel, table=True):
    id: int = Field(primary_key=True)
    ctime: int = Field(index=True)
    etime: int
    mtime: int = Field(
        sa_column=Column(
            Integer,
            server_default=text("(UNIX_TIMESTAMP())"),
            onupdate=text("(UNIX_TIMESTAMP())"),
            nullable=False,
        )
    )
    name: str = Field(index=True)
    checksum: str
    active: bool = Field(default=True)


class subissues(SQLModel, table=True):
    id: int = Field(primary_key=True)
    ctime: int
    etime: int
    mtime: int = Field(
        sa_column=Column(
            Integer,
            server_default=text("(UNIX_TIMESTAMP())"),
            onupdate=text("(UNIX_TIMESTAMP())"),
            nullable=False,
        )
    )
    status: int = Field(default=0)
    time_spent: int = Field(default=0)
    time_estimated: int = Field(default=0)
    issue_id: int = Field(foreign_key="issues.id")


class issues(SQLModel, table=True):
    id: int = Field(primary_key=True)
    ctime: int
    etime: int
    mtime: int = Field(
        sa_column=Column(
            Integer,
            server_default=text("(UNIX_TIMESTAMP())"),
            onupdate=text("(UNIX_TIMESTAMP())"),
            nullable=False,
        )
    )
    stime: int = Field(default=0)
    time_spent: int = Field(default=0)
    time_estimated: int = Field(default=0)
    title: str = Field(index=True)
    checksum: str
    position: int
    score: int
    priority: int = Field(default=3)
    description: str
    body: bytes | None = None
    color: str
    status: int = Field(default=0)
    active: bool = Field(default=True)
    type: str = Field(default="task")
    project_id: int | None = Field(default=None, foreign_key="projects.id")
    column_id: int | None = Field(default=None, foreign_key="columns.id")
    swimlane_id: int | None = Field(default=None, foreign_key="swimlanes.id")


class columns(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    ctime: int
    mtime: int = Field(
        sa_column=Column(
            Integer,
            server_default=text("(UNIX_TIMESTAMP())"),
            onupdate=text("(UNIX_TIMESTAMP())"),
            nullable=False,
        )
    )
    issue_limit: int = Field(default=5)
    position: int
    active: bool = Field(default=True)
    project_id: int | None = Field(foreign_key="projects.id")

    __table_args__ = (UniqueConstraint("name", "project_id", name="uq_c_i_project"),)


class swimlanes(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    ctime: int
    position: int
    issue_limit: int = Field(default=5)
    active: bool = Field(default=True)
    project_id: int | None = Field(foreign_key="projects.id")

    __table_args__ = (UniqueConstraint("name", "project_id", name="uq_sl_i_project"),)


class comments(SQLModel, table=True):
    id: int = Field(primary_key=True)
    ctime: int
    issue_id: int = Field(foreign_key="issues.id")
    user_id: int = Field(foreign_key="users.id")
    comment: bytes | None = None


class tags(SQLModel, table=True):
    id: int = Field(primary_key=True)
    value: str
    ctime: int


class issues_tags(SQLModel, table=True):
    id: int = Field(primary_key=True)
    issue_id: int = Field(foreign_key="issues.id")
    tag_id: int = Field(foreign_key="tags.id")


class users(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str
    token: str


class events(SQLModel, table=True):
    id: int = Field(primary_key=True)
    ctime: int
    project_id: int | None = Field(foreign_key="projects.id")
    issue_id: int | None = Field(foreign_key="issues.id")
    event_name: str
    action_name: str
    log: bytes | None = None


class version(SQLModel, table=True):
    version: int = Field(primary_key=True)


engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///database.db"))
SQLModel.metadata.create_all(engine)
