import io
import zipfile
from unittest.mock import MagicMock

import httpx
import pytest

from app.services.mineru_client import (
    MinerUError,
    _get_pdf_page_count,
    _split_pdf_bytes,
    extract_local_pdf,
    parse_mineru_zip,
    poll_batch_results,
    submit_local_files,
)


def _fake_zip_bytes(text: str) -> bytes:
    """Create an in-memory zip containing full.md with the given text."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("full.md", text)
    return buf.getvalue()


def _fake_client_class(put_resp=None, get_resp=None):
    """Return a fake httpx.Client class that yields a fake client instance."""

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def put(self, url, **kwargs):
            if put_resp is not None:
                return put_resp
            raise ValueError(f"unexpected PUT {url}")

        def get(self, url, **kwargs):
            if get_resp is not None:
                return get_resp
            raise ValueError(f"unexpected GET {url}")

    return FakeClient


def test_submit_local_files_success(monkeypatch, tmp_path):
    pdf = tmp_path / "demo.pdf"
    pdf.write_bytes(b"pdf content")

    post_resp = MagicMock()
    post_resp.raise_for_status = lambda: None
    post_resp.json.return_value = {
        "code": 0,
        "data": {
            "batch_id": "batch-123",
            "file_urls": ["https://upload.example.com/1"],
        },
        "msg": "ok",
    }

    put_resp = MagicMock()
    put_resp.raise_for_status = lambda: None

    def fake_post(url, **kwargs):
        assert "/api/v4/file-urls/batch" in url
        return post_resp

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("app.services.mineru_client.httpx.Client", _fake_client_class(put_resp=put_resp))

    batch_id = submit_local_files([str(pdf)])
    assert batch_id == "batch-123"


def test_submit_local_files_api_error(monkeypatch, tmp_path):
    pdf = tmp_path / "demo.pdf"
    pdf.write_bytes(b"pdf content")

    post_resp = MagicMock()
    post_resp.raise_for_status = lambda: None
    post_resp.json.return_value = {"code": -500, "msg": "param error"}

    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: post_resp)

    with pytest.raises(MinerUError):
        submit_local_files([str(pdf)])


def test_poll_batch_results_done(monkeypatch):
    get_resp = MagicMock()
    get_resp.raise_for_status = lambda: None
    get_resp.json.return_value = {
        "code": 0,
        "data": {
            "extract_result": [
                {"file_name": "demo.pdf", "state": "done", "full_zip_url": "https://zip.example.com/1.zip"}
            ]
        },
        "msg": "ok",
    }

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: get_resp)

    results = poll_batch_results("batch-123", timeout_seconds=1, interval_seconds=0)
    assert len(results) == 1
    assert results[0]["state"] == "done"


def test_parse_mineru_zip_extracts_markdown_and_tables():
    md = "# 标题\n\n| 产品 | 收入 | 占比 |\n|------|------|------|\n| A | 100 | 50% |\n| B | 100 | 50% |\n"
    zip_bytes = _fake_zip_bytes(md)

    parsed = parse_mineru_zip(zip_bytes)
    assert "# 标题" in parsed["text"]
    assert len(parsed["tables"]) == 1
    assert parsed["tables"][0][0] == ["产品", "收入", "占比"]
    assert parsed["tables"][0][1] == ["A", "100", "50%"]


def test_extract_local_pdf_end_to_end(monkeypatch, tmp_path):
    pdf = tmp_path / "demo.pdf"
    pdf.write_bytes(b"pdf content")

    post_resp = MagicMock()
    post_resp.raise_for_status = lambda: None
    post_resp.json.return_value = {
        "code": 0,
        "data": {
            "batch_id": "batch-abc",
            "file_urls": ["https://upload.example.com/1"],
        },
        "msg": "ok",
    }

    put_resp = MagicMock()
    put_resp.raise_for_status = lambda: None

    poll_get_resp = MagicMock()
    poll_get_resp.raise_for_status = lambda: None
    poll_get_resp.json.return_value = {
        "code": 0,
        "data": {
            "extract_result": [
                {"file_name": "demo.pdf", "state": "done", "full_zip_url": "https://zip.example.com/1.zip"}
            ]
        },
        "msg": "ok",
    }

    zip_get_resp = MagicMock()
    zip_get_resp.raise_for_status = lambda: None
    zip_get_resp.content = _fake_zip_bytes("# 报告\n\n正文内容。\n")

    def fake_poll_get(url, **kwargs):
        assert "/extract-results/batch/" in url
        return poll_get_resp

    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: post_resp)
    monkeypatch.setattr(httpx, "get", fake_poll_get)
    monkeypatch.setattr(
        "app.services.mineru_client.httpx.Client",
        _fake_client_class(put_resp=put_resp, get_resp=zip_get_resp),
    )

    result = extract_local_pdf(str(pdf))
    assert result["success"] is True
    assert result["metadata"]["parser_used"] == "mineru"
    assert "# 报告" in result["text"]


def test_get_pdf_page_count():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 50), f"page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    assert _get_pdf_page_count(pdf_bytes) == 3


def test_split_pdf_bytes():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((50, 50), f"page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    chunks = _split_pdf_bytes(pdf_bytes, max_pages=2)
    assert len(chunks) == 3
    assert chunks[0][:2] == (1, 2)
    assert chunks[1][:2] == (3, 4)
    assert chunks[2][:2] == (5, 5)

    # Verify each chunk has the expected number of pages.
    for start, end, chunk_bytes in chunks:
        chunk_doc = fitz.open(stream=chunk_bytes, filetype="pdf")
        assert len(chunk_doc) == end - start + 1
        chunk_doc.close()
