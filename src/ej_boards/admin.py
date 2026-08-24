from django.contrib import admin

from . import models


@admin.register(models.Board)
class BoardAdmin(admin.ModelAdmin):
    fields = ["title", "description", "slug", "conversations"]
    list_display = ["title", "owner", "description", "slug"]
    list_filter = ["created"]

    def save_model(self, request, obj, form, change):
        obj.owner = request.user
        return super().save_model(request, obj, form, change)


@admin.register(models.BoardManager)
class BoardManagerAdmin(admin.ModelAdmin):
    list_display = ["board", "user", "invitation", "created"]
    list_filter = ["created"]
    search_fields = ["board__title", "user__email"]


@admin.register(models.BoardManagerInvitation)
class BoardManagerInvitationAdmin(admin.ModelAdmin):
    list_display = ["board", "email", "user", "status", "is_active"]
    list_filter = ["status", "is_active", "created"]
    search_fields = ["board__title", "email", "user__email"]
