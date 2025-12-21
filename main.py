from datetime import datetime, timezone
import time
from enum import IntEnum

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import columns, comments, events, issues, projects

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def format_timestamp_utc(timestamp):
    if timestamp is None or timestamp <= 0:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError, OSError):
        return str(timestamp)


class Status(IntEnum):
    PENDING = 0
    ACTIVE = 1
    REVIEWING = 2
    CLOSED = 3


def format_status(status):
    return Status(status).name


def format_duration(seconds):
    if seconds is None:
        return ""
    try:
        total = max(0, int(seconds))
    except (TypeError, ValueError):
        return str(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


templates.env.filters["utc"] = format_timestamp_utc
templates.env.filters["status"] = format_status
templates.env.filters["duration"] = format_duration

project_service = projects.Project()
column_service = columns.Column()
issue_service = issues.Issue()
comment_service = comments.Comment()
event_service = events.Event()

def build_gantt_data(project_id: int, cols):
    events_list = event_service.get_by_project(project_id)
    events_by_issue = {}
    for event in events_list:
        if event.issue_id is None:
            continue
        events_by_issue.setdefault(int(event.issue_id), []).append(event)

    now = int(time.time())
    rows = []
    min_ts = None
    max_ts = None

    for col in cols:
        issues_list = issue_service.get_issues_by_column(col.id)
        for issue in issues_list:
            segments = []
            ctime = issue.ctime or now
            stime = issue.stime or 0
            etime = issue.etime or 0
            mtime = issue.mtime or ctime
            issue_events = events_by_issue.get(int(issue.id), [])
            issue_events.sort(key=lambda e: e.ctime)

            if issue_events:
                active_start = None
                cursor = ctime
                last_stop = None
                for event in issue_events:
                    if event.action_name == "start":
                        if active_start is None:
                            if event.ctime > cursor:
                                status = (
                                    int(Status.PENDING)
                                    if last_stop is None
                                    else int(Status.CLOSED)
                                )
                                segments.append(
                                    {
                                        "start": cursor,
                                        "end": event.ctime,
                                        "status": status,
                                    }
                                )
                            active_start = event.ctime
                    elif event.action_name == "stop":
                        if active_start is not None:
                            segments.append(
                                {
                                    "start": active_start,
                                    "end": event.ctime,
                                    "status": int(Status.ACTIVE),
                                }
                            )
                            active_start = None
                            cursor = event.ctime
                            last_stop = event.ctime
                        else:
                            cursor = event.ctime
                            last_stop = event.ctime
                if active_start is not None:
                    active_end = now if issue.status == int(Status.ACTIVE) else mtime
                    segments.append(
                        {
                            "start": active_start,
                            "end": active_end,
                            "status": int(Status.ACTIVE),
                        }
                    )
                else:
                    tail_end = mtime if mtime else now
                    if tail_end > cursor:
                        status = (
                            int(Status.CLOSED)
                            if last_stop is not None
                            else int(Status.PENDING)
                        )
                        segments.append(
                            {"start": cursor, "end": tail_end, "status": status}
                        )
            else:
                if stime and stime > ctime:
                    segments.append(
                        {"start": ctime, "end": stime, "status": int(Status.PENDING)}
                    )
                if stime:
                    active_end = (
                        etime
                        if etime
                        else (now if issue.status == int(Status.ACTIVE) else mtime)
                    )
                    if active_end < stime:
                        active_end = stime
                    segments.append(
                        {
                            "start": stime,
                            "end": active_end,
                            "status": int(Status.ACTIVE),
                        }
                    )
                else:
                    pending_end = mtime if mtime > ctime else ctime
                    segments.append(
                        {"start": ctime, "end": pending_end, "status": int(Status.PENDING)}
                    )
                if etime:
                    closed_end = mtime if mtime and mtime >= etime else etime
                    segments.append(
                        {
                            "start": etime,
                            "end": closed_end,
                            "status": int(Status.CLOSED),
                        }
                    )

            for seg in segments:
                if seg["end"] < seg["start"]:
                    seg["end"] = seg["start"]
                min_ts = seg["start"] if min_ts is None else min(min_ts, seg["start"])
                max_ts = seg["end"] if max_ts is None else max(max_ts, seg["end"])

            rows.append(
                {
                    "issue": issue,
                    "column_name": col.name,
                    "segments": segments,
                }
            )

    duration = max(0, (max_ts or 0) - (min_ts or 0))
    for row in rows:
        for seg in row["segments"]:
            if duration == 0:
                left_pct = 0
                width_pct = 100
            else:
                left_pct = (seg["start"] - min_ts) / duration * 100
                width_pct = (seg["end"] - seg["start"]) / duration * 100
                width_pct = max(1.0, width_pct)
            seg["left_pct"] = min(100, max(0, left_pct))
            seg["width_pct"] = min(100, max(1.0, width_pct))

    ticks = []
    now_pct = None
    if min_ts is not None and max_ts is not None and duration > 0:
        for i in range(6):
            pct = i * 20
            ts = int(min_ts + (duration * (i / 5)))
            ticks.append({"pct": pct, "ts": ts})
        now_pct = (now - min_ts) / duration * 100
        now_pct = min(100, max(0, now_pct))

    return {
        "rows": rows,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "ticks": ticks,
        "now_pct": now_pct,
        "status_labels": [
            (int(Status.PENDING), "PENDING"),
            (int(Status.ACTIVE), "ACTIVE"),
            (int(Status.REVIEWING), "REVIEWING"),
            (int(Status.CLOSED), "CLOSED"),
        ],
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    projects_list = project_service.get_projects(10, 0)
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects_list, "active_page": "projects"},
    )


