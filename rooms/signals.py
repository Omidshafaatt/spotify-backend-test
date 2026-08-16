# rooms/signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Room
import os


@receiver(post_delete, sender=Room)
def delete_room_file(sender, instance, **kwargs):
    if instance.current_song:
        if os.path.isfile(instance.current_song.path):
            os.remove(instance.current_song.path)