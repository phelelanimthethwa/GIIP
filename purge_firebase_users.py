import argparse
import json
import os
from datetime import datetime
from urllib.parse import unquote

import firebase_admin
from firebase_admin import auth, credentials, db, storage
from dotenv import load_dotenv


DEFAULT_DATABASE_URL = "https://giir-66ae6-default-rtdb.firebaseio.com"
DEFAULT_STORAGE_BUCKET = "giir-66ae6.firebasestorage.app"


def _init_firebase():
    if firebase_admin._apps:
        return

    load_dotenv()

    if os.environ.get("FIREBASE_CREDENTIALS"):
        cred_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(cred_dict)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    elif os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH"):
        cred = credentials.Certificate(os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"])
    else:
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_options = {
        "databaseURL": os.environ.get("FIREBASE_DATABASE_URL", DEFAULT_DATABASE_URL),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", DEFAULT_STORAGE_BUCKET),
    }
    firebase_admin.initialize_app(cred, firebase_options)


def _storage_path_from_public_url(url: str) -> str | None:
    """
    Supports URLs like:
    - https://storage.googleapis.com/{bucket}/{path}
    - https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{urlencoded_path}?alt=media&token=...
    """
    if not url:
        return None

    try:
        if "storage.googleapis.com/" in url:
            # https://storage.googleapis.com/{bucket}/{path}
            parts = url.split("/")
            if len(parts) < 5:
                return None
            return "/".join(parts[4:])

        if "firebasestorage.googleapis.com" in url and "/o/" in url:
            # .../o/{urlencoded_path}?...
            encoded = url.split("/o/", 1)[1]
            encoded_path = encoded.split("?", 1)[0]
            return unquote(encoded_path)
    except Exception:
        return None

    return None


def _maybe_delete_blob(bucket, blob_path: str, dry_run: bool) -> bool:
    if not blob_path:
        return False
    if dry_run:
        print(f"[dry-run] storage delete {blob_path}")
        return True
    try:
        bucket.blob(blob_path).delete()
        print(f"storage deleted {blob_path}")
        return True
    except Exception as e:
        print(f"storage delete failed {blob_path}: {e}")
        return False


def _maybe_delete_rtdb_path(path: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"[dry-run] rtdb delete {path}")
        return True
    try:
        db.reference(path).delete()
        print(f"rtdb deleted {path}")
        return True
    except Exception as e:
        print(f"rtdb delete failed {path}: {e}")
        return False


def _iter_dict(d):
    if not isinstance(d, dict):
        return []
    return list(d.items())


def purge_user_by_email(email: str, dry_run: bool) -> dict:
    report = {
        "email": email,
        "uid": None,
        "auth_deleted": False,
        "rtdb_deleted_paths": [],
        "rtdb_deleted_registration_ids": [],
        "rtdb_deleted_paper_ids": [],
        "storage_deleted_paths": [],
        "errors": [],
    }

    try:
        user = auth.get_user_by_email(email)
    except Exception as e:
        report["errors"].append(f"auth get_user_by_email failed: {e}")
        return report

    uid = user.uid
    report["uid"] = uid
    bucket = storage.bucket()

    # 1) Delete user profile + direct per-user nodes
    try:
        user_ref_path = f"users/{uid}"
        user_data = db.reference(user_ref_path).get() or {}
        photo_url = user_data.get("photo_url")
        photo_path = _storage_path_from_public_url(photo_url) if isinstance(photo_url, str) else None
        if photo_path:
            if _maybe_delete_blob(bucket, photo_path, dry_run=dry_run):
                report["storage_deleted_paths"].append(photo_path)

        for path in [
            f"users/{uid}",
            f"user_registrations/{uid}",
            f"user_paper_submissions/{uid}",
            f"payment_proofs/{uid}",
        ]:
            if _maybe_delete_rtdb_path(path, dry_run=dry_run):
                report["rtdb_deleted_paths"].append(path)
    except Exception as e:
        report["errors"].append(f"direct per-user cleanup failed: {e}")

    # 2) Delete registrations belonging to this user
    try:
        registrations = db.reference("registrations").get() or {}
        for reg_id, reg in _iter_dict(registrations):
            if not isinstance(reg, dict):
                continue
            reg_email = (reg.get("email") or reg.get("user_email") or "").strip().lower()
            reg_uid = (reg.get("user_id") or "").strip()
            if reg_uid == uid or (reg_email and reg_email == email.lower()):
                proof = reg.get("payment_proof")
                if isinstance(proof, dict):
                    proof_path = proof.get("path")
                    if isinstance(proof_path, str) and proof_path:
                        if _maybe_delete_blob(bucket, proof_path, dry_run=dry_run):
                            report["storage_deleted_paths"].append(proof_path)
                if _maybe_delete_rtdb_path(f"registrations/{reg_id}", dry_run=dry_run):
                    report["rtdb_deleted_registration_ids"].append(reg_id)
    except Exception as e:
        report["errors"].append(f"registrations cleanup failed: {e}")

    # 3) Delete paper submissions belonging to this user
    try:
        papers = db.reference("papers").get() or {}
        for paper_id, paper in _iter_dict(papers):
            if not isinstance(paper, dict):
                continue
            paper_email = (paper.get("user_email") or paper.get("email") or "").strip().lower()
            paper_uid = (paper.get("user_id") or "").strip()
            if paper_uid == uid or (paper_email and paper_email == email.lower()):
                if _maybe_delete_rtdb_path(f"papers/{paper_id}", dry_run=dry_run):
                    report["rtdb_deleted_paper_ids"].append(paper_id)
    except Exception as e:
        report["errors"].append(f"papers cleanup failed: {e}")

    # 4) Delete nested per-conference records (registrations + paper_submissions)
    try:
        conferences = db.reference("conferences").get() or {}
        for conf_id, conf in _iter_dict(conferences):
            if not isinstance(conf_id, str) or not conf_id:
                continue

            conf_regs = db.reference(f"conferences/{conf_id}/registrations").get() or {}
            for reg_id, reg in _iter_dict(conf_regs):
                if not isinstance(reg, dict):
                    continue
                reg_email = (reg.get("email") or reg.get("user_email") or "").strip().lower()
                reg_uid = (reg.get("user_id") or "").strip()
                if reg_uid == uid or (reg_email and reg_email == email.lower()):
                    _maybe_delete_rtdb_path(f"conferences/{conf_id}/registrations/{reg_id}", dry_run=dry_run)

            conf_papers = db.reference(f"conferences/{conf_id}/paper_submissions").get() or {}
            for paper_id, paper in _iter_dict(conf_papers):
                if not isinstance(paper, dict):
                    continue
                paper_email = (paper.get("user_email") or paper.get("email") or "").strip().lower()
                paper_uid = (paper.get("user_id") or "").strip()
                if paper_uid == uid or (paper_email and paper_email == email.lower()):
                    _maybe_delete_rtdb_path(f"conferences/{conf_id}/paper_submissions/{paper_id}", dry_run=dry_run)
    except Exception as e:
        report["errors"].append(f"nested conference cleanup failed: {e}")

    # 5) Finally delete Firebase Auth user
    try:
        if dry_run:
            print(f"[dry-run] auth delete uid {uid} ({email})")
            report["auth_deleted"] = True
        else:
            auth.delete_user(uid)
            print(f"auth deleted uid {uid} ({email})")
            report["auth_deleted"] = True
    except Exception as e:
        report["errors"].append(f"auth delete_user failed: {e}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Purge Firebase Auth + RTDB + Storage data for users by email.")
    parser.add_argument("--email", action="append", default=[], help="Email to purge. Can be used multiple times.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without deleting anything.")
    args = parser.parse_args()

    if not args.email:
        raise SystemExit("Provide at least one --email.")

    _init_firebase()

    started = datetime.utcnow().isoformat() + "Z"
    print(f"started {started} dry_run={args.dry_run}")

    reports = []
    for email in args.email:
        email = (email or "").strip()
        if not email:
            continue
        print(f"\n=== purge {email} ===")
        reports.append(purge_user_by_email(email, dry_run=args.dry_run))

    print("\n=== summary ===")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
