from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    path('', HomeView.as_view()),
    path('api/v1/signup/', CustomUserCreateView.as_view(), name='signup'),
    path('api/v1/signin/', SigninView.as_view(), name='signin'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/v1/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/v1/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/v1/folders/', FolderListCreateView.as_view(), name='folders'),
    path('api/v1/upload-images/<str:folder_uuid>/', ImageUploadView.as_view(), name='image-upload'),
    path('api/v1/image-list/<str:folder_uuid>/', ImageListView.as_view(), name='image-upload'),
    path('api/v1/profile/', ProfileView.as_view(), name='profile'),
    path('api/v1/profile-image/', ProfilePictureUpdateView.as_view(), name='profile-picture-update'),
    path('api/v1/move-to-trash-image/', MoveToTrashImage.as_view(), name='move-to-trash-image'),
    path('api/v1/permanently-delete-image/', DeleteImagePermanently.as_view(), name='delete-image-permanently'),
    path('api/v1/folder-move-to-trash/<str:folder_uuid>/', MoveFolderToTrash.as_view(), name='move-folder-to-trash'),
    path('api/v1/permanently-delete-folder/<str:folder_uuid>/', DeleteFolderPermanently.as_view(),
         name='delete-folder-permanently'),
    path('api/v1/restore-folder/<str:folder_uuid>/', RestoreFolderFromTrash.as_view(), name='restore-folder'),
    path('api/v1/restore-images/', RestoreImageFromTrash.as_view(), name='restore-images'),
    path('api/v1/trash/', TrashDataView.as_view(), name='trash-view'),
    path('api/v1/trash-folder-data/<str:folder_uuid>/', TrashFolderDataView.as_view(), name='trash-folder-data'),
    path('api/v1/update-folder/<str:folder_uuid>/', FolderUpdateView.as_view(), name='folder-update'),
    path('api/v1/shared-folder/<str:folder_uuid>/', FolderShareView.as_view(), name='shared-folder-view'),
    path('api/v1/shared-image/<str:image_uuid>/', SharedImageView.as_view(), name='shared-image-view'),
    path('api/v1/face-recognition/<str:folder_uuid>/', FaceMatchesView.as_view(), name='face-match'),
    path('api/v2/folders/', FolderListView.as_view(), name='folders'),
    path('api/v1/analytics/', AnalyticsView.as_view(), name='analytics'),
    path('api/v1/download_log/', DownloadLogListCreateView.as_view(), name='download-log'),
    path('api/v1/folder-cover-photo/<str:folder_uuid>/', UploadFolderCoverImage.as_view(), name='cover-photo-upload'),
]
