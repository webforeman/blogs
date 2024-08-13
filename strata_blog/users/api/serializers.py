from rest_framework import serializers

from strata_blog.users.models import Post, User, Comment


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {
                "view_name": "api:user-detail",
                "lookup_field": "pk"
            },
        }

    def get_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url())


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'author_name', 'content', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    last_comment_date = serializers.SerializerMethodField()
    last_comment_author = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'author', 'created_at','image_path', 'last_comment_date', 'last_comment_author', 'comments']

    def get_last_comment_date(self, obj):
        last_comment = obj.comments.order_by('-created_at').first()
        return last_comment.created_at if last_comment else None

    def get_last_comment_author(self, obj):
        last_comment = obj.comments.order_by('-created_at').first()
        return last_comment.author_name if last_comment else None

class PostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author', 'image_path', 'comments']
