from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from strata_blog.users.models import User

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .forms import PostForm, CommentForm

import requests


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None=None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()

class HomePageView(View):
    def get(self, request):
        # Получение номера страницы и размера страницы из параметров запроса
        page_number = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        sort_by = request.GET.get('sort_by', 'created_at')
        author_id = request.GET.get('author_id')

        # Запрос к API с параметрами пагинации
        response = requests.get(f'http://localhost:8000/api/posts/?page={page_number}&page_size={page_size}')

        if response.status_code == 200:
            posts_data = response.json()
            posts = posts_data.get('posts', [])  # Извлекаем список постов
            current_page = posts_data.get('current_page', 1) # Текущая страница
            total_count = posts_data.get('total_count', 0)  # Общее количество постов
            total_pages = posts_data.get('total_pages', 1)  # Общее количество страниц
        else:
            posts = []
            current_page = 1
            total_count = 0
            total_pages = 1

        return render(request, 'pages/home.html', {
            'posts': posts,
            'current_page': current_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'page_size': page_size,
        })

class BlogDetailView(View):
    def get(self, request, pk):
        # Получение данных о посте из API

        comment_form = CommentForm()
        response = requests.get(f'http://localhost:8000/api/posts/{pk}/')

        if response.status_code == 200:
            post = response.json()

        else:
            post = None  # Или можно обработать ошибку по-другому

        return render(request, 'pages/blog_detail.html', {'post': post, 'comment_form': comment_form})

    def post(self, request, pk):
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            # Сохранение комментария с указанием поста
            comment = comment_form.save(commit=False)
            comment.post_id = pk  # Указываем пост, к которому относится комментарий
            comment.save()
            return redirect('blog_detail', pk=pk)  # Перенаправление на страницу поста
        return render(request, 'pages/blog_detail.html', {'comment_form': comment_form})


class CreatePostView(View):
    def get(self, request):
        post_form = PostForm()
        return render(request, 'pages/create_post.html', {'post_form': post_form})

    def post(self, request):
        post_form = PostForm(request.POST, request.FILES)
        if post_form.is_valid():
            new_post = post_form.save(commit=False)
            new_post.author = request.user  # Убедитесь, что пользователь аутентифицирован
            new_post.save()
            return redirect('home')  # Перенаправление на главную страницу или другую страницу
        return render(request, 'pages/create_post.html', {'post_form': post_form})
