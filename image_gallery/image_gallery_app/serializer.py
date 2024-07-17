from rest_framework import serializers
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.conf import settings
from django.core.mail import send_mail


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Customizes JWT default Serializer to add more information about user"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['is_admin'] = user.is_superuser
        return token


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        user = CustomUser.objects.create_user(email=email, **validated_data)
        user.set_password(password)
        user.save()

        self.send_password_email(email, password)
        return user

    def send_password_email(self, email, password):
        subject = 'Your Account Password'
        message = f'Your account has been created. Here is your password: {password}'
        from_email = settings.EMAIL_HOST_USER  # Change this to your "from" email address
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list)


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'
        read_only_fields = ['created_by', 'previous_folder', 'created_on', 'size']

    def validate_name(self, value):
        if value.lower() == 'trash':
            raise serializers.ValidationError("Folder name can't be 'unpaid'.")
        return value


class ImageSerializer(serializers.ModelSerializer):
    folder_info = FolderSerializer(source='folder', required=False, read_only=True)
    previous_folder_info = FolderSerializer(source='previous_folder', required=False, read_only=True)

    class Meta:
        model = Image
        fields = '__all__'


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'first_name', 'email', 'last_name', 'phone', 'profile_picture', 'date_of_birth')
        read_only_field = ('id', 'username', 'email')


class ProfileImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['profile_picture']


class ImageUUIDListSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False
    )


class TrashResponseSerializer(serializers.Serializer):
    folders = FolderSerializer(many=True)
    images = ImageSerializer(many=True)


class FolderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'
        read_only_fields = ['folder_uuid', 'created_by', 'previous_folder', 'created_on', 'size', 'added_to_trash',
                            'added_to_trash_date']


class ImageObjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['compact_image']


class AnalyticsSerializer(serializers.Serializer):
    number_of_images = serializers.IntegerField()
    number_of_gallery = serializers.IntegerField()


class DownloadLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadLog
        fields = '__all__'


class FolderCoverImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'
        read_only_fields = (
            'folder_uuid', 'created_by', 'previous_folder', 'created_on', 'size', 'event_date', 'name',
            'added_to_trash', 'added_to_trash_date')
