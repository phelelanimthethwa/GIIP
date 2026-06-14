"""
One-off script to send an acceptance letter email with the PDF attachment.

Usage:
    python send_acceptance_letter.py
"""

import os
import sys
from datetime import datetime


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, send_acceptance_letter_email  # noqa: E402


RECIPIENT_EMAIL = "thobanisgabuzam@gmail.com"


def build_sample_payload():
    """Build a sample accepted-paper payload for a one-off send."""
    paper_data = {
        "paper_title": "Innovation Pathways in Global Research",
        "paper_id": "SUB-2026-0042",
        "presentation_type": "oral_presentation",
        "updated_at": datetime.now().isoformat(),
        "authors": [
            {"name": "Thobani Sgabuzam"},
            {"name": "Prof. A. Coauthor"},
        ],
        "conference_id": "preview-sample-conf",
        "user_email": RECIPIENT_EMAIL,
    }

    conference_data = {
        "conference_id": "preview-sample-conf",
        "conference_code": "GC2026",
        "basic_info": {
            "name": "Global Conferences 2026",
            "location": "Cape Town, South Africa",
            "start_date": "2026-09-15",
            "end_date": "2026-09-17",
        },
    }

    registration_data = {
        "conference_code": "GC2026",
        "total_amount": 3500.0,
    }

    comments = (
        "The committee congratulates you on a strong contribution. "
        "Please upload your camera-ready version by the stated deadline."
    )

    return paper_data, conference_data, registration_data, comments


def main():
    paper_data, conference_data, registration_data, comments = build_sample_payload()

    with app.app_context():
        sent = send_acceptance_letter_email(
            paper_data=paper_data,
            conference_data=conference_data,
            registration_data=registration_data,
            comments=comments,
        )

    if sent:
        print(f"Acceptance letter sent to {RECIPIENT_EMAIL}")
        return 0

    print(f"Failed to send acceptance letter to {RECIPIENT_EMAIL}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
