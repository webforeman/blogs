import os
import django
from faker import Faker
from django.core.management.base import BaseCommand
from strata_blog.users.models import User, Post, Comment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

class Command(BaseCommand):
    help = 'Seed the database with fake data'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Создание пользователей
        users = []
        for _ in range(42):  # Создаем пользователей
            user = User.objects.create(
                email=fake.email(),
                name=fake.name(),
            )
            user.set_password('password')  # Устанавливаем пароль
            user.save()
            users.append(user)
            self.stdout.write(self.style.SUCCESS(f'Created user {user.email}'))

        # Создание постов
        for user in users:
            for _ in range(5):  # Каждый пользователь создает 3 поста
                post = Post.objects.create(
                    title=fake.sentence(),
                    short_description=fake.text(max_nb_chars=100),
                    content=fake.text(),
                    image_path=fake.image_url(),
                    author=user
                )
                self.stdout.write(self.style.SUCCESS(f'Created post {post.title} by {user.email}'))

                # Создание комментариев к посту
                for _ in range(4):  # Каждый пост получает 2 комментария
                    comment = Comment.objects.create(
                        author_name=fake.name(),
                        content=fake.text(max_nb_chars=200),
                        post=post
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created comment by {comment.author_name} on post {post.title}'))
