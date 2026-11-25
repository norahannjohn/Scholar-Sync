from __future__ import annotations

import argparse
import getpass
import json
import sys

from sqlalchemy import select

from app.collectors.registry_defaults import ensure_official_registry_seeded
from app.core.config import configure_logging, get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.monitoring.sync_service import sync_all_active_sources
from app.services.auth_service import normalize_email, register_user


def cmd_create_admin(args: argparse.Namespace) -> int:
    email = normalize_email(args.email)
    password = args.password
    if not password:
        password = getpass.getpass("Enter admin password (min 8 chars): ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            existing.is_admin = True
            existing.is_active = True
            db.add(existing)
            db.commit()
            print(f"Promoted existing user '{email}' to admin.")
            return 0
        register_user(
            db,
            email=email,
            password=password,
            full_name=args.name or "ScholarSync Admin",
            is_admin=True,
        )
        print(f"Created admin user '{email}'.")
        return 0


def cmd_bootstrap_registry(_: argparse.Namespace) -> int:
    with SessionLocal() as db:
        src_count, sch_count = ensure_official_registry_seeded(db)
        print(
            f"Official registry bootstrap complete: {src_count} new source(s), {sch_count} new scheme(s)."
        )
    return 0


def cmd_sync_sources(_: argparse.Namespace) -> int:
    settings = get_settings()
    with SessionLocal() as db:
        ensure_official_registry_seeded(db)
        result = sync_all_active_sources(db, stale_after_days=settings.stale_after_days)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["sources_failed"] < result["sources_checked"] or result["sources_checked"] == 0 else 1


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="scholarsync-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_admin = sub.add_parser("create-admin", help="Create or promote an admin user")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--password", required=False, default="")
    p_admin.add_argument("--name", required=False, default="ScholarSync Admin")
    p_admin.set_defaults(func=cmd_create_admin)

    p_boot = sub.add_parser(
        "bootstrap-registry", help="Ensure verified official sources & baseline schemes exist"
    )
    p_boot.set_defaults(func=cmd_bootstrap_registry)

    p_sync = sub.add_parser(
        "sync-sources", help="Fetch official sources, detect updates, and refresh RAG index"
    )
    p_sync.set_defaults(func=cmd_sync_sources)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
