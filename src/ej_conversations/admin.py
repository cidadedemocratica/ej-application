from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from . import models
from .enums import Choice

SHOW_VOTES = getattr(settings, "EJ_CONVERSATIONS_SHOW_VOTES", False)


def descr(msg):
    def decorator(f):
        setattr(f, "short_description", msg)
        return f

    return decorator


admin.site.register(models.RasaConversation)


class VoteInline(admin.TabularInline):
    model = models.Vote
    raw_id_fields = ["author"]


class AuthorIsUserMixin(admin.ModelAdmin):
    author_field = "author"

    def save_model(self, request, obj, *args, **kwargs):
        if getattr(obj, self.author_field) is None:
            setattr(obj, self.author_field, request.user)
        return super().save_model(request, obj, *args, **kwargs)


@admin.register(models.Comment)
class CommentAdmin(AuthorIsUserMixin, admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["conversation", "content"]}),
        (
            _("Moderation"),
            {
                "fields": [
                    "status",
                    "rejection_reason",
                    "moderator",
                    "rejection_reason_text",
                ]
            },
        ),
    ]
    list_display = ["content", "conversation", "created", "status"]
    list_filter = ["conversation", "status", "created"]

    if SHOW_VOTES:
        inlines = [VoteInline]


@admin.register(models.Conversation)
class ConversationAdmin(AuthorIsUserMixin, admin.ModelAdmin):
    fields = ["title", "text", "is_promoted", "is_hidden", "tags"]
    list_display = ["title", "author", "created", "is_promoted", "n_comments"]
    list_filter = ["created", "is_promoted", "is_hidden"]
    list_editable = ["is_promoted"]

    #
    # Admin actions
    #
    actions = ["delete_votes", "delete_comments"]

    # Generic actions
    @descr(_("Delete all votes for selected conversations"))
    def delete_votes(self, request, queryset):
        self._delete_qs(request, queryset.votes(), "votes")

    @descr(_("Delete all comments for selected conversations"))
    def delete_comments(self, request, queryset):
        self._delete_qs(request, queryset.comments(), "comments")

    def _delete_qs(self, request, qs, which):
        n = qs.count()
        qs.delete()
        self.message_user(request, _("{n} {which} removed!").format(n=n, which=which))

    #
    #  Debug actions
    #
    @descr(_("Cast 50 random votes per selected conversation (slow)"))
    def random_votes_50(self, request, queryset):
        self._random_votes(request, queryset, 50)

    @descr(_("Cast 500 random votes per selected conversation (slow)"))
    def random_votes_500(self, request, queryset):
        self._random_votes(request, queryset, 500)

    @descr(_("Cast 5000 random votes per selected conversation (slow)"))
    def random_votes_5000(self, request, queryset):
        self._random_votes(request, queryset, 5000)

    @descr(_("Create 10 random comments in each selected conversation (slow)"))
    def random_comments_10(self, request, queryset):
        self._random_comments(request, queryset, 10)

    @descr(_("Create 100 random comments in each selected conversation (slow)"))
    def random_comments_100(self, request, queryset):
        self._random_comments(request, queryset, 100)

    @descr(_("Create 1000 random comments in each selected conversation (slow)"))
    def random_comments_1000(self, request, queryset):
        self._random_comments(request, queryset, 1000)

    def _random_comments(self, request, queryset, size):
        from random import choice

        from faker import Factory

        fake = Factory.create()
        users = list(get_user_model().objects.all())
        status = models.Comment.STATUS.approved

        total = 0
        for conversation in queryset:
            for idx in range(size):
                try:
                    content = fake.paragraph()
                    user = choice(users)
                    conversation.create_comment(user, content, status=status)
                except PermissionError:
                    pass
                else:
                    total += 1

        self.message_user(request, _("Created {n} comments").format(n=total))

    def _random_votes(self, request, queryset, size):
        from random import choice

        users = list(get_user_model().objects.all())
        choices = [Choice.DISAGREE, Choice.SKIP, Choice.DISAGREE]

        total = 0
        for conversation in queryset:
            comments = list(conversation.comments.approved())

            for idx in range(size):
                comment = choice(comments)
                user = choice(users)
                try:
                    comment.vote(user, choice(choices))
                except ValidationError:
                    pass
                else:
                    total += 1

        self.message_user(request, _("Created {n} votes").format(n=total))

    actions.extend(
        [
            "random_votes_50",
            "random_votes_500",
            "random_votes_5000",
            "random_comments_10",
            "random_comments_100",
            "random_comments_1000",
        ]
    )