@app.get("/project/{project_id}", response_class=HTMLResponse)
async def board(request: Request, project_id: int):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cols = column_service.get_columns_by_project(project_id)

    board_data = []
    for col in cols:
        issues_list = issue_service.get_issues_by_column(col.id)
        board_data.append({"column": col, "issues": issues_list})

    gantt_data = build_gantt_data(project_id, cols)
    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "project": project,
            "board_data": board_data,
            "active_page": "projects",
            "active_subpage": "board",
            **gantt_data,
        },
    )


@app.get("/project/{project_id}/kanban", response_class=HTMLResponse)
async def kanban(request: Request, project_id: int):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cols = column_service.get_columns_by_project(project_id)

    board_data = []
    for col in cols:
        issues_list = issue_service.get_issues_by_column(col.id)
        board_data.append({"column": col, "issues": issues_list})

    return templates.TemplateResponse(
        "kanban.html",
        {
            "request": request,
            "project": project,
            "board_data": board_data,
            "active_page": "projects",
            "active_subpage": "kanban",
        },
    )


@app.get("/project/{project_id}/gantt", response_class=HTMLResponse)
async def gantt(request: Request, project_id: int):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cols = column_service.get_columns_by_project(project_id)
    gantt_data = build_gantt_data(project_id, cols)

    return templates.TemplateResponse(
        "gantt.html",
        {
            "request": request,
            "project": project,
            **gantt_data,
            "active_page": "projects",
            "active_subpage": "gantt",
        },
    )


@app.post("/project/{project_id}/issue")
async def create_issue(
    project_id: int,
    title: str = Form(...),
    column_id: int = Form(...),
    description: str = Form(""),
):
    issue = issue_service.create(title, column_id, project_id, description)
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)


@app.post("/project/{project_id}/column")
async def create_column(
    project_id: int, name: str = Form(...), position: int = Form(0)
):
    column = column_service.create(name, project_id, position)
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)


@app.get("/issues", response_class=HTMLResponse)
async def issues(request: Request):
    issues_list = issue_service.get_issues()
    return templates.TemplateResponse(
        "issues.html",
        {"request": request, "issues": issues_list, "active_page": "issues"},
    )


