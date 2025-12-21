import time

import sqlmodel

import db
from core import utils


class Project:
    def create(self, name: str):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            project = db.projects(
                name=name, ctime=now, etime=0, checksum=utils.hash(name), mtime=now
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def get_projects(self, limit: int, offset: int):
        with sqlmodel.Session(db.engine) as session:
            result = session.exec(
                sqlmodel.select(db.projects)
                .where(db.projects.active)
                .limit(limit)
                .offset(offset)
            )
            return list(result.all())

    def get_project(self, project_id: int):
        with sqlmodel.Session(db.engine) as session:
            return session.get(db.projects, project_id)

    def update_mtime(self, project_id: int):
        with sqlmodel.Session(db.engine) as session:
            project = session.get(db.projects, project_id)
            project.mtime = int(time.time())
            session.add(project)
            session.commit()
