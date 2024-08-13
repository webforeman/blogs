from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination

from strata_blog.users.models import Post, User
from .serializers import UserSerializer, PostSerializer
from django.db import connection, ProgrammingError

class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

class PostPagination(PageNumberPagination):
    page_size = 10  # Количество постов на странице
    page_size_query_param = 'page_size'
    max_page_size = 100

class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    pagination_class = PostPagination

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'add_comment']:
            return [IsAuthenticated()]
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return []

    def get_queryset(self):
        sort_by = self.request.query_params.get('sort_by', 'created_at')
        author_id = self.request.query_params.get('author_id')

        allowed_sort_fields = ['created_at', 'title']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'

        query = """
        SELECT
            p.id,
            p.title,
            p.short_description,
            p.created_at,
            u.id as author_id,
            u.name, u.email,
            p.image_path,
            COALESCE(MAX(c.created_at), NULL) as last_comment_date,
            COALESCE(
                (SELECT c2.author_name
                FROM users_comment c2
                WHERE c2.post_id = p.id
                ORDER BY c2.created_at DESC
                LIMIT 1), '') as last_comment_author
        FROM users_post p
        JOIN users_user u ON p.author_id = u.id
        LEFT JOIN users_comment c ON c.post_id = p.id
        """

        # Параметризованный SQL-запрос
        params = []
        if author_id:
            query += " WHERE u.id = %s"
            params.append(author_id)

        query += f" GROUP BY p.id, p.title, p.short_description, u.id, u.name, u.email, p.image_path ORDER BY p.{sort_by} DESC;"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        return [
            {
                'id': row[0],
                'title': row[1],
                'short_description': row[2],
                'created_at': row[3],
                'author': {
                    'id': row[4],
                    'name': row[5],
                    'email': row[6],
                },
                'image_path': row[7],
                'last_comment_date': row[8],
                'last_comment_author': row[9]
            } for row in results
        ]


    def list(self, request, *args, **kwargs):
        page_number = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', self.pagination_class.page_size))
        sort_by = request.GET.get('sort_by', 'created_at')  # Получаем параметр сортировки
        author_id = request.GET.get('author_id', None)

        # Определите смещение для SQL-запроса
        offset = (page_number - 1) * page_size

        # Получите общее количество постов для пагинации
        count_query = "SELECT COUNT(*) FROM users_post"

        if author_id:
            count_query += f" WHERE author_id = {author_id}"

        with connection.cursor() as cursor:
            cursor.execute(count_query)
            total_count = cursor.fetchone()[0]

        # Проверка допустимости поля сортировки
        allowed_sort_fields = ['created_at', 'title', 'author_id']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'

        # Основной SQL-запрос с пагинацией
        query = f"""
        SELECT
            p.id,
            p.title,
            p.short_description,
            p.created_at,
            u.id as author_id,
            u.name, u.email,
            p.image_path,
            COALESCE(MAX(c.created_at), NULL) as last_comment_date,
            COALESCE(
                (SELECT c2.author_name
                FROM users_comment c2
                WHERE c2.post_id = p.id
                ORDER BY c2.created_at DESC
                LIMIT 1), '') as last_comment_author
        FROM users_post p
        JOIN users_user u ON p.author_id = u.id
        LEFT JOIN users_comment c ON c.post_id = p.id
        """
        if author_id:
            query += f" WHERE p.author_id = {author_id}"
        query += f" GROUP BY p.id, p.title, p.short_description, u.id, u.name, u.email, p.image_path"
        query += f" ORDER BY p.{sort_by} DESC"
        query += f" LIMIT %s OFFSET %s;"

        with connection.cursor() as cursor:
            cursor.execute(query, [page_size, offset])
            results = cursor.fetchall()

        # Формирование ответа
        posts = [
            {
                'id': row[0],
                'title': row[1],
                'short_description': row[2],
                'created_at': row[3],
                'author': {
                    'id': row[4],
                    'name': row[5],
                    'email': row[6],
                },
                'image_path': row[7],
                'last_comment_date': row[8],
                'last_comment_author': row[9]
            } for row in results
        ]

        # Формирование ответа с пагинацией
        response_data = {
            'total_count': total_count,
            'page_size': page_size,
            'current_page': page_number,
            'total_pages': (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            'posts': posts
        }

        return Response(response_data)


    def retrieve(self, request, pk):
        query = """
        SELECT
            p.id,
            p.title,
            p.content,
            u.id as author_id,
            u.name, u.email,
            p.image_path,
            c.id as comment_id,
            c.author_name,
            c.content as comment_content,
            c.created_at as comment_created_at
        FROM users_post p
        JOIN users_user u ON p.author_id = u.id
        LEFT JOIN users_comment c ON c.post_id = p.id
        WHERE p.id = %s
        ORDER BY c.created_at DESC;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [pk])
            results = cursor.fetchall()

        if not results:
            return Response({"detail": "Not found."}, status=404)

        post_data = {
            'id': results[0][0],
            'title': results[0][1],
            'content': results[0][2],
            'author': {
                'id': results[0][3],
                'name': results[0][4],
                'email': results[0][5],
            },
            'image_path': results[0][6],
            'comments': []
        }

        for row in results:
            if row[7] is not None:
                post_data['comments'].append({
                    'id': row[7],
                    'author_name': row[8],
                    'content': row[9],
                    'created_at': row[10],
                })

        return Response(post_data)

    def update(self, request, pk=None, partial=False):
        with connection.cursor() as cursor:
            cursor.execute("SELECT author_id FROM users_post WHERE id = %s", [pk])
            author_id = cursor.fetchone()
            if author_id is None or author_id[0] != request.user.id:
                return Response({"detail": "Not permission to update this post."}, status=status.HTTP_403_FORBIDDEN)

            fields_to_update = []
            values = []

            if 'title' in request.data:
                fields_to_update.append("title = %s")
                values.append(request.data['title'])
            if 'short_description' in request.data:
                fields_to_update.append("short_description = %s")
                values.append(request.data['short_description'])
            if 'content' in request.data:
                fields_to_update.append("content = %s")
                values.append(request.data['content'])
            if 'image_path' in request.data:
                fields_to_update.append("image_path = %s")
                values.append(request.data['image_path'])

            if not fields_to_update:
                return Response({"detail": "No fields to update."}, status=status.HTTP_400_BAD_REQUEST)

            query = f"UPDATE users_post SET {', '.join(fields_to_update)} WHERE id = %s"
            values.append(pk)
            cursor.execute(query, values)

            return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk=None):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT author_id FROM users_post WHERE id = %s", [pk])
                author_id = cursor.fetchone()
                if author_id is None or author_id[0] != request.user.id:
                    return Response({"detail": "Not permission to delete this post."}, status=status.HTTP_403_FORBIDDEN)

                cursor.execute("DELETE FROM users_post WHERE id = %s", [pk])
                return Response(status=status.HTTP_204_NO_CONTENT)
        except ProgrammingError as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        post_id = pk
        author_name = request.data.get('author_name')
        content = request.data.get('content')

        if not author_name or not content:
            return Response({"detail": "Author name and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users_comment (post_id, author_name, content)
                VALUES (%s, %s, %s)
            """, [post_id, author_name, content])

        return Response(status=status.HTTP_201_CREATED)
