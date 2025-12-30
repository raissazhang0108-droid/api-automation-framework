"""
智能测试修复Agent
使用AI分析测试失败并生成修复方案
"""
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from utils.logger import log


class TestFixerAgent:
    """测试修复Agent"""

    def __init__(self, ai_agent):
        """
        初始化

        Args:
            ai_agent: AI代理（Ollama/OpenAI/DeepSeek）
        """
        self.ai_agent = ai_agent

    def analyze_failure(
            self,
            test_case: Dict[str, Any],
            failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析测试失败原因

        Args:
            test_case: 测试用例数据
            failure_info: 失败信息 {expected_status, actual_status, error_message, response_data}

        Returns:
            分析结果和修复建议
        """
        log.info(f"分析失败用例: {test_case.get('id')}")

        # 构建分析提示词
        prompt = self._build_analysis_prompt(test_case, failure_info)

        # 调用AI分析
        try:
            analysis = self._call_ai_for_analysis(prompt)
        except Exception as e:
            log.warning(f"AI分析失败，使用规则引擎: {e}")
            analysis = self._rule_based_analysis(test_case, failure_info)

        return analysis

    def _build_analysis_prompt(
            self,
            test_case: Dict[str, Any],
            failure_info: Dict[str, Any]
    ) -> str:
        """构建分析提示词"""

        prompt = f"""你是一个专业的API测试专家。请分析以下测试失败的原因并提供修复建议。

## 测试用例信息
- ID: {test_case.get('id')}
- 标题: {test_case.get('title')}
- 类型: {', '.join(test_case.get('tags', []))}
- API: {test_case.get('api', {}).get('method')} {test_case.get('api', {}).get('endpoint')}

## 请求数据
```json
{json.dumps(test_case.get('data', {}), indent=2, ensure_ascii=False)}
```

## 期望结果
- 状态码: {test_case.get('expected', {}).get('status_code')}

## 实际结果
- 状态码: {failure_info.get('actual_status')}
- 响应:
```json
{json.dumps(failure_info.get('response_data', {}), indent=2, ensure_ascii=False)}
```

---

请分析并返回JSON格式的修复建议：

{{
  "failure_type": "status_mismatch",
  "root_cause": "API接受了无效数据，可能验证规则不严格",
  "fix_strategies": [
    {{
      "strategy": "convert_test_type",
      "description": "将此用例转换为正向测试",
      "confidence": 0.9,
      "changes": {{
        "status_code": 200,
        "tags": ["positive"],
        "reason": "API实际接受了该数据"
      }}
    }},
    {{
      "strategy": "update_expectation",
      "description": "仅更新期望状态码",
      "confidence": 0.7,
      "changes": {{
        "status_code": 200,
        "reason": "API行为与预期不符"
      }}
    }}
  ],
  "recommended_strategy": 0,
  "explanation": "API没有按预期返回错误，说明验证不严格或测试数据实际有效"
}}

重要：只返回JSON，不要有其他文字。"""

        return prompt

    def _call_ai_for_analysis(self, prompt: str) -> Dict[str, Any]:
        """调用AI进行分析"""
        # 调用AI
        response = self.ai_agent.generate_raw(prompt)

        # 提取JSON
        json_str = self.ai_agent.extract_json(response)

        # 解析
        analysis = json.loads(json_str)

        log.info(f"AI分析完成: {analysis.get('failure_type')}")

        return analysis

    def _rule_based_analysis(
            self,
            test_case: Dict[str, Any],
            failure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于规则的分析（AI失败时的后备方案）"""

        expected = failure_info.get('expected_status')
        actual = failure_info.get('actual_status')

        strategies = []

        # 规则1: 期望4xx/5xx，实际2xx -> 转为正向用例
        if expected >= 400 and actual == 200:
            strategies.append({
                "strategy": "convert_test_type",
                "description": "API接受了该数据，应转换为正向测试用例",
                "confidence": 0.95,
                "changes": {
                    "status_code": 200,
                    "tags": ["positive"],
                    "reason": "API验证规则可能与预期不同"
                }
            })

            root_cause = "API接受了预期应该被拒绝的数据"

        # 规则2: 期望2xx，实际4xx -> 修复测试数据
        elif expected == 200 and actual >= 400:
            strategies.append({
                "strategy": "fix_test_data",
                "description": "测试数据不符合API要求，需要修正",
                "confidence": 0.85,
                "changes": {
                    "status_code": actual,
                    "reason": "测试数据问题"
                }
            })

            root_cause = "测试数据不符合API要求"

        # 规则3: 其他情况 -> 更新期望
        else:
            strategies.append({
                "strategy": "update_expectation",
                "description": f"更新期望状态码从 {expected} 到 {actual}",
                "confidence": 0.7,
                "changes": {
                    "status_code": actual,
                    "reason": "API返回了不同的状态码"
                }
            })

            root_cause = f"API返回 {actual} 而不是期望的 {expected}"

        return {
            "failure_type": "status_mismatch",
            "root_cause": root_cause,
            "fix_strategies": strategies,
            "recommended_strategy": 0,
            "explanation": "使用规则引擎生成的建议"
        }

    def apply_fix(
            self,
            test_case: Dict[str, Any],
            fix_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用修复策略

        Args:
            test_case: 原测试用例
            fix_strategy: 修复策略

        Returns:
            修复后的测试用例
        """
        import copy
        fixed_case = copy.deepcopy(test_case)
        changes = fix_strategy.get('changes', {})

        # 更新状态码
        if 'status_code' in changes:
            if 'expected' not in fixed_case:
                fixed_case['expected'] = {}
            fixed_case['expected']['status_code'] = changes['status_code']

        # 更新tags
        if 'tags' in changes:
            fixed_case['tags'] = changes['tags']
        elif fix_strategy['strategy'] == 'convert_test_type':
            # 转换用例类型
            if 'negative' in fixed_case.get('tags', []):
                fixed_case['tags'] = [t for t in fixed_case['tags'] if t != 'negative']
            if 'positive' not in fixed_case.get('tags', []):
                fixed_case['tags'].insert(0, 'positive')

        # 更新数据
        if 'data' in changes and changes['data']:
            if 'data' not in fixed_case:
                fixed_case['data'] = {}
            fixed_case['data'].update(changes['data'])

        # 添加修复记录
        if 'metadata' not in fixed_case:
            fixed_case['metadata'] = {}

        fixed_case['metadata']['auto_fixed'] = True
        fixed_case['metadata']['fix_reason'] = changes.get('reason', '')
        fixed_case['metadata']['fix_strategy'] = fix_strategy['strategy']

        log.info(f"应用修复: {test_case.get('id')} - {fix_strategy['strategy']}")

        return fixed_case

    def generate_fix_report(
            self,
            analyses: List[Dict[str, Any]]
    ) -> str:
        """
        生成修复报告

        Args:
            analyses: 分析结果列表

        Returns:
            Markdown格式的报告
        """
        from datetime import datetime

        report = "# 测试修复分析报告\n\n"

        report += f"## 概览\n\n"
        report += f"- 失败用例数: {len(analyses)}\n"
        report += f"- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for idx, analysis in enumerate(analyses, 1):
            report += f"## 用例 {idx}\n\n"
            report += f"**失败类型**: {analysis.get('failure_type')}\n\n"
            report += f"**根本原因**: {analysis.get('root_cause')}\n\n"

            report += f"### 修复建议\n\n"

            strategies = analysis.get('fix_strategies', [])
            recommended = analysis.get('recommended_strategy', 0)

            for i, strategy in enumerate(strategies):
                prefix = "🌟 " if i == recommended else "   "
                report += f"{prefix}**策略 {i + 1}**: {strategy['strategy']}\n"
                report += f"   - 描述: {strategy['description']}\n"
                report += f"   - 置信度: {strategy['confidence']:.0%}\n\n"

            report += f"**推荐**: 使用策略 {recommended + 1}\n\n"
            report += f"**说明**: {analysis.get('explanation', '无')}\n\n"
            report += "---\n\n"

        return report