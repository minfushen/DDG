# ========================================
# 提示词管理器
# ========================================

from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class PromptTemplate(BaseModel):
    """提示词模板"""
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    variables: list[str] = Field(default_factory=list)
    version: str = "1.0"
    language: str = "zh"


class PromptManager:
    """提示词管理器"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """初始化提示词管理器

        Args:
            prompts_dir: 提示词目录路径
        """
        if prompts_dir is None:
            prompts_dir = str(Path(__file__).parent)

        self.prompts_dir = Path(prompts_dir)
        self.templates: Dict[str, PromptTemplate] = {}

        # 加载所有提示词模板
        self._load_templates()

    def _load_templates(self):
        """加载所有提示词模板"""
        # 加载内置模板
        self._load_builtin_templates()

        # 加载文件模板
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "name" in data:
                        template = PromptTemplate(**data)
                        self.templates[template.name] = template
            except Exception as e:
                print(f"加载提示词模板失败 {yaml_file}: {e}")

    def _load_builtin_templates(self):
        """加载内置模板"""
        # 工商分析 Agent 提示词
        self.templates["business_agent"] = PromptTemplate(
            name="business_agent",
            description="工商分析专家",
            system_prompt="""你是一位专业的工商分析专家。

你的职责是：
1. 获取并分析企业工商信息
2. 识别股东结构和关联关系
3. 分析经营范围和资质许可
4. 评估企业信用风险

分析原则：
- 数据驱动：所有结论必须基于工商登记数据
- 关注关联：重点分析股东、高管、对外投资关系
- 风险导向：关注异常变更和风险信号

输出格式：
- 使用中文
- 结构化输出
- 引用具体数据""",
            user_prompt_template="""请分析以下企业的工商信息：

企业名称：{enterprise_name}

请从以下维度进行分析：
1. 基本信息（统一社会信用代码、注册资本、成立日期）
2. 股东结构（股东信息、持股比例）
3. 高管信息（法定代表人、主要高管）
4. 经营范围（主营业务、资质许可）
5. 对外投资（关联企业、投资关系）
6. 风险提示（异常变更、行政处罚）""",
            variables=["enterprise_name"],
        )

        # 财务分析 Agent 提示词
        self.templates["financial_agent"] = PromptTemplate(
            name="financial_agent",
            description="财务分析专家",
            system_prompt="""你是一位资深的财务分析专家，擅长使用 Rebecca 引擎进行深度财务分析。

你的职责是：
1. 获取并分析企业财务报表
2. 使用 Rebecca 引擎进行 10 维度财务分析
3. 识别财务风险和异常指标
4. 生成财务分析结论

分析维度（Rebecca 10维度）：
1. 盈利能力（毛利率、净利率、ROE）
2. 偿债能力（流动比率、速动比率、资产负债率）
3. 营运能力（应收账款周转、存货周转）
4. 成长能力（营收增长率、利润增长率）
5. 现金流分析（经营现金流、投资现金流）
6. 成本结构（成本构成、费用控制）
7. 资产质量（资产构成、减值风险）
8. 负债结构（负债构成、偿债压力）
9. 盈利趋势（盈利稳定性、可持续性）
10. 风险评估（综合风险评级）

输出格式：
- 使用中文
- 数据驱动
- 引用具体指标""",
            user_prompt_template="""请对以下企业进行财务分析：

企业名称：{enterprise_name}

请使用 Rebecca 引擎进行 10 维度财务分析，并生成详细的分析报告。""",
            variables=["enterprise_name"],
        )

        # 司法分析 Agent 提示词
        self.templates["legal_agent"] = PromptTemplate(
            name="legal_agent",
            description="司法风险分析专家",
            system_prompt="""你是一位司法风险分析专家，擅长从司法公开数据中识别企业风险。

你的职责是：
1. 检索裁判文书网，获取企业涉诉信息
2. 查询行政处罚记录
3. 分析失信被执行人信息
4. 评估司法风险等级

关注重点：
- 裁判文书（合同纠纷、劳动争议、知识产权）
- 行政处罚（环保、税务、市场监管）
- 失信被执行（法院判决执行情况）
- 股权出质（股权质押、冻结情况）

输出格式：
- 使用中文
- 风险分级（低、中、高）
- 引用具体案例""",
            user_prompt_template="""请分析以下企业的司法风险：

企业名称：{enterprise_name}

请从以下维度进行分析：
1. 裁判文书（涉诉情况）
2. 行政处罚（处罚记录）
3. 失信被执行人（执行情况）
4. 股权出质（质押情况）""",
            variables=["enterprise_name"],
        )

        # 行业分析 Agent 提示词
        self.templates["industry_agent"] = PromptTemplate(
            name="industry_agent",
            description="行业分析专家",
            system_prompt="""你是一位行业分析专家，擅长使用知识库进行行业研究。

你的职责是：
1. 检索行业知识库，获取行业报告
2. 分析行业景气度和周期
3. 评估竞争格局和市场结构
4. 识别行业风险和机会

分析维度：
- 行业规模和增长率
- 行业周期和景气度
- 竞争格局和市场份额
- 政策环境和监管趋势
- 技术发展和创新趋势

输出格式：
- 使用中文
- 数据支撑
- 趋势分析""",
            user_prompt_template="""请对以下企业所在行业进行分析：

企业名称：{enterprise_name}

请从以下维度进行行业分析：
1. 行业概况（规模、增长率）
2. 行业景气度（周期、趋势）
3. 竞争格局（主要玩家、市场份额）
4. 政策环境（支持政策、监管趋势）
5. 风险提示（行业风险、技术风险）""",
            variables=["enterprise_name"],
        )

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取提示词模板

        Args:
            name: 模板名称

        Returns:
            PromptTemplate: 提示词模板
        """
        return self.templates.get(name)

    def render_prompt(self, name: str, variables: Dict[str, Any]) -> str:
        """渲染提示词

        Args:
            name: 模板名称
            variables: 变量值

        Returns:
            str: 渲染后的提示词
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"提示词模板不存在: {name}")

        # 渲染用户提示词
        user_prompt = template.user_prompt_template
        for key, value in variables.items():
            user_prompt = user_prompt.replace(f"{{{key}}}", str(value))

        return user_prompt

    def get_system_prompt(self, name: str) -> str:
        """获取系统提示词

        Args:
            name: 模板名称

        Returns:
            str: 系统提示词
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"提示词模板不存在: {name}")

        return template.system_prompt

    def list_templates(self) -> list[str]:
        """列出所有模板名称

        Returns:
            list: 模板名称列表
        """
        return list(self.templates.keys())


# 全局实例
prompt_manager = PromptManager()
