import datetime
import csv
import io

from fastapi import FastAPI, Request, Form, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from . import crud, config, product_hunt, models

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Hunt Research Console")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    token = config.get_setting_value(db, "product_hunt_token")
    default_sync_mode = config.get_setting_value(db, "default_sync_mode", "today")
    stats = crud.get_sync_stats(db)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "has_token": bool(token),
        "default_sync_mode": default_sync_mode,
        "stats": stats,
    })


@app.post("/sync", response_class=HTMLResponse)
async def sync_data(request: Request, sync_mode: str = Form(...), db: Session = Depends(get_db)):
    token = config.get_setting_value(db, "product_hunt_token")
    if not token:
        return "<div class='rounded-xl bg-rose-50 border border-rose-200 px-4 py-3 text-xs text-rose-800'>Error: Product Hunt token not configured. Go to Settings.</div>"

    try:
        client = product_hunt.ProductHuntClient(token)
        posts = client.fetch_launches(sync_mode=sync_mode)
        count = crud.upsert_products(db, posts)
        crud.log_sync_run(db, sync_mode=sync_mode, fetched_count=count)

        stats = crud.get_sync_stats(db)

        return f"""
        <div hx-swap-oob="innerHTML:#stats-panel" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="bg-white rounded-2xl border border-slate-200 p-6 flex items-center justify-between shadow-sm hover:shadow-md transition-shadow">
                <div class="space-y-1">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Products</span>
                    <p class="text-4xl font-black text-slate-900">{stats['total_products']}</p>
                    <p class="text-xs text-slate-500">Synced in local DB</p>
                </div>
                <div class="h-12 w-12 bg-indigo-50 border border-indigo-100 text-indigo-500 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-database text-xl"></i>
                </div>
            </div>
            <div class="bg-white rounded-2xl border border-slate-200 p-6 flex items-center justify-between shadow-sm hover:shadow-md transition-shadow">
                <div class="space-y-1">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Shortlisted</span>
                    <p class="text-4xl font-black text-slate-900">{stats['shortlisted']}</p>
                    <p class="text-xs text-slate-500">Marked for follow-up</p>
                </div>
                <div class="h-12 w-12 bg-brand-50 border border-brand-100 text-brand-500 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-star text-xl"></i>
                </div>
            </div>
            <div class="bg-white rounded-2xl border border-slate-200 p-6 flex items-center justify-between shadow-sm hover:shadow-md transition-shadow">
                <div class="space-y-1">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Annotated</span>
                    <p class="text-4xl font-black text-slate-900">{stats['with_notes']}</p>
                    <p class="text-xs text-slate-500">Products with custom research</p>
                </div>
                <div class="h-12 w-12 bg-emerald-50 border border-emerald-100 text-emerald-500 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-note-sticky text-xl"></i>
                </div>
            </div>
        </div>
        <div class="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs text-emerald-700">
            <span class="flex items-center gap-2">
                <i class="fa-solid fa-circle-check text-emerald-500 text-sm"></i>
                <span>Last sync: <strong>{stats['last_sync_time'].strftime('%Y-%m-%d %H:%M:%S')} UTC</strong></span>
            </span>
            <span>Fetched <strong>{count} product{'s' if count != 1 else ''}</strong></span>
        </div>
        """
    except Exception as e:
        db.rollback()
        crud.log_sync_run(db, sync_mode=sync_mode, fetched_count=0, error_state=str(e))
        return f"<div class='rounded-xl bg-rose-50 border border-rose-200 px-4 py-3 text-xs text-rose-800 flex items-center gap-2'><i class='fa-solid fa-circle-xmark text-rose-500 text-sm'></i> {str(e)}</div>"


@app.get("/launches", response_class=HTMLResponse)
async def list_launches(
    request: Request,
    search: str = Query(default=""),
    topic: str = Query(default=""),
    status: str = Query(default=""),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    db: Session = Depends(get_db),
):
    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        pass

    products, total = crud.get_products(
        db,
        search=search or None,
        topic_id=topic or None,
        status_label=status or None,
        start_date=start_dt,
        end_date=end_dt,
    )

    return templates.TemplateResponse("launches.html", {
        "request": request,
        "active_page": "launches",
        "products": products,
        "total": total,
        "topics": crud.get_all_topics(db),
        "search": search,
        "current_topic": topic,
        "current_status": status,
        "start_date": start_date,
        "end_date": end_date,
    })


@app.get("/launches/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "active_page": "launches",
        "product": product,
    })


@app.post("/launches/{product_id}/toggle-shortlist")
async def toggle_shortlist(product_id: str, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        return "<span>Product not found</span>"

    new_status = "shortlisted"
    if product.note and product.note.status_label == "shortlisted":
        new_status = "none"

    existing_text = product.note.text if product.note else ""
    crud.save_note_and_status(db, product_id, existing_text, new_status)

    if new_status == "shortlisted":
        icon_class = "fa-solid fa-star text-amber-400"
    else:
        icon_class = "fa-regular fa-star text-slate-400"

    return f"""
    <button hx-post="/launches/{product_id}/toggle-shortlist" hx-target="this" hx-swap="outerHTML"
            class="inline-flex items-center justify-center p-2 rounded-xl border border-slate-200 hover:bg-slate-50 transition text-slate-400 hover:text-amber-500"
            title="Toggle Shortlist">
        <i class="{icon_class} text-lg"></i>
    </button>
    """


@app.post("/launches/{product_id}/note")
async def update_note(
    product_id: str,
    note: str = Form(default=""),
    status_label: str = Form(default="none"),
    db: Session = Depends(get_db),
):
    crud.save_note_and_status(db, product_id, note, status_label)
    return RedirectResponse(url=f"/launches/{product_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/export/csv")
async def export_csv(
    search: str = Query(default=""),
    topic: str = Query(default=""),
    status: str = Query(default=""),
    db: Session = Depends(get_db),
):
    products, _ = crud.get_products(
        db,
        search=search or None,
        topic_id=topic or None,
        status_label=status or None,
        limit=1000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Tagline", "Votes", "Comments", "Topics", "Makers", "Status", "Note", "Website", "Product Hunt URL"])

    for p in products:
        topics_str = ", ".join([t.name for t in p.topics])
        makers_str = ", ".join([m.name for m in p.makers])
        status_label = p.note.status_label if p.note else "none"
        note_text = p.note.text if p.note else ""
        writer.writerow([
            p.name, p.tagline, p.votes, p.comments_count,
            topics_str, makers_str, status_label, note_text,
            p.website, p.product_hunt_url,
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=launches.csv"},
    )


@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request, db: Session = Depends(get_db)):
    token = config.get_setting_value(db, "product_hunt_token")
    sync_mode = config.get_setting_value(db, "default_sync_mode", "today")
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "token": token,
        "sync_mode": sync_mode,
    })


@app.post("/settings")
async def save_settings(
    request: Request,
    token: str = Form(default=""),
    sync_mode: str = Form(default="today"),
    db: Session = Depends(get_db),
):
    config.set_setting_value(db, "product_hunt_token", token.strip())
    config.set_setting_value(db, "default_sync_mode", sync_mode)
    return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)
