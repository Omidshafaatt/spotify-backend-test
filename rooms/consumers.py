# rooms/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Room
from .serializers import RoomStatusSerializer

User = get_user_model()


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if not token:
            await self.close()
            return

        # Authenticate user with token
        user = await self.get_user_from_token(token)
        if not user:
            await self.close()
            return

        # Set user in scope
        self.scope['user'] = user

        self.room_id = self.scope['url_route']['kwargs']['uuid']
        self.room_group_name = f'room_{self.room_id}'

        # Check if user is a member
        if not await self.is_member(user, self.room_id):
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current room state to the new member
        room = await self.get_room(self.room_id)
        state = await self.get_room_state(room, user)
        await self.send(text_data=json.dumps({
            'type': 'state_update',
            'data': state
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'play':
            room = await self.get_room(self.room_id)
            if room.current_song and not room.is_playing:
                room.is_playing = True
                await self.update_room(room, ['is_playing', 'updated_at'])
                await self.broadcast_state(room, self.scope['user'])

        elif action == 'pause':
            room = await self.get_room(self.room_id)
            if room.is_playing:
                room.is_playing = False
                await self.update_room(room, ['is_playing', 'updated_at'])
                await self.broadcast_state(room, self.scope['user'])

        elif action == 'seek':
            position = data.get('position')
            if position is not None:
                room = await self.get_room(self.room_id)
                room.current_position = float(position)
                await self.update_room(room, ['current_position', 'updated_at'])
                await self.broadcast_state(room, self.scope['user'])

        elif action == 'upload':
            # Upload is handled via REST; we just broadcast after upload.
            # But we can also handle it here if we want to accept file via WS.
            pass

        elif action == 'leave':
            # Handle leave via REST; notify via WS after member leaves.
            pass

    async def broadcast_state(self, room, user):
        """Send the current room state to all members of the group."""
        state = await self.get_room_state(room, user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'state_update',
                'data': state
            }
        )

    async def state_update(self, event):
        """Send state update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'state_update',
            'data': event['data']
        }))

    # ---- Database helpers ----

    @database_sync_to_async
    def is_member(self, user, room_id):
        room = get_object_or_404(Room, id=room_id)
        return room.members.filter(id=user.id).exists()

    @database_sync_to_async
    def get_room(self, room_id):
        return get_object_or_404(Room, id=room_id)

    @database_sync_to_async
    def update_room(self, room, fields):
        room.save(update_fields=fields)

    @database_sync_to_async
    def get_room_state(self, room, user):
        serializer = RoomStatusSerializer(room, context={'request': None})
        return serializer.data

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None