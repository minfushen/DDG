from app.agents.tools.pdf_extraction_engine import (
    download_pdf,
    extract_pdf,
    extract_with_pdfplumber,
    extract_with_pymupdf,
)


def test_extract_pdf_empty_bytes():
    result = extract_pdf(b"")
    assert result["success"] is False
    assert result["error"]


def test_extract_pdf_with_pdfplumber_text(monkeypatch):
    long_text = "2025年年度报告\n" + "第三节 经营情况讨论与分析\n公司主营半导体。" * 20

    def fake_extract(_bytes):
        return {
            "success": True,
            "text": long_text,
            "tables": [],
            "metadata": {"page_count": 1, "parser_used": "pdfplumber"},
            "error": "",
        }

    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_pdfplumber", fake_extract)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._pdfplumber_available", lambda: True)

    result = extract_pdf(b"fake")
    assert result["success"] is True
    assert result["metadata"]["parser_used"] == "pdfplumber"


def test_extract_pdf_fallback_to_pymupdf(monkeypatch):
    def fake_pdfplumber(_bytes):
        return {
            "success": True,
            "text": "x",
            "tables": [],
            "metadata": {"page_count": 1, "parser_used": "pdfplumber"},
            "error": "",
        }

    def fake_pymupdf(_bytes):
        return {
            "success": True,
            "text": "2025年年度报告\n经营情况讨论与分析\n公司主营半导体。",
            "tables": [],
            "metadata": {"page_count": 1, "parser_used": "pymupdf"},
            "error": "",
        }

    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_pdfplumber", fake_pdfplumber)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_pymupdf", fake_pymupdf)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._pdfplumber_available", lambda: True)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._pymupdf_available", lambda: True)

    result = extract_pdf(b"fake")
    assert result["success"] is True
    assert result["metadata"]["parser_used"] == "pymupdf"


def test_download_pdf_size_guard(monkeypatch):
    import httpx

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=64 * 1024):
            chunk = b"x" * (1024 * 1024)
            for _ in range(60):
                yield chunk

    monkeypatch.setattr(httpx, "stream", lambda method, url, **kwargs: FakeStream())

    result = download_pdf("https://example.com/big.pdf", max_size_mb=50)
    assert result is None


def test_extract_pdf_uses_mineru_when_enabled(monkeypatch):
    def fake_mineru(_bytes):
        return {
            "success": True,
            "text": "MinerU parsed markdown",
            "tables": [],
            "metadata": {"page_count": 2, "parser_used": "mineru"},
            "error": "",
        }

    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_mineru", fake_mineru)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._mineru_enabled", lambda: True)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._mineru_available", lambda: True)

    result = extract_pdf(b"fake")
    assert result["success"] is True
    assert result["metadata"]["parser_used"] == "mineru"
    assert result["text"] == "MinerU parsed markdown"


def test_extract_pdf_fallback_to_local_when_mineru_fails(monkeypatch):
    def fake_mineru(_bytes):
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "mineru"},
            "error": "MinerU service error",
        }

    def fake_pdfplumber(_bytes):
        return {
            "success": True,
            "text": "local fallback text " * 10,
            "tables": [],
            "metadata": {"page_count": 1, "parser_used": "pdfplumber"},
            "error": "",
        }

    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_mineru", fake_mineru)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine.extract_with_pdfplumber", fake_pdfplumber)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._mineru_enabled", lambda: True)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._mineru_available", lambda: True)
    monkeypatch.setattr("app.agents.tools.pdf_extraction_engine._pdfplumber_available", lambda: True)

    result = extract_pdf(b"fake")
    assert result["success"] is True
    assert result["metadata"]["parser_used"] == "pdfplumber"
