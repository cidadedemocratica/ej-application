from boogie import rules


@rules.register_perm("ej.can_access_dataviz")
def can_access_dataviz(user, conversation):
    """
    Can access dataviz views for a conversation.

    * User is staff
    * OR user is a superuser
    * OR user can edit the conversation
    """
    return (
        user.is_staff
        or user.is_superuser
        or user.has_perm("ej.can_edit_conversation", conversation)
    )


@rules.register_perm("ej.can_view_report")
def can_view_report(user, conversation):
    """
    Can see basic report data
    """
    if can_view_report_detail(user, conversation):
        return True
    else:
        return user.has_perm("ej.can_edit_conversation", conversation)


@rules.register_perm("ej.can_view_report_detail")
def can_view_report_detail(user, conversation):
    """
    Can see advanced report data

    * Must be staff
    """
    return (
        user.is_superuser
        or user.is_staff
        or conversation
        and conversation.author.id == user.id
    )
