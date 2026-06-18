from app.agents.research_engine import public_search_pipeline as pipeline


def test_pipeline_filters_single_character_baike_and_dedupes():
    results = [
        {"title": "欣（汉语汉字）_百度百科", "url": "https://baike.baidu.com/item/%E6%AC%A3/4636736", "content": "字典解释"},
        {"title": "欣旺达2024年年度报告", "url": "https://www.cninfo.com.cn/new/disclosure/detail", "content": "营业收入 净利润"},
        {"title": "欣旺达2024年年度报告重复", "url": "https://www.cninfo.com.cn/new/disclosure/detail#abc", "content": "重复"},
    ]

    output = pipeline.process_public_search_results(provider_results=results, category="financial", query="欣旺达 年报", crawl_enabled=False)

    assert output["stats"]["cleaned_count"] == 1
    assert output["stats"]["filtered_count"] == 2
    assert output["evidence"][0]["source_type"] == "exchange_announcement"
    assert output["evidence"][0]["trust_level"] == "high"


def test_pipeline_extracts_legal_fields_from_search_result():
    results = [{
        "title": "药明康德行政处罚公告",
        "url": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
        "content": "行政处罚决定书显示罚款2亿元，案号（2024）沪01民初123号。",
    }]

    output = pipeline.process_public_search_results(provider_results=results, category="legal", query="药明康德 行政处罚", crawl_enabled=False)
    fields = output["evidence"][0]["metadata"]["extracted_fields"]["legal_signals"]

    assert "行政处罚" in fields["signal_types"]
    assert fields["amounts"]
    assert fields["case_numbers"]


def test_pipeline_generates_crawled_evidence(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "ENABLE_CRAWL4AI_READER", True)
    monkeypatch.setattr(pipeline.settings, "CRAWL4AI_MAX_PAGES_PER_TASK", 2)
    monkeypatch.setattr(
        pipeline,
        "_get_crawl4ai_reader",
        lambda: lambda url, query_context, max_chars=8000: {
            "success": True,
            "url": url,
            "title": "士兰微年报经营讨论",
            "cleaned_markdown": "公司主营业务为集成电路和半导体分立器件，行业竞争格局加剧，政策支持国产替代。",
            "text_excerpt": "公司主营业务为集成电路和半导体分立器件。",
            "metadata": {},
        },
    )
    results = [{"title": "士兰微年报", "url": "https://www.sse.com.cn/disclosure", "content": "年报"}]

    output = pipeline.process_public_search_results(provider_results=results, category="industry", query="士兰微 行业", crawl_enabled=True)

    assert output["stats"]["crawl_attempt_count"] == 1
    assert any(item["source_type"] == "crawled_web_page" for item in output["evidence"])
    crawled = [item for item in output["evidence"] if item["source_type"] == "crawled_web_page"][0]
    assert "industry_anchors" in crawled["metadata"]["extracted_fields"]
