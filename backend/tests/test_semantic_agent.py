from agent.semantic import SemanticAgentAnalyzer


def test_semantic_analyzer_exists():
    analyzer = SemanticAgentAnalyzer()

    assert analyzer is not None


def test_invalid_json_is_rejected():
    result = SemanticAgentAnalyzer._parse_json(
        "this is not json"
    )

    assert result is None


def test_markdown_json_is_parsed():
    result = SemanticAgentAnalyzer._parse_json(
        """```json
        {
            "tool": "database.read",
            "resource": "sales_summary",
            "arguments": {
                "action": "read"
            }
        }
        ```"""
    )

    assert result is not None
    assert result["tool"] == "database.read"