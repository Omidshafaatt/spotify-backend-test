# rooms/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Room
from .serializers import RoomCreateSerializer, RoomStatusSerializer, UploadSongSerializer
from .utils import broadcast_room_state


class CreateRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room = Room.objects.create()
        room.members.add(request.user)
        # No need to broadcast yet because no other members
        serializer = RoomCreateSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JoinRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)
        if not room.members.filter(id=request.user.id).exists():
            room.members.add(request.user)
            # Broadcast updated member list to all members
            broadcast_room_state(room, request.user)
        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RoomStatusView(APIView):
    """
    GET /api/rooms/<uuid>/status/
    Returns the current status of the room (members, song, position, etc.)
    Only members can access this.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UploadSongView(APIView):
    """
    POST /api/rooms/<uuid>/upload/
    Upload a new song to the room.
    Only members can upload. After upload, the song becomes the current song,
    position resets to 0, and playing state becomes True.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UploadSongSerializer(data=request.data)
        if serializer.is_valid():
            # Update room with new song
            room.current_song = serializer.validated_data['audio_file']
            room.current_song_title = (
                serializer.validated_data.get('title', '') or
                serializer.validated_data['audio_file'].name
            )
            room.current_position = 0.0
            room.is_playing = True
            room.save()

            # Broadcast new song to all members
            broadcast_room_state(room, request.user)

            status_serializer = RoomStatusSerializer(room, context={'request': request})
            return Response(status_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlayRoomView(APIView):
    """
    POST /api/rooms/<uuid>/play/
    Resumes playback for the room.
    Only members can control playback.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not room.current_song:
            return Response(
                {"detail": "No song uploaded yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        room.is_playing = True
        room.save(update_fields=['is_playing', 'updated_at'])

        # Broadcast play state
        broadcast_room_state(room, request.user)

        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PauseRoomView(APIView):
    """
    POST /api/rooms/<uuid>/pause/
    Pauses playback for the room.
    Only members can control playback.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        room.is_playing = False
        room.save(update_fields=['is_playing', 'updated_at'])

        # Broadcast pause state
        broadcast_room_state(room, request.user)

        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SeekRoomView(APIView):
    """
    POST /api/rooms/<uuid>/seek/
    Seeks to a specific position (in seconds) in the current song.
    Only members can control playback.
    Request body: {"position": <float>}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not room.current_song:
            return Response(
                {"detail": "No song uploaded yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        position = request.data.get('position')
        if position is None:
            return Response(
                {"detail": "Position is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            position = float(position)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Position must be a number."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if position < 0:
            return Response(
                {"detail": "Position cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )

        room.current_position = position
        room.save(update_fields=['current_position', 'updated_at'])

        # Broadcast seek position
        broadcast_room_state(room, request.user)

        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveRoomView(APIView):
    """
    POST /api/rooms/<uuid>/leave/
    Removes the authenticated user from the room.
    If the room becomes empty, it is automatically deleted.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        room = get_object_or_404(Room, id=uuid)

        if not room.members.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are not a member of this room."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Remove user from members
        room.members.remove(request.user)

        # If room is now empty, delete it
        if room.is_empty():
            # Broadcast 'room_closed' message before deletion
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'room_{room.id}',
                {
                    'type': 'room_closed',
                    'data': {'detail': 'The room has been closed because all members left.'}
                }
            )
            room.delete()
            return Response(
                {"detail": "You left the room. The room has been deleted because it was empty."},
                status=status.HTTP_200_OK
            )

        # Otherwise, broadcast updated member list and room state
        broadcast_room_state(room, request.user)

        serializer = RoomStatusSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)