from .policy_loader import load_roles, load_tasks


class AuthorizationEngine:

    def __init__(self):

        self.roles = load_roles().get(
            "roles",
            {}
        )

        self.tasks = load_tasks().get(
            "tasks",
            {}
        )

    def authorize(
        self,
        role: str,
        task_id: str,
        tool: str,
        resource: str,
        action: str,
    ) -> tuple[bool, str]:

        # -------------------------------
        # ROLE
        # -------------------------------

        role_policy = self.roles.get(role)

        if not role_policy:
            return False, f"Unknown role: {role}"

        # -------------------------------
        # TOOL
        # -------------------------------

        tool_policy = (
            role_policy
            .get("tools", {})
            .get(tool)
        )

        if not tool_policy:
            return (
                False,
                f"Tool '{tool}' is not permitted "
                f"for role '{role}'",
            )

        # -------------------------------
        # ACTION
        # -------------------------------

        if action not in tool_policy.get(
            "actions",
            [],
        ):
            return (
                False,
                f"Action '{action}' is not permitted",
            )

        # -------------------------------
        # RESOURCE
        # -------------------------------

        if resource not in tool_policy.get(
            "resources",
            [],
        ):
            return (
                False,
                f"Resource '{resource}' "
                f"is outside role scope",
            )

        # -------------------------------
        # TASK
        # -------------------------------

        task = self.tasks.get(task_id)

        if not task:
            return False, f"Unknown task: {task_id}"

        # -------------------------------
        # TASK TOOL SCOPE
        # -------------------------------

        if tool not in task.get(
            "allowed_tools",
            [],
        ):
            return (
                False,
                f"Tool '{tool}' is outside "
                f"task scope",
            )

        # -------------------------------
        # TASK RESOURCE SCOPE
        # -------------------------------

        if resource not in task.get(
            "allowed_resources",
            [],
        ):
            return (
                False,
                f"Resource '{resource}' "
                f"is outside task scope",
            )

        # -------------------------------
        # FORBIDDEN ACTION
        # -------------------------------

        if action in task.get(
            "forbidden_actions",
            [],
        ):
            return (
                False,
                f"Action '{action}' is forbidden "
                f"by task policy",
            )

        return True, "Authorization successful"