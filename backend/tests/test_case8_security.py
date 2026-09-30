import pytest

from agent.semantic import SemanticAgentAnalyzer
def test_json_array_is_rejected():

    result = SemanticAgentAnalyzer._parse_json(
        """
        [
            {
                "tool": "database.read"
            }
        ]
        """
    )

    assert result is None