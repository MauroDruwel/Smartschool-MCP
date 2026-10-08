#!/usr/bin/env python3
"""List courses and teachers for the configured account."""

from __future__ import annotations

import argparse
from typing import Any

from smartschool import Courses

from _common import (
    add_profile_argument,
    combine_profiles,
    main,
    open_sessions,
    teacher_names,
    use_profile_argument,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Smartschool courses.")
    add_profile_argument(parser)
    return parser.parse_args(argv)


def build(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    use_profile_argument(args)

    def fetch(session: object) -> dict[str, Any]:
        rows = []
        for course in Courses(session):  # type: ignore[arg-type]
            rows.append(
                {
                    "name": getattr(course, "name", "") or "",
                    "teachers": teacher_names(getattr(course, "teachers", None)),
                }
            )
        return {"courses": rows, "total": len(rows)}

    return combine_profiles(open_sessions(), fetch)


if __name__ == "__main__":
    main(build)
