from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Añade el rol de negocio para que DRF pueda aplicar autorización RBAC."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = getattr(getattr(user, 'profile', None), 'role', 'STUDENT')
        return token