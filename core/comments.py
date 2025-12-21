import time
from typing import List

import sqlmodel

import db


class Comment:
    def _get_default_user_id(self, session: sqlmodel.Session) -> int:
        """Return a usable user id, creating a default user if none exist."""
        existing = session.exec(
            sqlmodel.select(db.users).order_by(db.users.id).limit(1)
        ).first()
        if existing:
            return existing.id

        user = db.users(username="anonymous", token="")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id

    def create(self, issue_id: int, text: str, user_id: int | None = None):
        with sqlmodel.Session(db.engine) as session:
            now = int(time.time())
            resolved_user_id = (
                user_id if user_id is not None else self._get_default_user_id(session)
            )

            comment = db.comments(
                ctime=now,
                issue_id=issue_id,
                user_id=resolved_user_id,
                comment=text.encode("utf-8"),
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)
            return comment

    def get_by_issue(self, issue_id: int) -> List[dict]:
        with sqlmodel.Session(db.engine) as session:
            results = session.exec(
                sqlmodel.select(db.comments, db.users.username)
                .join(db.users, db.comments.user_id == db.users.id, isouter=True)
                .where(db.comments.issue_id == issue_id)
                .order_by(db.comments.ctime)
            ).all()

            comments = []
            for comment, username in results:
                comments.append(
                    {
                        "id": comment.id,
                        "ctime": comment.ctime,
                        "username": username or "anonymous",
                        "text": (comment.comment or b"").decode("utf-8", "ignore"),
                    }
                )
            return comments
