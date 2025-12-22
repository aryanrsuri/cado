import time

import sqlmodel

import db


class Tag:
    def tag_issue(self, issue_id: int, tag: str):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            issue = session.get(db.issues, issue_id)
            if issue is None:
                return None
            existing_tag = session.exec(
                sqlmodel.select(db.tags).where(db.tags.value == tag)
            ).first()
            if existing_tag:
                existing_link = session.exec(
                    sqlmodel.select(db.issues_tags).where(
                        db.issues_tags.issue_id == issue_id,
                        db.issues_tags.tag_id == existing_tag.id,
                    )
                ).first()
                if existing_link:
                    return None
                issue_tag = db.issues_tags(issue_id=issue_id, tag_id=existing_tag.id)
                session.add(issue_tag)
                session.commit()
                return existing_tag
            new_tag = db.tags(value=tag, ctime=now)
            session.add(new_tag)
            session.commit()
            session.refresh(new_tag)
            issue_tag = db.issues_tags(issue_id=issue_id, tag_id=new_tag.id)
            session.add(issue_tag)
            session.commit()
            return new_tag

    def get_tags_by_issue_id(self, issue_id: int):
        with sqlmodel.Session(db.engine) as session:
            statement = (
                sqlmodel.select(db.tags, db.issues_tags)
                .join(db.issues_tags, db.tags.id == db.issues_tags.tag_id)
                .where(db.issues_tags.issue_id == issue_id)
                .order_by(db.tags.ctime)
            )
            result = session.exec(statement)
            return list(result.all())
