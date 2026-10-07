#!/usr/bin/env python3
"""Log in with the selected profile and print who that session is."""

from __future__ import annotations

import argparse
from typing import Any

from _common import (
    add_profile_argument,
    clear_saved_credentials,
    combine_profiles,
    main,
    open_sessions,
    public_user,
    use_profile_argument,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log in and print who the session is, or wipe one saved profile."
    )
    add_profile_argument(parser)
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete one profile, its Keychain items, and its session cache. "
            "On a terminal, ask for a replacement. Does not log in."
        ),
    )
    return parser.parse_args(argv)


def _login_payload(session: object) -> dict[str, Any]:
    creds = getattr(session, "creds", None)
    host = str(getattr(creds, "main_url", "") or "")
    user = session.confirm_login()  # type: ignore[attr-defined]
    return {
        "ok": True,
        "main_url": host,
        "user": public_user(user),
    }


def build(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    use_profile_argument(args)
    if args.reset:
        return clear_saved_credentials()
    return combine_profiles(open_sessions(), _login_payload)


if __name__ == "__main__":
    main(build)
