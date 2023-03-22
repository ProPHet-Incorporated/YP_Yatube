from django.contrib import admin

from .models import Comment, Group, Post


class PostAdmin(admin.ModelAdmin):
    """Управление постами."""

    list_display = ('pk', 'text', 'created', 'author', 'group',)
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ['created']
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    """Управление группами."""

    list_display = ('pk', 'slug', 'description', 'title',)
    search_fields = ('title',)
    empty_value_display = '-пусто-'


class CommentAdmin(admin.ModelAdmin):
    """Управление комментариями."""

    list_display = ('post', 'text', 'author')
    search_fields = ('post', 'text')
    empty_value_display = '-пусто-'


admin.site.register(Post, PostAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Comment, CommentAdmin)
