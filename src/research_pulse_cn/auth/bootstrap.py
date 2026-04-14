"""Bootstrap a super admin account for local or deployment setup."""

from __future__ import annotations

import argparse

from research_pulse_cn.db.session import get_session_factory
from research_pulse_cn.services.admin import AdminService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a bootstrap super admin.")
    parser.add_argument("--email", required=True, help="Bootstrap super admin email address.")
    parser.add_argument("--password", required=True, help="Bootstrap super admin password.")
    parser.add_argument(
        "--display-name",
        default=None,
        help="Optional display name for the bootstrap super admin.",
    )
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        account = AdminService(session).bootstrap_super_admin(
            email=args.email,
            password=args.password,
            display_name=args.display_name,
        )
        print(
            f"Bootstrap super admin ready: {account.email} "
            f"(role={account.role.value}, active={account.is_active})"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
