from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username','first_name', 'last_name', 'email', 'password', 'password2',]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("A user with this username already exists."))
        return value
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(_("Password must be at least 8 characters long."))
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(_("Password must contain at least one digit."))
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError(_("Password must contain at least one letter."))
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(_("Password must contain at least one uppercase letter."))
        if not any(char.islower() for char in value):
            raise serializers.ValidationError(_("Password must contain at least one lowercase letter."))
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in value):
            raise serializers.ValidationError(_("Password must contain at least one special character."))
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": _("Passwords do not match.")})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Old password is not correct"))
        return value

    @staticmethod
    def _longest_common_substring(s1, s2):
        if not s1 or not s2:
            return 0

        len1, len2 = len(s1), len(s2)
        prev = [0] * (len2 + 1)
        curr = [0] * (len2 + 1)
        max_len = 0

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i - 1] == s2[j - 1]:
                    curr[j] = prev[j - 1] + 1
                    max_len = max(max_len, curr[j])
                else:
                    curr[j] = 0
            prev, curr = curr, prev  # swap for next iteration

        return max_len

    def validate(self, attrs):
        old_password = attrs['old_password']
        new_password = attrs['new_password']

        common_len = self._longest_common_substring(old_password, new_password)
        similarity_ratio = common_len / len(new_password)

        if similarity_ratio >= 0.5:
            raise serializers.ValidationError(
                _("New password is too similar to the old one. Please choose a more distinct password.")
            )
        return attrs

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(_("New password must be at least 8 characters long"))
        

class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username','first_name', 'last_name', 'email', 'is_active',]


