import time

import sqlmodel

import db


class Event:
    def create(
        self,
        project_id: int | None,
        issue_id: int | None,
        event_name: str,
        action_name: str,
        log: bytes | None = None,
    ):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            event = db.events(
                ctime=now,
                project_id=project_id,
                issue_id=issue_id,
                event_name=event_name,
                action_name=action_name,
                log=log,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def get_by_project(self, project_id: int):
        with sqlmodel.Session(db.engine) as session:
            result = session.exec(
                sqlmodel.select(db.events)
                .where(db.events.project_id == project_id)
                .order_by(db.events.ctime)
            )
            return list(result.all())
