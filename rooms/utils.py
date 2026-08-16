# rooms/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import RoomStatusSerializer


def broadcast_room_state(room, user=None):
    """Send current room state to all members of the room group."""
    channel_layer = get_channel_layer()
    serializer = RoomStatusSerializer(room, context={'request': None})
    group_name = f'room_{room.id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'state_update',
            'data': serializer.data
        }
    )