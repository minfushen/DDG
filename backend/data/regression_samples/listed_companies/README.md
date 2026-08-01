# 上市公司回归样例

本目录保存 10 家上市公司的回归测试配置，用于报告质量评测、行业识别、财务诊断和正文级 evidence 引用检查。

## 样例清单

| 文件 | 公司 | 股票代码 | 重点覆盖 |
| --- | --- | --- | --- |
| `silan_micro.json` | 士兰微 | 600460 | 半导体 IDM、行业错分、财务压力 |
| `maxscend_microelectronics.json` | 卓胜微 | 300782 | 射频前端、毛利率、研发投入 |
| `wingtech_technology.json` | 闻泰科技 | 600745 | 半导体 + ODM、多业务结构、司法公告 |
| `sunwoda.json` | 欣旺达 | 300207 | 锂电池、应收、经营现金流 |
| `chuaneng_power.json` | 川能动力 | 000155 | 新能源资源、项目建设、政策周期 |
| `lens_technology.json` | 蓝思科技 | 300433 | 消费电子精密制造、简称识别 |
| `wuxi_apptec.json` | 药明康德 | 603259 | CXO、海外合规、政策风险 |
| `sungrow_power.json` | 阳光电源 | 300274 | 光伏逆变器、储能、海外收入 |
| `muyuan_foods.json` | 牧原股份 | 002714 | 猪周期、生物资产、现金流 |
| `aero_engine_corporation.json` | 航发动力 | 600893 | 航空发动机、军工订单、应收存货 |

## 配置字段

- `sample_id`：样例唯一 ID。
- `company_name`：上市公司全称。
- `display_name`：前端输入和报告展示常用简称。
- `stock_code` / `exchange`：证券代码和交易所。
- `test_input`：建议用于端到端测试的首页输入。
- `expected_aliases`：主体识别评测使用的公司别名。
- `expected_industry_keywords`：行业识别评测使用的关键行业词。
- `focus_areas`：人工审查报告时重点看哪些内容。
- `quality_gate`：该样例的最低质量门槛。

## 评测命令

```bash
cd backend
./venv312/bin/python -m app.agents.research_engine.report_quality_evaluator \
  /path/to/generated_report.json \
  --sample regression_samples/listed_companies/silan_micro.json \
  --pretty
```

后续可以新增批量脚本，自动读取 `index.json`，逐个跑首页创建任务、保存报告 JSON、执行质量评测并生成 Markdown 汇总。
