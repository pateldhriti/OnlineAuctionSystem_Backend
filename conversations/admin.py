from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['sender', 'body', 'created_at']
    readonly_fields = ['sender', 'body', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['listing', 'bidder', 'created_at']
    search_fields = ['listing__title', 'bidder__username']
    readonly_fields = ['created_at']
    inlines = [MessageInline]
