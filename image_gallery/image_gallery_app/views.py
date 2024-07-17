from datetime import date
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from .serializer import *
from .models import *
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .upload_file_s3 import upload_to_s3
import os
from .compressed_image import compressed_image
from django.core.files.base import ContentFile
from io import BytesIO
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from .delete_object_s3 import delete_objects
from django.db.models import Q
from .face_match import match_faces
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from datetime import timedelta
from rest_framework.parsers import MultiPartParser, FormParser


# Create your views here.

class SigninView(TokenObtainPairView):
    # Replace the serializer with your custom
    serializer_class = MyTokenObtainPairSerializer


class LogoutView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer

    def create(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')

            # Check if the old password matches the current password
            if not check_password(old_password, request.user.password):
                return Response({"message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

            # Change the password and save the user object
            request.user.set_password(new_password)
            request.user.save()

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomUserCreateView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAdminUser,)


class FolderListCreateView(generics.ListCreateAPIView):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter folders to only show those created by the current user
        return Folder.objects.filter(created_by=self.request.user, added_to_trash=False)

    def perform_create(self, serializer):
        # Set the created_by field to the current user
        serializer.save(created_by=self.request.user)


class ImageUploadView(generics.CreateAPIView):
    queryset = Image.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ImageSerializer

    def get_folder(self, folder_uuid, created_by):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=created_by)
        except Folder.DoesNotExist:
            return None

    def process_image(self, image, folder, user):
        image_name = image.name
        size = image.size
        image_uuid = str(uuid.uuid4())

        # Read the file content into memory
        image_content = image.read()
        image.seek(0)  # Reset the pointer to the beginning of the file

        # Define S3 key for each image (you can customize the key as per your requirement)
        key = f"{folder.folder_uuid}/{image_uuid}.{image_name.split('.')[-1]}"

        # Upload image to S3
        success, url = upload_to_s3(BytesIO(image_content), key)
        if not success:
            return None, 'Upload error'
        # Create a copy of the image file-like object for compression
        image_copy = BytesIO(image_content)
        compact_image = compressed_image(image_copy, image_name, 461, 288)
        serializer = ImageSerializer(
            data={'image_name': image_name, 'image_size': size / 1048576, 's3_link': url,
                  'compact_image': compact_image,
                  'folder': folder.id, 'created_by': user.id, 'image_uuid': image_uuid})
        if serializer.is_valid():
            serializer.save()
            return serializer.data, None
        else:
            return None, serializer.errors

    def create(self, request, *args, **kwargs):
        folder_uuid = kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid, created_by=request.user)
        if not folder:
            return Response("You have no permission to upload images in this folder or folder doesn't exist",
                            status=status.HTTP_400_BAD_REQUEST)
        images = request.FILES.getlist('images', [])
        if not images:
            return Response('There is no image', status=status.HTTP_400_BAD_REQUEST)
        data = []
        total_size = 0.0

        # Use ThreadPoolExecutor to process images concurrently
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_image, image, folder, request.user) for image in images]

            for future in as_completed(futures):
                result, error = future.result()
                if error:
                    return Response(error, status=status.HTTP_400_BAD_REQUEST)
                data.append(result)
                total_size += result['image_size']

        folder.size += total_size
        folder.save()
        return Response(data, status=status.HTTP_201_CREATED)


class ImageListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ImageSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid)
        except Folder.DoesNotExist:
            return None

    def get_queryset(self):
        folder_uuid = self.kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response("There is no folder.", status=status.HTTP_400_BAD_REQUEST)
        return Image.objects.filter(folder=folder)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomUserUpdateSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        image = request.FILES.get('image')
        if image:
            image_data = BytesIO(image.read())  # Wrap image data in BytesIO

            compressed_image_file = compressed_image(
                image_data=image_data,
                original_file_name=image.name,
                height=242,
                width=242
            )

            request.user.profile_picture = compressed_image_file
            request.user.save()
            request.data.pop('image')
        serializer = CustomUserUpdateSerializer(request.user, request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfilePictureUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileImageUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        image = request.FILES.get('image')

        if image:
            image_data = BytesIO(image.read())  # Wrap image data in BytesIO

            compressed_image_file = compressed_image(
                image_data=image_data,
                original_file_name=image.name,
                height=242,
                width=242
            )

            request.user.profile_picture = compressed_image_file
            request.user.save()

        serializer = ProfileImageUpdateSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MoveToTrashImage(generics.UpdateAPIView):
    queryset = Image.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ImageUUIDListSerializer

    def get_queryset(self):
        image_list = self.request.data.get('images', [])
        return Image.objects.filter(image_uuid__in=image_list, created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        trash_folder, created = Folder.objects.get_or_create(name='Trash')
        images = self.get_queryset()

        for image in images:
            image.previous_folder = image.folder
            image.folder = trash_folder
            image.added_to_trash_date = date.today()
            image.save()
        return Response(status=status.HTTP_200_OK)


class DeleteImagePermanently(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ImageUUIDListSerializer

    def get_queryset(self):
        image_list = self.request.data.get('images', [])
        return Image.objects.filter(image_uuid__in=image_list, created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = self.get_queryset()
        if images:
            keys = [image.s3_link for image in images]

            deleted = delete_objects(keys)

            if not deleted:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            for image in images:
                image.folder.size -= image.image_size
                image.folder.save()

            images.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class MoveFolderToTrash(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=self.request.user)
        except Folder.DoesNotExist:
            return None

    def put(self, request, *args, **kwargs):
        folder_uuid = kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response('There is no folder associated with this id', status=status.HTTP_400_BAD_REQUEST)
        trash, _ = Folder.objects.get_or_create(name='Trash')

        images = Image.objects.filter(folder=folder)
        images.update(previous_folder=folder, added_to_trash_date=date.today(), folder=trash)
        folder.added_to_trash = True
        folder.added_to_trash_date = date.today()
        folder.save()
        return Response(status=status.HTTP_200_OK)


class DeleteFolderPermanently(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=self.request.user)
        except Folder.DoesNotExist:
            return None

    def delete(self, request, *args, **kwargs):
        folder_uuid = kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response(status=status.HTTP_204_NO_CONTENT)
        images = Image.objects.filter(Q(folder=folder) | Q(previous_folder=folder))
        keys = [image.s3_link for image in images]
        if keys:
            deleted = delete_objects(keys)
            if not deleted:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        images.delete()
        folder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RestoreFolderFromTrash(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=self.request.user, added_to_trash=True)
        except Folder.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        folder_uuid = kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response('There is no folder associated with this id', status=status.HTTP_400_BAD_REQUEST)

        images = Image.objects.filter(Q(folder=folder) | Q(previous_folder=folder))
        images.update(folder=folder, previous_folder=None, added_to_trash_date=None)
        folder.added_to_trash = False
        folder.added_to_trash_date = None
        folder.save()
        return Response(status=status.HTTP_200_OK)


class RestoreImageFromTrash(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ImageUUIDListSerializer

    def get_queryset(self):
        image_list = self.request.data.get('images', [])
        return Image.objects.filter(image_uuid__in=image_list, created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        image_list = self.get_queryset()
        data = []
        for image in image_list:
            image.folder = image.previous_folder
            image.previous_folder = None
            image.trash_folder = None
            image.added_to_trash_date = None
            image.save()
            data.append(image)
        serializer = ImageSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrashDataView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TrashResponseSerializer

    def get_queryset(self):
        # This method should return a queryset, but for combined data, we will handle it in `list`.
        return []

    def list(self, request, *args, **kwargs):
        user = request.user

        # Get folders added to trash
        trashed_folders = Folder.objects.filter(added_to_trash=True, created_by=user)

        # Get images whose previous folder was not added to trash
        trashed_images = Image.objects.filter(
            created_by=user,
            folder__name='Trash',
            previous_folder__added_to_trash=False,
            previous_folder__created_by=user
        )

        # Serialize the data
        serialized_folders = FolderSerializer(trashed_folders, many=True).data
        serialized_images = ImageSerializer(trashed_images, many=True).data

        # Create custom response structure
        response_data = {
            'folders': serialized_folders,
            'images': serialized_images
        }

        return Response(response_data, status=status.HTTP_200_OK)


class TrashFolderDataView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ImageSerializer

    def get_queryset(self):
        folder_uuid = self.kwargs.get('folder_uuid', '')
        trash = Folder.objects.get_or_create(name='Trash')[0]
        return Image.objects.filter(folder=trash, created_by=self.request.user,
                                    previous_folder__folder_uuid=folder_uuid)


class FolderUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderUpdateSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=self.request.user)
        except Folder.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        folder_uuid = kwargs.get('folder_uuid')
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.data.get('name').lower() == 'trash':
            return Response('You can not name a folder trash.', status=status.HTTP_400_BAD_REQUEST)
        serializer = FolderUpdateSerializer(folder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FolderShareView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TrashResponseSerializer

    def get_queryset(self):
        folder_uuid = self.kwargs.get('folder_uuid')
        try:
            return Folder.objects.get(folder_uuid=folder_uuid)
        except Folder.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        folder = self.get_queryset()
        if not folder or folder.name.lower() == 'trash':
            return Response("There is no folder associate with this name", status=status.HTTP_404_NOT_FOUND)

        serialized_folders = FolderSerializer(folder).data
        folder_images = Image.objects.filter(folder=folder)
        serialized_images = ImageSerializer(folder_images, many=True).data

        # Create custom response structure
        response_data = {
            'folders': serialized_folders,
            'images': serialized_images
        }
        return Response(response_data, status=status.HTTP_200_OK)


class SharedImageView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ImageSerializer

    def get_queryset(self):
        image_uuid = self.kwargs.get('image_uuid')
        try:
            return Image.objects.get(image_uuid=image_uuid)
        except Image.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        image = self.get_queryset()
        if not image:
            return Response('there is no Image associate with this id', status=status.HTTP_400_BAD_REQUEST)

        serialized_image = ImageSerializer(image).data
        return Response(serialized_image, status=status.HTTP_200_OK)


class FaceMatchesView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ImageSerializer

    def get_folder(self, folder_uuid):
        try:
            return Folder.objects.get(folder_uuid=folder_uuid)
        except Folder.DoesNotExist:
            return None

    def post(self, request, *args, **kwargs):
        image = request.FILES.get('image')
        if not image:
            return Response('There is no Image please upload an Image', status=status.HTTP_200_OK)
        folder_uuid = kwargs.get('folder_uuid', '')
        if not folder_uuid:
            return Response('Please add folder uuid', status=status.HTTP_400_BAD_REQUEST)
        folder = self.get_folder(folder_uuid=folder_uuid)
        if not folder:
            return Response('Folder not found', status=status.HTTP_400_BAD_REQUEST)
        face_uuids = []
        faces = match_faces(image_data=image.read())
        if not faces:
            return Response({'your_image': []}, status=status.HTTP_200_OK)
        for face in faces:
            face_uuids.append(face['image_uuid'])
        serializer = ImageSerializer(Image.objects.filter(image_uuid__in=face_uuids, folder=folder), many=True)
        return Response({'your_image': serializer.data}, status=status.HTTP_200_OK)


class HomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)


class FolderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderSerializer

    def get(self, request, *args, **kwargs):
        folders = Folder.objects.filter(created_by=self.request.user, added_to_trash=False)
        data = []
        for folder in folders:
            serializer = FolderSerializer(folder)
            d = serializer.data
            images = []
            if Image.objects.filter(folder=folder).count() >= 6:
                images = ImageObjectLinkSerializer(Image.objects.filter(folder=folder)[:6], many=True).data
            i = []
            for image in images:
                i.append(image['compact_image'])
            d['images'] = i
            data.append(d)
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AnalyticsSerializer

    def get(self, request, *args, **kwargs):
        data = {'number_of_images': Image.objects.exclude(folder__name='Trash').count(),
                'number_of_gallery': Folder.objects.exclude(Q(name='Trash') | Q(added_to_trash=True)).count()}

        return Response(AnalyticsSerializer(data).data, status=status.HTTP_200_OK)


class DownloadLogListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = DownloadLogsSerializer

    def get_queryset(self):
        return DownloadLog.objects.all().order_by('-id')

    def perform_create(self, serializer):
        serializer.save()


class UploadFolderCoverImage(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FolderCoverImageSerializer
    lookup_field = 'folder_uuid'

    def get_queryset(self):
        return Folder.objects.filter(created_by=self.request.user)

    def get_object(self):
        folder_uuid = self.kwargs.get('folder_uuid')
        try:
            return Folder.objects.get(folder_uuid=folder_uuid, created_by=self.request.user)
        except Folder.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        image = self.request.FILES.get('image')
        if not image:
            return Response('Please upload image.', status=status.HTTP_400_BAD_REQUEST)

        folder = self.get_object()
        if not folder:
            return Response('Folder does not exist', status=status.HTTP_400_BAD_REQUEST)

        image_data = BytesIO(image.read())  # Wrap image data in BytesIO

        compressed_image_file = compressed_image(
            image_data=image_data,
            original_file_name=image.name,
            height=1920,
            width=650
        )
        folder.cover_photo = compressed_image_file
        folder.save()
        serializer = FolderSerializer(folder)
        return Response(serializer.data, status=status.HTTP_200_OK)