@app.post("/issue/{issue_id}/move")
async def move_issue(
    issue_id: int, column_id: int = Form(...), position: int = Form(...)
):
    issue = issue_service.move(issue_id, column_id, position)
    if issue:
        return RedirectResponse(url=f"/project/{issue.project_id}", status_code=303)
    raise HTTPException(status_code=404)


@app.get("/issue/{issue_id}", response_class=HTMLResponse)
async def view_issue(request: Request, issue_id: int, edit: int = 0):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    project = (
        project_service.get_project(issue.project_id) if issue.project_id else None
    )
    column = column_service.get_column(issue.column_id) if issue.column_id else None
    issue_comments = comment_service.get_by_issue(issue_id)

    return templates.TemplateResponse(
        "issue.html",
        {
            "request": request,
            "issue": issue,
            "project": project,
            "column": column,
            "status_active": int(Status.ACTIVE),
            "editing": bool(edit),
            "comments": issue_comments,
        },
    )


@app.get("/issue/{issue_id}/edit", response_class=HTMLResponse)
async def view_issue_edit(request: Request, issue_id: int):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    project = (
        project_service.get_project(issue.project_id) if issue.project_id else None
    )

    return templates.TemplateResponse(
        "issue/edit.html",
        {
            "request": request,
            "issue": issue,
            "project": project,
        },
    )


@app.post("/issue/{issue_id}")
async def update_issue(
    issue_id: int,
    title: str = Form(default=None),
    description: str = Form(default=None),
    status: int = Form(default=None),
    priority: int = Form(default=None),
    type: str = Form(default=None),
    color: str = Form(default=None),
):
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if status is not None:
        update_data["status"] = int(status)
    if priority is not None:
        update_data["priority"] = int(priority)
    if type is not None:
        update_data["type"] = type
    if color is not None:
        update_data["color"] = color

    issue = issue_service.update(issue_id, **update_data)
    if issue:
        return RedirectResponse(url=f"/issue/{issue_id}", status_code=303)
    raise HTTPException(status_code=404)


@app.post("/issue/{issue_id}/start")
async def start_issue(issue_id: int):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.status == int(Status.ACTIVE):
        raise HTTPException(status_code=400, detail="Issue already active")
    issue_service.start(issue_id)
    return RedirectResponse(url=f"/issue/{issue_id}", status_code=303)


@app.post("/issue/{issue_id}/stop")
async def stop_issue(issue_id: int):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.status != int(Status.ACTIVE):
        raise HTTPException(status_code=400, detail="Issue is not active")
    issue_service.stop(issue_id)
    return RedirectResponse(url=f"/issue/{issue_id}", status_code=303)


@app.post("/issue/{issue_id}/log")
async def log_issue_time(issue_id: int, minutes: int = Form(0)):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.status != int(Status.ACTIVE):
        raise HTTPException(status_code=400, detail="Issue is not active")
    seconds = max(0, int(minutes)) * 60
    issue_service.log(issue_id, seconds)
    return RedirectResponse(url=f"/issue/{issue_id}", status_code=303)


@app.post("/issue/{issue_id}/description")
def update_issue_description(issue_id: int, description: str = Form("")):
    issue = issue_service.update(issue_id, **{"description": description})
    if issue:
        return RedirectResponse(
            url=f"/issue/{issue_id}",
            status_code=303,
        )


@app.post("/issue/{issue_id}/comment")
async def create_comment(issue_id: int, comment: str = Form("")):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comment_text = comment.strip()
    if comment_text:
        comment_service.create(issue_id, comment_text)

    return RedirectResponse(url=f"/issue/{issue_id}", status_code=303)


@app.post("/project")
async def create_project(name: str = Form(...)):
    project = project_service.create(name)
    return RedirectResponse(url=f"/project/{project.id}", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
