from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from strata_blog.users.api.views import UserViewSet, PostViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# router.register('users', UserViewSet)
router.register('posts', PostViewSet, basename='posts')


app_name = 'api'
urlpatterns = router.urls
