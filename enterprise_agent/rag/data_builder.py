"""Deterministic enterprise corpus builder for the M1 RAG baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise_agent.tools.parse_doc import parse_document


BASE_COUNTS = {
    "policies": 80,
    "workflows": 40,
    "projects": 80,
    "meetings": 80,
    "contracts": 50,
    "reports": 30,
}

TYPE_ALIASES = {
    "policies": "policy",
    "workflows": "workflow",
    "projects": "project",
    "meetings": "meeting",
    "contracts": "contract",
    "reports": "report",
}

RAW_DIR = Path("enterprise_agent/data/raw")
GENERATOR_DIR = Path("enterprise_agent/data/generators")
STATS_PATH = Path("enterprise_agent/data/index/corpus_stats.json")
SOURCE_MANIFEST_PATH = Path("enterprise_agent/data/index/source_manifest.jsonl")
RAW_SUFFIXES = {".md", ".txt", ".pdf", ".docx", ".html", ".htm"}
MAX_RAW_BYTES = 10_000_000


def _target_counts(min_docs: int) -> dict[str, int]:
    counts = dict(BASE_COUNTS)
    extra = max(0, min_docs - sum(counts.values()))
    order = ("policies", "projects", "meetings", "contracts", "workflows", "reports")
    for index in range(extra):
        counts[order[index % len(order)]] += 1
    return counts


def _load_snippets(directory: Path) -> list[str]:
    if not directory.exists():
        return []

    snippets: list[str] = []
    for path in sorted(directory.glob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                snippets.append(text[:500])
    return snippets


def _iter_raw_paths(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        return []
    return sorted(
        path
        for path in raw_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in RAW_SUFFIXES
        and not path.name.endswith(".meta.json")
        and path.stat().st_size <= MAX_RAW_BYTES
    )


def _load_sidecar_metadata(path: Path) -> dict:
    sidecar = path.with_suffix(path.suffix + ".meta.json")
    if not sidecar.exists():
        return {}
    return json.loads(sidecar.read_text(encoding="utf-8"))


def _load_seed_documents(raw_dir: Path) -> list[dict]:
    seeds = []
    for path in _iter_raw_paths(raw_dir):
        try:
            parsed = parse_document(str(path))
        except Exception as exc:
            seeds.append(
                {
                    "source": path.name,
                    "doc_type": "general",
                    "title": path.stem,
                    "content": f"原始文件解析失败：{exc}",
                    "metadata": {
                        "path": str(path),
                        "raw_format": path.suffix.lower().lstrip("."),
                        "parse_error": str(exc),
                    },
                }
            )
            continue
        parsed["metadata"].update(_load_sidecar_metadata(path))
        parsed["metadata"].setdefault("source_url", "")
        parsed["metadata"].setdefault("seed_path", str(path))
        seeds.append(parsed)
    return seeds


def _seed_for(folder: str, index: int, seeds: list[dict]) -> dict | None:
    if not seeds:
        return None
    target_type = TYPE_ALIASES[folder]
    typed = [seed for seed in seeds if seed.get("doc_type") == target_type]
    candidates = typed or seeds
    return candidates[(index - 1) % len(candidates)]


def _topic(folder: str, index: int) -> str:
    topics = {
        "policies": [
            "差旅报销",
            "采购申请",
            "信息安全",
            "费用预算",
            "合同用印",
            "供应商准入",
            "远程办公",
            "客户数据保护",
        ],
        "workflows": [
            "8000 元采购申请",
            "合同审批",
            "会议纪要生成项目周报",
            "差旅报销提交",
            "供应商付款",
            "项目风险升级",
        ],
        "projects": [
            "A 项目",
            "B 项目",
            "客户成功平台",
            "财务共享中心",
            "智能客服迁移",
            "数据治理专项",
        ],
        "meetings": [
            "A 项目周会",
            "合同审批例会",
            "采购评审会",
            "项目风险复盘",
            "经营分析会",
            "交付协调会",
        ],
        "contracts": [
            "合同审批",
            "软件采购合同",
            "数据处理协议",
            "外包服务合同",
            "框架采购协议",
            "保密协议",
        ],
        "reports": [
            "项目周报",
            "A 项目风险报告",
            "采购合规月报",
            "合同审批统计",
            "差旅费用分析",
            "交付质量报告",
        ],
    }
    return topics[folder][(index - 1) % len(topics[folder])]


def _title(folder: str, index: int) -> str:
    noun = {
        "policies": "制度",
        "workflows": "流程",
        "projects": "档案",
        "meetings": "纪要",
        "contracts": "管理规程",
        "reports": "报告",
    }[folder]
    return f"{_topic(folder, index)}{noun} {index:03d}"


def _source_metadata(source: str, folder: str, seed: dict | None) -> dict:
    if not seed:
        return {
            "source": source,
            "doc_type": TYPE_ALIASES[folder],
            "source_url": "template_fallback",
            "seed_path": "template_fallback",
            "raw_format": "template",
            "seed_title": "",
            "is_expanded": True,
        }

    metadata = seed.get("metadata") or {}
    return {
        "source": source,
        "doc_type": TYPE_ALIASES[folder],
        "source_url": metadata.get("source_url") or "unknown_public_source",
        "seed_path": metadata.get("seed_path") or metadata.get("path") or seed.get("source"),
        "raw_format": metadata.get("raw_format") or "unknown",
        "seed_title": seed.get("title", ""),
        "is_expanded": True,
    }


def _body(folder: str, index: int, seed: dict | None, snippets: list[str]) -> str:
    topic = _topic(folder, index)
    title = _title(folder, index)
    amount = 5000 + (index % 12) * 1000
    owner = ["财务部", "采购部", "法务部", "项目管理办公室", "信息安全部"][index % 5]
    lines = [
        f"# {title}",
        "",
        "## 适用范围",
        f"本规程适用于{topic}相关事项，由{owner}负责制度解释、流程维护和执行监督。",
        f"适用于金额约 {amount} 元以上、需要跨部门留痕或形成项目档案的业务事项。",
        "所有申请、审批、用印、付款、会议结论和项目报告均应在对应系统中形成可追溯记录。",
        "",
    ]
    lines.extend(_natural_sections(folder, index, topic, owner, amount))
    lines.extend(_operational_sections(folder, index, topic, owner, amount))
    lines.append("")
    return "\n".join(lines)


def _natural_sections(folder: str, index: int, topic: str, owner: str, amount: int) -> list[str]:
    builders = {
        "policies": _policy_sections,
        "workflows": _workflow_sections,
        "projects": _project_sections,
        "meetings": _meeting_sections,
        "contracts": _contract_sections,
        "reports": _report_sections,
    }
    return builders[folder](index, topic, owner, amount)


def _operational_sections(folder: str, index: int, topic: str, owner: str, amount: int) -> list[str]:
    case_id = f"{TYPE_ALIASES[folder].upper()}-{index:04d}"
    requester = ["华东销售组", "交付一组", "财务共享组", "客户成功组", "平台研发组"][index % 5]
    reviewer = ["部门负责人", "财务复核人", "法务经理", "采购负责人", "项目经理"][(index + 2) % 5]
    exception = ["材料缺失", "预算不足", "供应商延期", "审批超时", "条款表述不清"][(index + 3) % 5]
    system_name = ["OA 审批系统", "采购管理系统", "合同台账", "项目看板", "费用报销平台"][index % 5]

    return [
        "",
        "## 操作记录样例",
        f"样例编号为 {case_id}，申请部门为{requester}，责任部门为{owner}，事项主题为{topic}。",
        f"申请人提交的业务说明应包含事项背景、预计金额 {amount} 元、期望完成时间、关联项目和外部相对方。",
        f"{reviewer}复核时应写明同意、退回或补充材料的理由，并指出后续需要进入的系统或台账。",
        "",
        "## 材料清单样例",
        "基础材料包括申请说明、金额明细、审批依据、附件目录、责任人和预计完成日期。",
        "如果事项涉及采购，需要补充供应商选择依据、询价记录、预算编号、验收方式和合同草案。",
        "如果事项涉及会议或项目，需要补充会议纪要、行动项清单、风险状态和周报同步记录。",
        "",
        "## 异常案例",
        f"本类事项常见异常是{exception}，通常会导致审批退回、付款延迟或项目周报信息不完整。",
        "审批退回后，申请人需要在原流程中补正材料，不能另起流程规避原有审批记录。",
        "如果异常影响客户承诺或合同履约，应同步给项目经理和业务负责人，并在下一次会议纪要中记录处理结果。",
        "",
        "## 审计检查点",
        "审计人员会检查金额、审批链、附件、合同编号、预算编号和实际付款记录是否一致。",
        "对跨部门事项，还会检查会议纪要、项目周报和流程系统中的责任人是否一致。",
        "发现审批意见过于笼统、材料版本不一致或归档路径缺失时，应要求责任部门重新补充说明。",
        "",
        "## 系统字段",
        f"{system_name}中应保留事项编号、申请人、部门、金额、主题、审批状态、退回原因和归档路径。",
        "系统字段应避免只存自由文本，关键字段如金额、成本中心、供应商、合同编号和项目编号应可筛选。",
        "完成后的记录需要同步到知识库索引，方便后续问答、报告生成和流程校验工具调用。",
        "",
        "## 复盘问题",
        "复盘时先确认事项是否按照制度走完审批链，再确认结果是否被写入项目、合同或费用台账。",
        "若同类事项多次退回，应分析是材料清单不清楚、系统字段缺失，还是审批职责划分不明确。",
        "复盘结论应形成可执行改进项，例如更新模板、补充字段校验、调整提醒时间或增加法务复核节点。",
        "",
        "## 后续跟踪",
        "责任部门应在下一周期确认行动项状态，区分已关闭、进行中、阻塞和需要升级四类结果。",
        "需要升级的事项应说明影响范围、决策人、截止日期和可选方案，避免长期停留在待处理状态。",
        "如果事项已经完成，应补充最终结果、实际金额、归档编号和经验结论，便于后续相似问题复用。",
    ]


def _policy_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    approver = ["直属负责人", "部门负责人", "财务复核人", "采购负责人"][index % 4]
    return [
        "## 制度目标",
        f"{topic}制度用于统一{owner}与业务部门之间的申请口径，减少口头确认和重复补材料的情况。",
        f"当事项金额达到 {amount} 元或涉及外部供应商时，申请人需要在发起前确认预算余额、业务依据和审批路径。",
        "制度要求所有关键结论都有明确责任人，审批意见不能只写“同意”而缺少处理范围、金额和例外说明。",
        "",
        "## 申请材料",
        "差旅报销需要提供行程单、发票、审批单、费用明细和付款账户；如发生改签、超标住宿或多人同行，还需要补充情况说明。",
        "采购申请需要提供采购需求说明、预算编号、询价记录、供应商信息和验收方式；单项 8000 元以上应附部门负责人意见。",
        "合同用印或供应商付款事项，需要同时提交合同编号、履约节点、收款账户、税务信息和历史付款记录。",
        "",
        "## 审批口径",
        f"{approver}负责判断业务必要性，{owner}负责判断预算、票据和制度符合性。",
        "财务复核时优先核对金额、成本中心、发票抬头、付款账户和审批链是否一致。",
        "涉及跨部门项目时，项目经理需要确认费用是否计入项目预算，并在项目周报中同步预算影响。",
        "",
        "## 例外与退回",
        "材料缺失、金额不一致、发票信息错误、预算编号为空或合同未归档时，审批人应退回申请并说明补正项。",
        "因客户现场、紧急采购或系统故障导致先发生后审批的，申请人需要在两个工作日内补录原因和证明材料。",
        "超过制度标准但确有业务必要的事项，应由部门负责人写明例外原因，并由财务或法务进行复核。",
        "",
        "## 归档要求",
        "归档字段包括申请人、部门、金额、成本中心、审批编号、发票号码、合同编号和付款状态。",
        "归档材料应能支持后续审计、项目复盘和报告生成，不能只保存审批截图而缺少业务说明。",
        "涉及风险或例外事项的记录，应在月度费用分析或项目风险报告中继续追踪。",
        "",
        "## 常见问题",
        "如果用户询问差旅报销需要哪些材料，应回答行程单、发票、审批单、费用明细和付款账户，并说明例外材料。",
        "如果用户询问 8000 元采购申请是否需要审批，应说明需要部门负责人、采购或财务按制度复核。",
        "如果用户询问合同用印是否可以跳过法务，应说明合同类事项必须保留法务或授权复核记录。",
    ]


def _workflow_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    sla = 1 + index % 3
    return [
        "## 流程入口",
        f"{topic}流程由申请人在业务系统发起，入口字段包括事项名称、金额、预算编号、合同编号、供应商或项目名称。",
        f"当金额达到 {amount} 元、涉及合同审批或影响项目预算时，系统应要求申请人补充业务背景和预期交付结果。",
        "流程发起前，申请人应确认需求已通过部门内部讨论，避免审批链路中反复修改需求范围。",
        "",
        "## 节点与角色",
        "第一节点由直属负责人确认业务必要性，重点看申请事项是否与部门目标、客户承诺或项目计划一致。",
        f"第二节点由{owner}复核预算、制度口径和归档字段，必要时要求补充询价、合同或会议纪要。",
        "第三节点由财务、法务或采购按事项类型分流；合同审批进入法务，用印和付款进入财务，供应商选择进入采购。",
        "",
        "## 输入输出",
        "流程输入包括申请说明、金额明细、材料附件、审批依据和期望完成时间。",
        "流程输出包括审批结论、退回原因、归档编号、责任人和下一步动作；审批完成后应同步到项目或合同台账。",
        "会议纪要生成项目周报时，应从流程输出中提取风险、阻塞事项、负责人和截止日期。",
        "",
        "## 超时处理",
        f"任一节点超过 {sla} 个工作日未处理时，系统提醒当前审批人；超过两个提醒周期后升级到部门负责人。",
        "紧急采购或客户现场事项可以走加急路径，但必须在事后补齐审批依据和验收记录。",
        "流程退回后，申请人需要重新提交完整材料，不能只在评论区补充口头说明。",
        "",
        "## 风险控制",
        "同一供应商短期内多次小额申请、预算编号反复变更、审批人与申请人同属一个项目时，应触发复核。",
        "合同审批需要经过业务部门、法务部、财务部，重大合同还需管理层复核。",
        "流程结束后，审计日志应保留节点状态、审批意见、材料版本和时间戳。",
        "",
        "## 示例场景",
        "8000 元采购申请需要说明采购用途、预算来源、供应商选择依据和验收方式。",
        "供应商付款申请需要核对合同履约节点、发票信息、验收结论和历史付款记录。",
        "项目风险升级流程需要说明风险影响、当前阻塞、需要协调的部门和预计恢复时间。",
    ]


def _project_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    milestone = ["需求冻结", "接口联调", "用户验收", "灰度上线"][index % 4]
    return [
        "## 项目背景",
        f"{topic}由{owner}牵头，目标是在既定预算内完成业务流程优化、系统交付和跨部门协同。",
        f"当前预算基准约为 {amount * 10} 元，核心约束包括供应商交付、关键接口、业务验收和合同付款节点。",
        "项目资料需要同时保存需求清单、会议纪要、审批记录、合同材料和阶段报告。",
        "",
        "## 当前进展",
        f"最近一个里程碑为{milestone}，项目经理已完成进度同步，但仍需业务负责人确认验收口径。",
        "已完成事项包括需求澄清、供应商沟通、费用预算初审和项目例会纪要归档。",
        "未完成事项包括部分接口验收、风险缓解动作复核、关键用户培训和报告口径确认。",
        "",
        "## 风险清单",
        "A 项目当前风险包括需求冻结延迟、供应商交付波动、关键接口验收延期和预算消耗偏高。",
        "若供应商延期超过一周，项目经理需要在周报中标红风险，并说明替代方案和预计恢复日期。",
        "若预算消耗超过计划比例，财务需要复核采购申请、合同付款和差旅费用是否计入正确成本中心。",
        "",
        "## 会议结论",
        "项目会议纪要应记录议题、决议、行动项、责任人和截止日期，不能只记录参会人员和泛化结论。",
        "涉及合同审批、采购申请或客户承诺的议题，应附上审批编号或后续办理流程。",
        "会议结论需要转化为周报中的风险、进展和待办事项，避免信息散落在聊天记录中。",
        "",
        "## 后续计划",
        "下一阶段重点是关闭高风险问题、确认验收标准、完成供应商交付复核和准备阶段报告。",
        "项目经理每周更新风险矩阵，红色风险必须给出负责人、动作、截止时间和恢复判断。",
        "项目复盘时应对照原始公开材料、内部审批记录和实际执行结果，形成可追溯的知识条目。",
    ]


def _meeting_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    host = ["项目经理", "采购负责人", "法务经理", "财务负责人"][index % 4]
    return [
        "## 会议基本信息",
        f"{topic}由{host}主持，{owner}、业务负责人、财务或法务根据议题参加。",
        "会议目标是同步事项进展、确认风险状态、形成行动项，并为后续周报或审批材料提供依据。",
        f"本次会议涉及金额口径约 {amount} 元，若后续进入采购或合同流程，需要补充审批编号。",
        "",
        "## 议题一：进展同步",
        "各负责人按事项汇报已完成工作、未完成工作、阻塞原因和预计完成日期。",
        "项目类事项需要说明里程碑变化；采购类事项需要说明供应商选择、预算状态和验收方式。",
        "合同类事项需要说明法务意见、付款条件、违约责任和用印归档状态。",
        "",
        "## 议题二：风险与问题",
        "会议识别的风险包括审批超时、材料缺失、供应商延期、预算不足和合同条款不完整。",
        "风险记录需要明确影响范围、责任人、缓解动作和下次检查时间。",
        "无法在会议中解决的问题，应转入流程系统或项目风险台账，不能只停留在口头承诺。",
        "",
        "## 决议与行动项",
        "会议决定将关键行动项拆分到责任人，并要求在下次例会前同步完成状态。",
        "涉及差旅报销的事项需要补齐行程单、发票、审批单和费用明细。",
        "涉及合同审批的事项需要业务部门、法务部、财务部逐项确认，重大合同提交管理层复核。",
        "",
        "## 周报生成要求",
        "根据会议纪要生成项目周报时，应包含目标进展、风险状态、待办责任人、阻塞事项和下周计划。",
        "周报中的每一项风险都应能回溯到会议纪要、审批记录或项目台账。",
        "如果会议结论影响预算或合同，应在周报中单独列出金额、审批节点和预计完成时间。",
    ]


def _contract_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    counterparty = ["软件供应商", "咨询服务商", "外包交付方", "数据处理服务商"][index % 4]
    return [
        "## 合同背景",
        f"{topic}涉及{counterparty}，由业务部门提出需求，{owner}负责跟踪审批、用印或归档。",
        f"合同金额参考区间为 {amount * 3} 元，付款条件应与验收节点、发票要求和预算编号保持一致。",
        "合同材料需要包括需求说明、报价或采购依据、合同文本、审批意见和用印记录。",
        "",
        "## 审批链路",
        "合同审批需要经过业务部门、法务部、财务部，涉及采购事项时还需要采购部确认供应商选择依据。",
        "业务部门负责确认服务范围和交付标准，法务负责审查权利义务、违约责任和数据安全条款。",
        "财务负责核对付款条件、发票税率、预算编号和历史付款记录，重大合同需管理层复核。",
        "",
        "## 关键条款",
        "合同文本应明确服务范围、交付物、验收标准、付款节点、保密义务、数据处理要求和争议解决方式。",
        "如果合同涉及客户数据、个人信息或接口开放，应增加安全评估和数据处理协议。",
        "付款条款不得早于验收结论，预付款比例超过制度标准时需要额外说明业务必要性。",
        "",
        "## 风险提示",
        "常见风险包括服务范围表述模糊、验收标准不可量化、违约责任缺失、自动续约条款不明确。",
        "供应商交付延期时，业务部门需要在项目周报中说明影响，并由法务评估是否触发违约处理。",
        "合同审批退回时，应明确退回条款、修改责任人和重新提交时间。",
        "",
        "## 用印与归档",
        "用印前应核对最终文本、审批编号、签署主体、合同金额和附件完整性。",
        "归档字段包括相对方、合同金额、履约周期、审批链路、用印状态、付款计划和验收记录。",
        "合同生效后，业务负责人需要按履约节点更新交付状态，财务据此安排付款复核。",
    ]


def _report_sections(index: int, topic: str, owner: str, amount: int) -> list[str]:
    period = ["周度", "月度", "季度", "专项"][index % 4]
    return [
        "## 报告摘要",
        f"{topic}为{period}报告，由{owner}整理，覆盖进展、风险、预算、审批和后续计划。",
        f"本期关注金额约 {amount * 5} 元，重点核对采购、合同、差旅和项目成本是否与台账一致。",
        "报告结论应区分事实、判断和建议，关键指标需要说明来源系统和统计口径。",
        "",
        "## 指标概览",
        "进度指标包括已完成里程碑、延期事项、待办数量和跨部门阻塞事项。",
        "预算指标包括已申请金额、已审批金额、已付款金额、预算剩余和异常费用。",
        "质量指标包括验收通过率、退回次数、材料缺失次数和审批超时次数。",
        "",
        "## 主要发现",
        "项目周报需要汇总里程碑、风险、预算、会议结论和跨部门协同事项。",
        "采购合规报告需要说明供应商选择依据、询价记录、预算编号和合同审批状态。",
        "差旅费用分析需要区分正常报销、超标事项、逾期提交和缺失材料。",
        "",
        "## 原因分析",
        "审批超时通常来自材料不完整、责任人不明确或流程节点与事项类型不匹配。",
        "项目风险扩大通常来自需求冻结延迟、供应商交付波动或会议行动项没有进入台账。",
        "合同风险通常来自付款节点、验收标准和违约责任没有在审批阶段充分确认。",
        "",
        "## 建议与跟踪",
        "对红色风险设置责任人和截止时间，并在下一期报告中说明恢复情况。",
        "对重复退回的流程补充材料清单，减少申请人在审批链路中反复补录。",
        "对合同、采购和项目事项建立统一归档编号，方便后续问答、报告生成和审计追踪。",
    ]


def build_corpus(
    output_dir: str = "enterprise_agent/data/docs",
    min_docs: int = 300,
    raw_dir: str = "enterprise_agent/data/raw",
) -> dict:
    """Generate deterministic expanded Markdown documents from public raw seeds."""

    docs_root = Path(output_dir)
    docs_root.mkdir(parents=True, exist_ok=True)

    seeds = _load_seed_documents(Path(raw_dir))
    snippets = _load_snippets(GENERATOR_DIR)
    counts = _target_counts(max(min_docs, sum(BASE_COUNTS.values())))
    generated_from_seed = 0
    source_rows = []

    for folder, count in counts.items():
        type_dir = docs_root / folder
        type_dir.mkdir(parents=True, exist_ok=True)
        prefix = TYPE_ALIASES[folder]

        for index in range(1, count + 1):
            seed = _seed_for(folder, index, seeds)
            if seed:
                generated_from_seed += 1
            content = _body(folder, index, seed, snippets)
            path = type_dir / f"{prefix}_{index:03d}.md"
            path.write_text(content, encoding="utf-8")
            source_rows.append(_source_metadata(path.name, folder, seed))

    total_docs = sum(counts.values())
    fallback_docs = total_docs - generated_from_seed
    stats = {
        "total_docs": total_docs,
        "raw_seed_docs": len(seeds),
        "by_type": {TYPE_ALIASES[key]: value for key, value in counts.items()},
        "source_mix": {
            "public_seed": generated_from_seed / total_docs if total_docs else 0,
            "template_fallback": fallback_docs / total_docs if total_docs else 0,
        },
        "source_counts": {
            "public_seed_docs": generated_from_seed,
            "template_fallback_docs": fallback_docs,
            "expanded": total_docs,
        },
    }
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SOURCE_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SOURCE_MANIFEST_PATH.open("w", encoding="utf-8") as file:
        for row in source_rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic M1 enterprise corpus.")
    parser.add_argument("--output-dir", default="enterprise_agent/data/docs")
    parser.add_argument("--min-docs", type=int, default=300)
    parser.add_argument("--raw-dir", default="enterprise_agent/data/raw")
    args = parser.parse_args()

    stats = build_corpus(output_dir=args.output_dir, min_docs=args.min_docs, raw_dir=args.raw_dir)
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
