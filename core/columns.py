import time

import sqlmodel

import db
from core.projects import Project


class Column:
    def create(self, name: str, project_id: int, position: int = 0):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            column = db.columns(
                name=name,
                project_id=project_id,
                position=position,
                ctime=now,
                mtime=now,
                active=True,
            )
            session.add(column)
            session.commit()
            session.refresh(column)
            project = Project()
            project.update_mtime(project_id)

            return column

    def get_columns_by_project(self, project_id: int):
        with sqlmodel.Session(db.engine) as session:
            result = session.exec(
                sqlmodel.select(db.columns)
                .where(db.columns.project_id == project_id)
                .where(db.columns.active)
                .order_by(db.columns.position)
            )
            return list(result.all())

    def get_column(self, column_id: int):
        with sqlmodel.Session(db.engine) as session:
            return session.get(db.columns, column_id)
