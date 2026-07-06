import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, text
from .models import Product, Maker, Topic, Note, SyncRun, Setting


def get_products(
    db: Session,
    search: Optional[str] = None,
    topic_id: Optional[str] = None,
    status_label: Optional[str] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    offset: int = 0,
    limit: int = 50,
) -> Tuple[List[Product], int]:
    query = db.query(Product).outerjoin(Note).options(
        joinedload(Product.topics),
        joinedload(Product.makers),
        joinedload(Product.note),
    )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.like(search_filter),
                Product.tagline.like(search_filter),
                Product.description.like(search_filter),
                Note.text.like(search_filter),
            )
        )

    if topic_id:
        query = query.filter(Product.topics.any(Topic.id == topic_id))

    if status_label:
        if status_label == "none":
            query = query.filter(or_(Note.id == None, Note.status_label == "none"))
        else:
            query = query.filter(Note.status_label == status_label)

    if start_date:
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        query = query.filter(Product.created_at >= start_datetime)
    if end_date:
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        query = query.filter(Product.created_at <= end_datetime)

    total_count = query.distinct().count()
    products = (
        query.order_by(desc(Product.votes), desc(Product.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return products, total_count


def get_product(db: Session, product_id: str) -> Optional[Product]:
    return (
        db.query(Product)
        .options(
            joinedload(Product.topics),
            joinedload(Product.makers),
            joinedload(Product.note),
        )
        .filter(Product.id == product_id)
        .first()
    )


def get_all_topics(db: Session) -> List[Topic]:
    return db.query(Topic).order_by(Topic.name).all()


def save_note_and_status(db: Session, product_id: str, text: str, status_label: str) -> Note:
    note = db.query(Note).filter(Note.product_id == product_id).first()
    if note:
        note.text = text
        note.status_label = status_label
        note.updated_at = datetime.datetime.utcnow()
    else:
        note = Note(
            product_id=product_id,
            text=text,
            status_label=status_label,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(note)
    db.commit()
    db.refresh(note)
    return note


def log_sync_run(db: Session, sync_mode: str, fetched_count: int, error_state: Optional[str] = None) -> Optional[SyncRun]:
    try:
        run = SyncRun(
            timestamp=datetime.datetime.utcnow(),
            sync_mode=sync_mode,
            fetched_count=fetched_count,
            error_state=error_state,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception:
        db.rollback()
        return None


def get_last_sync_run(db: Session) -> Optional[SyncRun]:
    return db.query(SyncRun).order_by(desc(SyncRun.timestamp)).first()


def get_sync_stats(db: Session) -> dict:
    product_count = db.query(Product).count()
    shortlisted_count = db.query(Note).filter(Note.status_label == "shortlisted").count()
    noted_count = db.query(Note).filter(Note.text != "").count()
    last_sync = get_last_sync_run(db)

    return {
        "total_products": product_count,
        "shortlisted": shortlisted_count,
        "with_notes": noted_count,
        "last_sync_time": last_sync.timestamp if last_sync else None,
        "last_sync_count": last_sync.fetched_count if last_sync else 0,
        "last_sync_error": last_sync.error_state if last_sync else None,
    }


def _parse_topics(raw_topics: dict) -> List[dict]:
    edges = raw_topics.get("edges", []) if isinstance(raw_topics, dict) else []
    return [edge.get("node", {}) for edge in edges if edge.get("node", {}).get("id")]


def _parse_makers(raw_makers) -> List[dict]:
    if not isinstance(raw_makers, list):
        return []
    return [m for m in raw_makers if m.get("id")]


def _upsert_maker(db: Session, mid: str, name: str, username: str, profile_url: str) -> Maker:
    """Insert or update a maker using raw SQL to avoid SQLAlchemy merge issues."""
    db.execute(
        text("INSERT OR REPLACE INTO makers (id, name, username, profile_url) VALUES (:id, :name, :username, :profile_url)"),
        {"id": mid, "name": name, "username": username, "profile_url": profile_url},
    )
    return db.query(Maker).filter(Maker.id == mid).first()


def _upsert_topic(db: Session, tid: str, name: str, slug: str) -> Topic:
    """Insert or update a topic using raw SQL to avoid SQLAlchemy merge issues."""
    db.execute(
        text("INSERT OR REPLACE INTO topics (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": tid, "name": name, "slug": slug},
    )
    return db.query(Topic).filter(Topic.id == tid).first()


def upsert_products(db: Session, raw_posts: List[dict]) -> int:
    """
    Upsert list of products from Product Hunt GraphQL response.
    Uses INSERT OR REPLACE for makers/topics to avoid IntegrityError.
    Returns count of successful upserts.
    """
    upserted_count = 0
    for post in raw_posts:
        try:
            pid = post.get("id")
            if not pid:
                continue

            created_at_str = post.get("createdAt")
            created_at = (
                datetime.datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
                if created_at_str
                else datetime.datetime.utcnow()
            )

            featured_at_str = post.get("featuredAt")
            featured_at = None
            if featured_at_str:
                featured_at = datetime.datetime.strptime(featured_at_str, "%Y-%m-%dT%H:%M:%SZ")

            # 1. Product Upsert using INSERT OR REPLACE
            db.execute(
                text("INSERT OR REPLACE INTO products (id, name, tagline, description, website, product_hunt_url, votes, comments_count, created_at, featured_at) VALUES (:id, :name, :tagline, :description, :website, :product_hunt_url, :votes, :comments_count, :created_at, :featured_at)"),
                {
                    "id": pid,
                    "name": post.get("name"),
                    "tagline": post.get("tagline"),
                    "description": post.get("description"),
                    "website": post.get("website"),
                    "product_hunt_url": post.get("url"),
                    "votes": post.get("votesCount", 0),
                    "comments_count": post.get("commentsCount", 0),
                    "created_at": created_at,
                    "featured_at": featured_at,
                },
            )
            product = db.query(Product).filter(Product.id == pid).first()

            # 2. Topics Upsert and Association
            topics_list = _parse_topics(post.get("topics", {}))
            product_topics_list = []
            for tdata in topics_list:
                tid = tdata.get("id")
                if not tid:
                    continue
                topic = _upsert_topic(db, tid, tdata.get("name", ""), tdata.get("slug", ""))
                if topic:
                    product_topics_list.append(topic)
            product.topics = product_topics_list

            # 3. Makers Upsert and Association
            makers_list = _parse_makers(post.get("makers", []))
            product_makers_list = []
            for mdata in makers_list:
                mid = mdata.get("id")
                if not mid:
                    continue
                username = mdata.get("username") or ""
                profile_url = f"https://www.producthunt.com/@{username}" if username else ""
                maker = _upsert_maker(db, mid, mdata.get("name", ""), username, profile_url)
                if maker:
                    product_makers_list.append(maker)
            product.makers = product_makers_list

            upserted_count += 1
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error processing product {post.get('name', 'unknown')}: {str(e)}")

    db.commit()
    return upserted_count
