from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional, List
from pathlib import Path
from ..storage import db
from .auth import hash_password, verify_password, create_token, decode_token
import json
from datetime import datetime
from ..delivery.emailer import send_email
from ..delivery.html_report import render_html_string
import threading
import time
from ..classify.taxonomy import load_taxonomy
from fastapi import Form

app = FastAPI()

TEMPLATE_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html"]))

def get_current(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    u = db.get_user_by_email(payload.get("sub"))
    return u

def sort_key(item):
    level = (item.get("venue_ccf_level") or "").upper()
    rank = {"A": 3, "B": 2, "C": 1}.get(level, 0)
    pub = item.get("published")
    pub_dt = None
    if pub:
        try:
            pub_dt = datetime.fromisoformat(pub)
        except Exception:
            pub_dt = None
    return (-rank, pub_dt or datetime.max)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = get_current(request)
    tpl = env.get_template("index.html")
    areas, push_time, max_per_day, interval_days, last_push_date = db.get_preferences()
    return tpl.render(user=user, areas=areas, push_time=push_time, max_per_day=max_per_day, interval_days=interval_days)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    tpl = env.get_template("register.html")
    err = request.query_params.get("error")
    return tpl.render(error=err)

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...)):
    db.init_db()
    if db.get_user_by_email(email):
        return RedirectResponse(url="/register?error=该邮箱已存在，请直接登录", status_code=302)
    db.create_user(email, hash_password(password), [], "user")
    resp = RedirectResponse(url="/login", status_code=302)
    return resp

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    tpl = env.get_template("login.html")
    return tpl.render()

@app.post("/login")
def login(response: Response, email: str = Form(...), password: str = Form(...)):
    db.init_db()
    db.create_admin_if_missing()
    user = db.get_user_by_email(email)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if email == "admin" and password == "admin" and not user["password_hash"]:
        token = create_token(email, "admin")
        r = RedirectResponse(url="/admin", status_code=302)
        r.set_cookie("session", token, httponly=True)
        return r
    if not verify_password(password, user["password_hash"]):
        return RedirectResponse(url="/login", status_code=302)
    token = create_token(email, user["role"])
    r = RedirectResponse(url="/", status_code=302)
    r.set_cookie("session", token, httponly=True)
    return r

@app.get("/logout")
def logout():
    r = RedirectResponse(url="/", status_code=302)
    r.delete_cookie("session")
    return r

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    user = get_current(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=302)
    areas, push_time, max_per_day, interval_days, last_push_date = db.get_preferences()
    msg = request.query_params.get("msg")
    err = request.query_params.get("error")
    users = db.list_users()
    tax = load_taxonomy()
    directions = list(tax.keys())
    grouped = {}
    for d in directions:
        cand = db.query_candidates_by_direction(d)
        grouped[d] = sorted(cand, key=sort_key)[:10]
    tpl = env.get_template("admin.html")
    return tpl.render(user=user, areas=areas, push_time=push_time, max_per_day=max_per_day, interval_days=interval_days, users=users, directions=directions, grouped=grouped, msg=msg, error=err)

@app.post("/admin/schedule")
def admin_schedule(request: Request, push_time: str = Form(...), max_per_day: int = Form(...), interval_days: int = Form(...)):
    user = get_current(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=302)
    areas, _, _, _, last_push_date = db.get_preferences()
    db.save_preferences(areas, push_time, int(max_per_day), int(interval_days), last_push_date)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/user_settings")
def admin_user_settings(request: Request, user_id: int = Form(...), push_time_user: str = Form(...), max_per_day_user: int = Form(...)):
    user = get_current(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=302)
    db.set_user_settings(int(user_id), push_time_user, int(max_per_day_user))
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/send_email")
def admin_send_email(request: Request, email: str = Form(...), directions: List[str] = Form(None)):
    user = get_current(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=302)
    tax = load_taxonomy()
    dirs_all = list(tax.keys())
    dirs = directions or []
    dirs = [d for d in dirs if d in dirs_all]
    rows = []
    for d in dirs:
        cand = db.query_candidates_by_direction(d)
        cand_sorted = sorted(cand, key=sort_key)[:10]
        for p in cand_sorted:
            rows.append({
                "source": "arxiv",
                "external_id": p["external_id"],
                "title": p["title"],
                "authors": p["authors"],
                "abstract": p["abstract"],
                "link": p["link"],
                "direction": p["direction"],
                "summary": None,
                "method_improvement": None,
                "experiments": None,
                "venue_name": None,
                "venue_year": None,
                "venue_status": None,
                "venue_ccf_level": p["venue_ccf_level"],
            })
    if not rows:
        return RedirectResponse(url="/admin?error=未选择领域或无候选论文", status_code=302)
    if "@" not in email:
        return RedirectResponse(url="/admin?error=邮箱地址无效", status_code=302)
    html = render_html_string(rows, dirs)
    ok, err = send_email(email, "今日推荐论文", html)
    if ok:
        return RedirectResponse(url="/admin?msg=发送成功", status_code=302)
    return RedirectResponse(url="/admin?error=" + (err or "发送失败"), status_code=302)
