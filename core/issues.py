import time

import sqlmodel

import db
from core import utils
from core.projects import Project


class Issue:
    def create(
        self,
        title: str,
        column_id: int,
        project_id: int = None,
        description: str = "",
    ):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            statement = sqlmodel.select(db.issues).where(
                db.issues.column_id == column_id
            )
            existing = list(session.exec(statement).all())
            max_pos = max([i.position for i in existing], default=0) if existing else 0

            issue = db.issues(
                title=title,
                column_id=column_id,
                project_id=project_id,
                ctime=now,
                etime=0,
                stime=0,
                mtime=now,
                checksum=utils.hash(title),
                position=max_pos + 1,
                score=0,
                priority=3,
                description=description,
                color="#7CA37C",
                status=0,
                active=True,
                type="task",
            )
            session.add(issue)
            session.commit()
            session.refresh(issue)
            if project_id:
                project = Project()
                project.update_mtime(project_id)
            return issue

    def move(self, issue_id: int, new_column_id: int, new_position: int = None):
        with sqlmodel.Session(db.engine) as session:
            issue = session.get(db.issues, issue_id)
            if issue:
                issue.column_id = new_column_id
                if new_position is not None:
                    issue.position = new_position
                issue.mtime = int(time.time())
                session.add(issue)
                session.commit()
                session.refresh(issue)
                return issue
            return None

    def start(self, issue_id: int):
        with sqlmodel.Session(db.engine) as session:
            issue = session.get(db.issues, issue_id)
            if issue:
                now = int(time.time())
                issue.stime = now
                issue.etime = 0
                issue.status = 1
                issue.mtime = now
                event = db.events(
                    ctime=now,
                    project_id=issue.project_id,
                    issue_id=issue.id,
                    event_name="issue",
                    action_name="start",
                    log=None,
                )
                session.add(issue)
                session.add(event)
                session.commit()
                session.refresh(issue)
                return issue
            return None

    def stop(self, issue_id: int):
        with sqlmodel.Session(db.engine) as session:
            issue = session.get(db.issues, issue_id)
            if issue:
                now = int(time.time())
                if issue.stime:
                    elapsed = max(0, now - issue.stime)
                    if issue.time_spent <= 0:
                        issue.time_spent = elapsed
                issue.etime = now
                issue.status = 3
                issue.mtime = now
                event = db.events(
                    ctime=now,
                    project_id=issue.project_id,
                    issue_id=issue.id,
                    event_name="issue",
                    action_name="stop",
                    log=None,
                )
                session.add(issue)
                session.add(event)
                session.commit()
                session.refresh(issue)
                return issue
            return None

    def log(self, issue_id: int, seconds: int):
        with sqlmodel.Session(db.engine) as session:
            issue = session.get(db.issues, issue_id)
            if issue:
                if seconds > 0:
                    issue.time_spent += seconds
                    issue.mtime = int(time.time())
                    session.add(issue)
                    session.commit()
                    session.refresh(issue)
                return issue
            return None

    def get_issues_by_column(self, column_id: int):
        with sqlmodel.Session(db.engine) as session:
            result = session.exec(
                sqlmodel.select(db.issues)
                .where(db.issues.column_id == column_id)
                .where(db.issues.active)
                .order_by(db.issues.position)
            )
            return list(result.all())

    def get_issue(self, issue_id: int):
        with sqlmodel.Session(db.engine) as session:
            return session.get(db.issues, issue_id)

    def get_issues(self, project_id: int | None = None):
        with sqlmodel.Session(db.engine) as session:
            statement = (
                sqlmodel.select(db.issues, db.projects.name)
                .join(db.projects, db.issues.project_id == db.projects.id, isouter=True)
                .join(db.columns, db.issues.column_id == db.columns.id, isouter=True)
                .where(db.issues.active)
            )
            if project_id is not None:
                statement = statement.where(db.issues.project_id == project_id)
            statement = statement.order_by(db.issues.ctime)
            result = session.exec(statement)
            return list(result.all())

    def update(self, issue_id: int, **kwargs):
        with sqlmodel.Session(db.engine) as session:
            issue = session.get(db.issues, issue_id)
            if issue:
                for key, value in kwargs.items():
                    if hasattr(issue, key):
                        setattr(issue, key, value)
                issue.mtime = int(time.time())
                session.add(issue)
                session.commit()
                session.refresh(issue)
                return issue
            return None
