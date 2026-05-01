// ========================================
// 印尼企业演示数据 — PT Sinar Mas Teknologi
// PSAK 三表 + 尽调清单 + 思维链推理
// ========================================

import type {
  FinancialStatement, CrossValidationRule,
  ChecklistItem, CoTStep,
} from '../types/psak';

// ── 企业基本信息 ─────────────────────────────────────
export const indoEnterprise = {
  id: 'ent-id-001',
  name: 'PT Sinar Mas Teknologi',
  nameZh: '金光科技有限公司',
  npwp: '01.234.567.8-012.000',         // 印尼税号
  industry: 'Teknologi Informasi',
  industryZh: '信息技术服务业',
  region: 'Jakarta Selatan, DKI Jakarta',
  regionZh: '雅加达南部',
  registeredCapital: 50000,               // IDR 百万
  establishedDate: '2016-08-20',
  legalPerson: 'Budi Santoso',
  legalPersonZh: '布迪·桑托索',
  employeeCount: 342,
  businessScope: 'Pengembangan perangkat lunak, layanan cloud, konsultasi TI',
  businessScopeZh: '软件开发、云服务、IT 咨询',
};

// ── PSAK 资产负债表 (Neraca) ──────────────────────────
export const balanceSheet: FinancialStatement = {
  type: 'balance_sheet',
  title: 'Neraca',
  titleZh: '资产负债表',
  items: [
    // 资产
    { id: 'bs-cash', label: 'Kas dan Setara Kas', labelZh: '现金及等价物', currentYear: 45000, priorYear: 32000, psakCode: 'PSAK 1', indent: 0, linkedItems: ['cf-end-cash'] },
    { id: 'bs-receivable', label: 'Piutang Usaha', labelZh: '应收账款', currentYear: 38000, priorYear: 29000, psakCode: 'PSAK 72', indent: 0 },
    { id: 'bs-inventory', label: 'Persediaan', labelZh: '存货', currentYear: 12000, priorYear: 9500, psakCode: 'PSAK 2', indent: 0 },
    { id: 'bs-other-ca', label: 'Aset Lancar Lainnya', labelZh: '其他流动资产', currentYear: 5000, priorYear: 4500, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-total-ca', label: 'Total Aset Lancar', labelZh: '流动资产合计', currentYear: 100000, priorYear: 75000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    { id: 'bs-ppe', label: 'Aset Tetap', labelZh: '固定资产', currentYear: 85000, priorYear: 72000, psakCode: 'PSAK 16', indent: 0 },
    { id: 'bs-intangible', label: 'Aset Tak Berwujud', labelZh: '无形资产', currentYear: 15000, priorYear: 18000, psakCode: 'PSAK 19', indent: 0 },
    { id: 'bs-total-nca', label: 'Total Aset Non-Lancar', labelZh: '非流动资产合计', currentYear: 100000, priorYear: 90000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    { id: 'bs-total-assets', label: 'TOTAL ASET', labelZh: '资产总计', currentYear: 200000, priorYear: 165000, psakCode: 'PSAK 1', indent: 0, isTotal: true, linkedItems: ['bs-total-le'] },

    // 负债
    { id: 'bs-payable', label: 'Utang Usaha', labelZh: '应付账款', currentYear: 28000, priorYear: 22000, psakCode: 'PSAK 72', indent: 0 },
    { id: 'bs-short-debt', label: 'Utang Bank Jangka Pendek', labelZh: '短期银行借款', currentYear: 20000, priorYear: 15000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-other-cl', label: 'Liabilitas Jangka Pendek Lainnya', labelZh: '其他流动负债', currentYear: 7000, priorYear: 5000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-total-cl', label: 'Total Liabilitas Jangka Pendek', labelZh: '流动负债合计', currentYear: 55000, priorYear: 42000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    { id: 'bs-long-debt', label: 'Utang Bank Jangka Panjang', labelZh: '长期银行借款', currentYear: 35000, priorYear: 30000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-other-ncl', label: 'Liabilitas Jangka Panjang Lainnya', labelZh: '其他非流动负债', currentYear: 5000, priorYear: 3000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-total-ncl', label: 'Total Liabilitas Jangka Panjang', labelZh: '非流动负债合计', currentYear: 40000, priorYear: 33000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    { id: 'bs-total-liab', label: 'TOTAL LIABILITAS', labelZh: '负债合计', currentYear: 95000, priorYear: 75000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    // 权益
    { id: 'bs-capital', label: 'Modal Disetor', labelZh: '实收资本', currentYear: 35000, priorYear: 35000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-retained', label: 'Laba Ditahan', labelZh: '留存收益', currentYear: 68000, priorYear: 52250, psakCode: 'PSAK 1', indent: 0, linkedItems: ['is-net-profit'] },
    { id: 'bs-other-eq', label: 'Ekuitas Lainnya', labelZh: '其他权益', currentYear: 2000, priorYear: 2750, psakCode: 'PSAK 1', indent: 0 },
    { id: 'bs-total-eq', label: 'TOTAL EKUITAS', labelZh: '权益合计', currentYear: 105000, priorYear: 90000, psakCode: 'PSAK 1', indent: 0, isTotal: true },

    { id: 'bs-total-le', label: 'TOTAL LIABILITAS DAN EKUITAS', labelZh: '负债和权益总计', currentYear: 200000, priorYear: 165000, psakCode: 'PSAK 1', indent: 0, isTotal: true },
  ],
};

// ── PSAK 利润表 (Laporan Laba Rugi) ──────────────────
export const incomeStatement: FinancialStatement = {
  type: 'income_statement',
  title: 'Laporan Laba Rugi',
  titleZh: '利润表',
  items: [
    { id: 'is-revenue', label: 'Pendapatan', labelZh: '营业收入', currentYear: 185000, priorYear: 148000, psakCode: 'PSAK 72', indent: 0 },
    { id: 'is-cogs', label: 'Beban Pokok Pendapatan', labelZh: '营业成本', currentYear: -105000, priorYear: -86000, psakCode: 'PSAK 72', indent: 0 },
    { id: 'is-gross', label: 'Laba Kotor', labelZh: '毛利润', currentYear: 80000, priorYear: 62000, psakCode: 'PSAK 72', indent: 0, isTotal: true },
    { id: 'is-opex', label: 'Beban Operasional', labelZh: '运营费用', currentYear: -38000, priorYear: -30000, psakCode: 'PSAK 1', indent: 0 },
    { id: 'is-depreciation', label: 'Beban Penyusutan', labelZh: '折旧摊销', currentYear: -12000, priorYear: -10000, psakCode: 'PSAK 16', indent: 0 },
    { id: 'is-operating', label: 'Laba Operasional', labelZh: '营业利润', currentYear: 30000, priorYear: 22000, psakCode: 'PSAK 1', indent: 0, isTotal: true },
    { id: 'is-interest', label: 'Beban Bunga', labelZh: '利息支出', currentYear: -5500, priorYear: -4200, psakCode: 'PSAK 1', indent: 0 },
    { id: 'is-other-income', label: 'Pendapatan Lain', labelZh: '其他收入', currentYear: 1250, priorYear: 800, psakCode: 'PSAK 1', indent: 0 },
    { id: 'is-pretax', label: 'Laba Sebelum Pajak', labelZh: '税前利润', currentYear: 25750, priorYear: 18600, psakCode: 'PSAK 1', indent: 0, isTotal: true },
    { id: 'is-tax', label: 'Beban Pajak', labelZh: '所得税费用', currentYear: -10000, priorYear: -7250, psakCode: 'PSAK 46', indent: 0 },
    { id: 'is-net-profit', label: 'Laba Bersih', labelZh: '净利润', currentYear: 15750, priorYear: 11350, psakCode: 'PSAK 1', indent: 0, isTotal: true, linkedItems: ['bs-retained', 'cf-net-profit'] },
  ],
};

// ── PSAK 现金流量表 (Laporan Arus Kas) ────────────────
export const cashFlowStatement: FinancialStatement = {
  type: 'cash_flow',
  title: 'Laporan Arus Kas',
  titleZh: '现金流量表',
  items: [
    { id: 'cf-net-profit', label: 'Laba Bersih', labelZh: '净利润', currentYear: 15750, priorYear: 11350, psakCode: 'PSAK 2', indent: 0, linkedItems: ['is-net-profit'] },
    { id: 'cf-depreciation', label: 'Penyusutan dan Amortisasi', labelZh: '折旧与摊销', currentYear: 12000, priorYear: 10000, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-working-capital', label: 'Perubahan Modal Kerja', labelZh: '营运资本变动', currentYear: -8750, priorYear: -5350, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-operating', label: 'Arus Kas dari Operasi', labelZh: '经营活动现金流', currentYear: 19000, priorYear: 16000, psakCode: 'PSAK 2', indent: 0, isTotal: true },
    { id: 'cf-capex', label: 'Pembelian Aset Tetap', labelZh: '购置固定资产', currentYear: -25000, priorYear: -18000, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-investing', label: 'Arus Kas dari Investasi', labelZh: '投资活动现金流', currentYear: -25000, priorYear: -18000, psakCode: 'PSAK 2', indent: 0, isTotal: true },
    { id: 'cf-borrowing', label: 'Penerimaan Pinjaman', labelZh: '借款收入', currentYear: 25000, priorYear: 10000, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-repayment', label: 'Pembayaran Pinjaman', labelZh: '偿还借款', currentYear: -6000, priorYear: -4000, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-financing', label: 'Arus Kas dari Pendanaan', labelZh: '筹资活动现金流', currentYear: 19000, priorYear: 6000, psakCode: 'PSAK 2', indent: 0, isTotal: true },
    { id: 'cf-net-change', label: 'Perubahan Bersih Kas', labelZh: '现金净变动', currentYear: 13000, priorYear: 4000, psakCode: 'PSAK 2', indent: 0, isTotal: true },
    { id: 'cf-begin-cash', label: 'Kas Awal Periode', labelZh: '期初现金', currentYear: 32000, priorYear: 28000, psakCode: 'PSAK 2', indent: 0 },
    { id: 'cf-end-cash', label: 'Kas Akhir Periode', labelZh: '期末现金', currentYear: 45000, priorYear: 32000, psakCode: 'PSAK 2', indent: 0, isTotal: true, linkedItems: ['bs-cash'] },
  ],
};

export const psakStatements: FinancialStatement[] = [
  balanceSheet,
  incomeStatement,
  cashFlowStatement,
];

// ── 钩稽校验规则 ─────────────────────────────────────
export const crossValidationRules: CrossValidationRule[] = [
  {
    id: 'cv-1',
    rule: '资产总计 = 负债合计 + 权益合计',
    formula: 'BS.总资产 = BS.总负债 + BS.总权益',
    leftLabel: '资产总计 (Rp 200,000)',
    rightLabel: '负债+权益 (Rp 95,000 + Rp 105,000)',
    leftValue: 200000,
    rightValue: 200000,
    tolerance: 0,
    psakRef: 'PSAK 1 — Persamaan Akuntansi',
  },
  {
    id: 'cv-2',
    rule: '现金流量表期末现金 = 资产负债表现金',
    formula: 'CF.期末现金 = BS.现金及等价物',
    leftLabel: 'CF 期末现金 (Rp 45,000)',
    rightLabel: 'BS 现金 (Rp 45,000)',
    leftValue: 45000,
    rightValue: 45000,
    tolerance: 0,
    psakRef: 'PSAK 2 — Rekonsiliasi Kas',
  },
  {
    id: 'cv-3',
    rule: '利润表净利润链接至资产负债表留存收益',
    formula: 'IS.净利润 ⊂ BS.留存收益变动',
    leftLabel: 'IS 净利润 (Rp 15,750)',
    rightLabel: 'BS 留存收益变动 (Rp 15,750)',
    leftValue: 15750,
    rightValue: 15750,
    tolerance: 0,
    psakRef: 'PSAK 1 — Laba Ditahan',
  },
  {
    id: 'cv-4',
    rule: '现金流量表净利润 = 利润表净利润',
    formula: 'CF.净利润 = IS.净利润',
    leftLabel: 'CF 净利润 (Rp 15,750)',
    rightLabel: 'IS 净利润 (Rp 15,750)',
    leftValue: 15750,
    rightValue: 15750,
    tolerance: 0,
    psakRef: 'PSAK 2 — Metode Tidak Langsung',
  },
  {
    id: 'cv-5',
    rule: '流动比率 >= 1.5（行业警戒线）',
    formula: 'BS.流动资产 / BS.流动负债 >= 1.5',
    leftLabel: '流动比率 (100,000 / 55,000)',
    rightLabel: '行业阈值 (1.5)',
    leftValue: 1.82,
    rightValue: 1.5,
    tolerance: 0,
    psakRef: 'Internal — Rasio Lancar',
  },
  {
    id: 'cv-6',
    rule: '资产负债率 <= 60%（风控阈值）',
    formula: 'BS.总负债 / BS.总资产 <= 60%',
    leftLabel: '资产负债率 (95,000 / 200,000)',
    rightLabel: '风控阈值 (60%)',
    leftValue: 47.5,
    rightValue: 60,
    tolerance: 0,
    psakRef: 'Internal — Debt-to-Asset Ratio',
  },
];

// ── 尽调清单 ─────────────────────────────────────────
export const checklistItems: ChecklistItem[] = [
  // 财务资料 (6 项)
  { id: 'cl-1', category: 'financial', documentName: '2023年度审计报告', documentNameId: 'Laporan Audit Tahunan 2023', status: 'received', source: 'ai_extracted', aiConfidence: 98, extractedData: '无保留意见审计报告，总资产 Rp 200,000 juta', pageNumber: 3, fileName: 'Audit_Report_2023.pdf' },
  { id: 'cl-2', category: 'financial', documentName: '资产负债表', documentNameId: 'Neraca', status: 'received', source: 'ai_extracted', aiConfidence: 99, extractedData: '资产总计 Rp 200,000 juta，资产负债率 47.5%', pageNumber: 8, fileName: 'Audit_Report_2023.pdf' },
  { id: 'cl-3', category: 'financial', documentName: '利润表', documentNameId: 'Laporan Laba Rugi', status: 'received', source: 'ai_extracted', aiConfidence: 99, extractedData: '营业收入 Rp 185,000 juta，净利润 Rp 15,750 juta', pageNumber: 10, fileName: 'Audit_Report_2023.pdf' },
  { id: 'cl-4', category: 'financial', documentName: '现金流量表', documentNameId: 'Laporan Arus Kas', status: 'received', source: 'ai_extracted', aiConfidence: 97, extractedData: '经营活动现金流 Rp 19,000 juta', pageNumber: 12, fileName: 'Audit_Report_2023.pdf' },
  { id: 'cl-5', category: 'financial', documentName: '银行流水（近6个月）', documentNameId: 'Rekening Koran Bank', status: 'received', source: 'ai_extracted', aiConfidence: 95, extractedData: '月均流入 Rp 16,200 juta，主要来自客户回款', pageNumber: 1, fileName: 'Bank_Statement_6M.pdf' },
  { id: 'cl-6', category: 'financial', documentName: '纳税申报表', documentNameId: 'SPT Tahunan', status: 'pending', source: 'manual', aiConfidence: undefined, extractedData: undefined },

  // 法律文件 (5 项)
  { id: 'cl-7', category: 'legal', documentName: '公司注册证（Akta Pendirian）', documentNameId: 'Akta Pendirian Perusahaan', status: 'received', source: 'ai_extracted', aiConfidence: 96, extractedData: '2016年8月20日注册，注册资本 Rp 35,000 juta', pageNumber: 1, fileName: 'Akta_Pendirian.pdf' },
  { id: 'cl-8', category: 'legal', documentName: '营业执照（NIB）', documentNameId: 'Nomor Induk Berusaha', status: 'received', source: 'system', aiConfidence: 100, extractedData: 'NIB: 1234567890123，有效期至 2026-08-20', pageNumber: 1, fileName: 'NIB_Certificate.pdf' },
  { id: 'cl-9', category: 'legal', documentName: '股东名册', documentNameId: 'Daftar Pemegang Saham', status: 'received', source: 'ai_extracted', aiConfidence: 94, extractedData: 'Budi Santoso 60%, PT Sinar Mas Group 40%', pageNumber: 2, fileName: 'Akta_Pendirian.pdf' },
  { id: 'cl-10', category: 'legal', documentName: '董事会决议', documentNameId: 'Keputusan Direksi', status: 'overdue', source: 'manual' },
  { id: 'cl-11', category: 'legal', documentName: '诉讼/仲裁记录', documentNameId: 'Catatan Litigasi', status: 'received', source: 'ai_extracted', aiConfidence: 88, extractedData: '无未决诉讼，历史 1 起已结案（2021年）', pageNumber: 1, fileName: 'Litigation_Search.pdf' },

  // 经营资料 (4 项)
  { id: 'cl-12', category: 'operational', documentName: '主要客户合同', documentNameId: 'Kontrak Pelanggan Utama', status: 'received', source: 'ai_extracted', aiConfidence: 92, extractedData: 'Top 5 客户合同总额 Rp 92,500 juta/年', pageNumber: 1, fileName: 'Customer_Contracts.pdf' },
  { id: 'cl-13', category: 'operational', documentName: '员工花名册', documentNameId: 'Daftar Karyawan', status: 'received', source: 'ai_extracted', aiConfidence: 100, extractedData: '342 名员工，研发占比 58%', pageNumber: 1, fileName: 'Employee_Roster.xlsx' },
  { id: 'cl-14', category: 'operational', documentName: '经营场所照片', documentNameId: 'Foto Lokasi Usaha', status: 'pending', source: 'manual' },
  { id: 'cl-15', category: 'operational', documentName: 'IT 系统架构说明', documentNameId: 'Dokumentasi Arsitektur IT', status: 'pending', source: 'manual' },

  // 担保物 (3 项)
  { id: 'cl-16', category: 'collateral', documentName: '房产评估报告', documentNameId: 'Laporan Penilaian Properti', status: 'received', source: 'ai_extracted', aiConfidence: 91, extractedData: 'Jakarta 办公楼评估价值 Rp 95,000 juta', pageNumber: 5, fileName: 'Property_Valuation.pdf' },
  { id: 'cl-17', category: 'collateral', documentName: '不动产登记证', documentNameId: 'Sertifikat Hak Milik', status: 'received', source: 'ai_extracted', aiConfidence: 97, extractedData: 'SHM No. 001234，面积 2,500 m²', pageNumber: 1, fileName: 'SHM_Certificate.pdf' },
  { id: 'cl-18', category: 'collateral', documentName: '抵押登记证明', documentNameId: 'Bukti Pendaftaran Hipotik', status: 'overdue', source: 'manual' },

  // 合规文件 (2 项)
  { id: 'cl-19', category: 'compliance', documentName: '反洗钱自查报告', documentNameId: 'Laporan Self-Assessment AML', status: 'overdue', source: 'manual' },
  { id: 'cl-20', category: 'compliance', documentName: '环保合规证明', documentNameId: 'Sertifikat Kepatuhan Lingkungan', status: 'received', source: 'system', aiConfidence: 100, extractedData: 'ISO 14001 认证有效，至 2025-12-31', pageNumber: 1, fileName: 'ISO_14001.pdf' },
];

// ── 思维链推理步骤 ───────────────────────────────────
export const cotSteps: CoTStep[] = [
  {
    id: 'cot-1',
    phase: 'ingest',
    phaseLabel: '文件接收',
    description: '接收到 12 份文件，涵盖 PDF 审计报告、Excel 银行流水、图像扫描件',
    input: '12 files (8 PDF, 2 XLSX, 2 JPG)',
    output: '文件完整性检查通过，已按格式分类存储',
    duration: 1500,
    status: 'pending',
  },
  {
    id: 'cot-2',
    phase: 'classify',
    phaseLabel: '智能分类',
    description: '基于 OCR + NLP 模型自动识别文件类型，归类至 5 大尽调维度',
    input: '12 份原始文件',
    output: '财务 6 份 · 法律 5 份 · 经营 4 份 · 担保 3 份 · 合规 2 份（含重叠）',
    duration: 2200,
    status: 'pending',
  },
  {
    id: 'cot-3',
    phase: 'extract',
    phaseLabel: '信息提取',
    description: '从审计报告中提取 PSAK 三表结构化数据，识别 86 个财务指标',
    input: 'Audit_Report_2023.pdf (48 pages)',
    output: '资产负债表 21 项 · 利润表 11 项 · 现金流量表 12 项，提取置信度 ≥97%',
    duration: 3500,
    sourceRef: 'cl-1',
    sourcePage: 3,
    status: 'pending',
  },
  {
    id: 'cot-4',
    phase: 'extract',
    phaseLabel: '多语言识别',
    description: '识别印尼语会计科目，自动映射至中文标准科目名称',
    input: '印尼语原始科目 (e.g. "Piutang Usaha")',
    output: '86 个科目全部映射成功，PSAK → CAS 对应率 100%',
    duration: 1800,
    status: 'pending',
  },
  {
    id: 'cot-5',
    phase: 'validate',
    phaseLabel: '钩稽校验',
    description: '执行 PSAK 标准钩稽校验：资产=负债+权益、现金流期末=BS现金、净利润跨表一致',
    input: 'PSAK 三表结构化数据',
    output: '6 条校验规则全部通过，偏差率 0%',
    duration: 2500,
    sourceRef: 'cl-2',
    sourcePage: 8,
    status: 'pending',
  },
  {
    id: 'cot-6',
    phase: 'analyze',
    phaseLabel: '风险分析',
    description: '基于三表数据计算 12 项财务比率，对比行业均值评估风险等级',
    input: '财务比率矩阵 + 行业基准数据',
    output: '流动比率 1.82（行业 1.5）· ROE 15.0%（行业 12%）· 综合风险：中等',
    duration: 2000,
    status: 'pending',
  },
  {
    id: 'cot-7',
    phase: 'analyze',
    phaseLabel: '关联分析',
    description: '穿透股权关系图谱，识别实控人及关联方风险传导路径',
    input: '股东名册 + 工商数据',
    output: '实控人 Budi Santoso 持股 60%，关联企业 3 家，无异常担保',
    duration: 1800,
    sourceRef: 'cl-9',
    sourcePage: 2,
    status: 'pending',
  },
  {
    id: 'cot-8',
    phase: 'conclude',
    phaseLabel: '生成结论',
    description: '综合所有分析维度，生成尽调结论和授信建议',
    input: '全部分析结果汇总',
    output: '建议授信 Rp 50,000 juta，期限 1 年，利率 JIBOR+150BP',
    duration: 2500,
    status: 'pending',
  },
];

// ── AI Copilot 预制回复 ──────────────────────────────
export const copilotResponses: Record<string, string> = {
  '三表对比': `**PSAK 三表数据对比分析：**

📊 **资产负债表 (Neraca)**
- 总资产 Rp 200,000 juta，同比 +21.2%
- 资产负债率 47.5%，健康水平
- 流动比率 1.82，高于行业阈值 1.5

📈 **利润表 (Laporan Laba Rugi)**
- 营收 Rp 185,000 juta，同比 +25.0%
- 净利润率 8.5%（Rp 15,750 juta）
- ROE 15.0%，行业均值 12%

💰 **现金流量表 (Laporan Arus Kas)**
- 经营现金流 Rp 19,000 juta，正向
- 投资支出 Rp 25,000 juta（产能扩张）
- 筹资净流入 Rp 19,000 juta

**结论：** 三表联动校验通过，财务结构稳健。`,

  '风险摘要': `**PT Sinar Mas Teknologi 风险评估摘要：**

🟢 **低风险项：**
- 资产负债率 47.5%（阈值 60%）
- 流动比率 1.82（阈值 1.5）
- 无未决诉讼

🟡 **中风险项：**
- 前 5 大客户集中度 50%
- 应收账款周转天数延长至 75 天
- 资本开支 Rp 25,000 juta，占营收 13.5%

**综合评级：** 中等风险（Medium Risk）`,
};

// ── AI Copilot 命令 ──────────────────────────────────
export const copilotCommands = [
  { command: '/apply', label: '填入报告', description: '将分析结果自动填入报告对应位置' },
  { command: '/chart', label: '生成图表', description: '生成股权结构图或财务趋势图' },
  { command: '/summary', label: '风险摘要', description: '生成综合风险评估摘要' },
];