@app.post("/admin/push")
def admin_push(request: Request):
    user = get_current(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=302)
    areas, _, _, _, _ = db.get_preferences()
    users = db.list_users()
    for u in users:
        if u["role"] == "admin":
            continue
        inter = u["interests"]
        maxn = max(5, min(int(u["max_per_day_user"] or 10), 10))
        candidates = db.query_user_candidates(inter)
        candidates_sorted = sorted(candidates, key=sort_key)[:maxn]
        directions = inter or areas
        rows = []
        for p in candidates_sorted:
            rows.append({
                "source": "arxiv",
                "external_id": p["external_id"],
                "title": p["title"],
                "authors": p["authors"],
                "abstract": p["abstract"],
                "link": p["link"],
                "direction": p["direction"],
                "summary": None,
                "method_improvement": None,
                "experiments": None,
                "venue_name": None,
                "venue_year": None,
                "venue_status": None,
                "venue_ccf_level": p["venue_ccf_level"],
            })
        html = render_html_string(rows, directions)
        if "@" in u["email"]:
            send_email(u["email"], "每日CS预印本推送", html)
        db.mark_user_pushed(u["id"], [p["external_id"] for p in candidates_sorted])
    return RedirectResponse(url="/admin", status_code=302)

@app.get("/me", response_class=HTMLResponse)
def me_page(request: Request):
    user = get_current(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    areas = user["interests"]
    _, push_time, max_per_day, _, _ = db.get_preferences()
    candidates = db.query_user_candidates(areas)
    candidates_sorted = sorted(candidates, key=sort_key)
    tpl = env.get_template("me.html")
    tax = load_taxonomy()
    dirs = list(tax.keys())
    return tpl.render(user=user, papers=candidates_sorted[:max_per_day], push_time=push_time, directions=dirs)

@app.post("/me/interests")
def update_interests(request: Request, directions: List[str] = Form(None)):
    user = get_current(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    inter = directions or []
    inter = inter[:5]
    db.create_user(user["email"], user["password_hash"], inter, user["role"])
    return RedirectResponse(url="/me", status_code=302)

def run_scheduled_push():
    while True:
        try:
            areas, push_time, max_per_day, interval_days, last_push_date = db.get_preferences()
            if not push_time:
                time.sleep(60)
                continue
            now = datetime.now()
            hhmm = now.strftime("%H:%M")
            do_push = False
            users = db.list_users()
            for u in users:
                if u["role"] == "admin":
                    continue
                pt = u["push_time_user"] or push_time
                if hhmm != pt:
                    continue
                if last_push_date:
                    try:
                        last = datetime.fromisoformat(last_push_date).date()
                        if (now.date() - last).days < int(interval_days):
                            continue
                    except Exception:
                        pass
                maxn = max(5, min(int(u["max_per_day_user"] or max_per_day), 10))
                inter = u["interests"]
                candidates = db.query_user_candidates(inter)
                candidates_sorted = sorted(candidates, key=sort_key)[:maxn]
                directions = inter or areas
                rows = []
                for p in candidates_sorted:
                    rows.append({
                        "source": "arxiv",
                        "external_id": p["external_id"],
                        "title": p["title"],
                        "authors": p["authors"],
                        "abstract": p["abstract"],
                        "link": p["link"],
                        "direction": p["direction"],
                        "summary": None,
                        "method_improvement": None,
                        "experiments": None,
                        "venue_name": None,
                        "venue_year": None,
                        "venue_status": None,
                        "venue_ccf_level": p["venue_ccf_level"],
                    })
                html = render_html_string(rows, directions)
                if "@" in u["email"]:
                    send_email(u["email"], "每日CS预印本推送", html)
                db.mark_user_pushed(u["id"], [p["external_id"] for p in candidates_sorted])
                db.save_preferences(areas, push_time, int(max_per_day), int(interval_days), datetime.now().isoformat())
            time.sleep(30)
        except Exception:
            time.sleep(30)

@app.on_event("startup")
def startup_event():
    db.init_db()
    db.create_admin_if_missing()
    t = threading.Thread(target=run_scheduled_push, daemon=True)
    t.start()
