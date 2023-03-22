from django.contrib.auth import get_user_model
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import (
    CurrentUserDefault, ModelSerializer, ValidationError
)
from rest_framework.validators import UniqueTogetherValidator

from posts.models import Comment, Follow, Group, Post

User = get_user_model()


class PostSerializer(ModelSerializer):
    author = SlugRelatedField(read_only=True, slug_field='username')

    class Meta:
        fields = '__all__'
        model = Post


class GroupSerializer(ModelSerializer):

    class Meta:
        model = Group
        fields = '__all__'


class CommentSerializer(ModelSerializer):
    author = SlugRelatedField(read_only=True, slug_field='username')

    class Meta:
        fields = '__all__'
        read_only_fields = ('post',)
        model = Comment


class FollowSerializer(ModelSerializer):
    user = SlugRelatedField(
        default=CurrentUserDefault(),
        read_only=True,
        slug_field='username'
    )
    following = SlugRelatedField(
        queryset=User.objects.all(), slug_field='username'
    )

    class Meta:
        model = Follow
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'following')
            )
        ]

    def validate_following(self, value):
        user = self.context['request'].user
        if value == user:
            raise ValidationError(
                'Нельзя подписываться на самого себя!')
        return super().validate(value)
