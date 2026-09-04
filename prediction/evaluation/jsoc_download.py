"""Manual JSOC FITS download utilities for offline analysis."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import drms
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


def download_latest_fits_from_jsoc(
    email: str | None = None,
    out_dir: str | Path = "data/hmi_fits/",
    filename: str | None = None,
) -> Path:
    """Download the latest HMI 720-second magnetogram FITS export from JSOC."""
    email = email or os.environ.get("JSOC_EMAIL", "").strip()
    if not email:
        raise ValueError("Missing JSOC email. Set environment variable JSOC_EMAIL.")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = drms.Client(email=email)

    if not client.check_email(email):
        raise ValueError(
            "This email is not registered with JSOC exports. "
            "Register it at http://jsoc.stanford.edu/ajax/register_email.html"
        )

    latest_keys = client.query("hmi.M_720s", key="T_REC, CAMERA", n=-1)
    if latest_keys is None or latest_keys.empty:
        raise RuntimeError("No latest hmi.M_720s record found.")

    row = latest_keys.iloc[0]
    record = f"hmi.M_720s[{row['T_REC']}][{row['CAMERA']}]{{magnetogram}}"
    logger.info("Requesting JSOC FITS export for %s", record)

    request = client.export(record, method="url", protocol="fits", email=email)
    if not request.wait(timeout=120):
        raise TimeoutError(f"JSOC export timed out for {record}")
    if request.urls is None or request.urls.empty:
        raise RuntimeError(f"No FITS URL returned for record {record}")
    if request.data is None or request.data.empty:
        raise RuntimeError(f"No export metadata returned for record {record}")

    server_filename = str(request.data.iloc[0]["filename"])
    final_path = out_dir / filename if filename else out_dir / server_filename
    if final_path.exists():
        return final_path

    downloaded = request.download(out_dir)
    if downloaded is None or downloaded.empty:
        raise RuntimeError("JSOC FITS download failed")

    downloaded_path = Path(downloaded.iloc[0]["download"])
    if filename and downloaded_path != final_path:
        downloaded_path.replace(final_path)
        return final_path
    return downloaded_path
