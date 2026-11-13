from django.contrib import admin
from .models import News, Tag, PostReaction


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'status', 'category', 'views_count', 'likes_count', 'dislikes_count', 'created_at')
    list_filter = ('status', 'category', 'topic', 'created_at')
    search_fields = ('name', 'description', 'content', 'author__username', 'tags__name')
    readonly_fields = ('views_count', 'likes_count', 'dislikes_count', 'created_at', 'updated_at')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'value', 'created_at')
    list_filter = ('value',)
    readonly_fields = ('post', 'user', 'value', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
