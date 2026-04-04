CATEGORY = {
    "links": {"self": "http://testserver/categories/category/"},
    "name": "Category",
    "slug": "category",
    "image": None,
    "image_caption": "",
}

USER_ROOT = {"url": "http://testserver/users/root/", "username": "root"}

USER = {"url": "http://testserver/users/user/", "username": "user"}

COMMENT = {
    "content": "content",
    "status": "approved",
    "rejection_reason": 0,
    "rejection_reason_text": "",
}

CONVERSATION = {
    "author": "email@server.com",
    "title": "title",
    "id": 1,
    "slug": "title",
    "statistics": {
        "comments": {"approved": 0, "rejected": 0, "pending": 0, "total": 0},
        "votes": {"agree": 0, "disagree": 0, "skip": 0, "total": 0},
        "participants": {"commenters": 0, "voters": 0},
        "channel_votes": {
            "opinion_component": 0,
            "telegram": 0,
            "unknown": 0,
            "webchat": 0,
            "whatsapp": 0,
            "ej": 0,
        },
        "channel_participants": {
            "opinion_component": 0,
            "telegram": 0,
            "unknown": 0,
            "ej": 0,
            "webchat": 0,
            "whatsapp": 0,
        },
    },
    "text": "test",
    "board": "Explore",
    "participants_can_add_comments": True,
    "send_profile_question": False,
    "votes_to_send_profile_question": 0,
}

VOTE = {
    "comment": "content",
    "choice": 1,
    "channel": "ej",
}

VOTES = [
    {
        "email": "email@server.com",
        "author": "",
        "author_id": 1,
        "comment": "content",
        "comment_id": 1,
        "choice": "agree",
        "created": 1622928765251,
    }
]
