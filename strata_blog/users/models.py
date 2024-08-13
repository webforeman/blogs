
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, EmailField, Model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator

from .managers import UserManager

from django.db import models

class User(AbstractUser):
    """
    Default custom user model for strata_blog.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def __str__(self):
        return self.email

class Post(Model):
    title = models.CharField(max_length=200, validators=[MinLengthValidator(10)])
    short_description = models.TextField()
    content = models.TextField()
    image_path = models.ImageField(upload_to='blog/%Y/%m/%d/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['created_at']),
            models.Index(fields=['author']),
        ]

    def __str__(self):
        return f"Post by {self.author} on {self.title[:30]}"

class Comment(Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    author_name = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['author_name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.author_name}"
