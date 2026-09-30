"""
Agent workflow package for APG.

Case 7 introduces the controlled agent layer.

The agent:
    1. receives a task
    2. proposes an action
    3. sends the action to the Governor
    4. follows the Governor decision

The agent never bypasses the Governor.
"""