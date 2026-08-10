from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import ArtistRequestHistorySerializer, ArtistRequestListSerializer, ArtistRequestUpdateSerializer, ListenerRegistrationSerializer, LoginSerializer, ArtistRequestSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from drf_spectacular.utils import extend_schema
from .models import ArtistRequest
from .permissions import IsAdminOrSupport, IsListenerOrArtist

class ListenerRegisterView(generics.CreateAPIView):
    serializer_class = ListenerRegistrationSerializer
    permission_classes = [AllowAny]

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'role': user.role,
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArtistRequestCreateView(generics.CreateAPIView):
    serializer_class = ArtistRequestSerializer
    permission_classes = [IsAuthenticated]
    queryset = ArtistRequest.objects.all()  # required for CreateAPIView

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # alternative to using context

class ArtistRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSupport]
    serializer_class = ArtistRequestListSerializer
    queryset = ArtistRequest.objects.all().order_by('-created_at')

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

class ArtistRequestHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = ArtistRequestHistorySerializer

    def get_queryset(self):
        # Return only requests belonging to the current user, ordered by newest first
        return ArtistRequest.objects.filter(user=self.request.user).order_by('-created_at')

class ArtistRequestUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSupport]
    serializer_class = ArtistRequestUpdateSerializer
    queryset = ArtistRequest.objects.all()
    http_method_names = ['patch', 'put']  # allow both