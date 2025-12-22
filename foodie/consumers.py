from channels.generic.websocket import AsyncJsonWebsocketConsumer


class FoodieConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if user is None or user.is_anonymous:
            await self.close()
            return
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def foodie_event(self, event):
        # event contains: type, event, payload
        await self.send_json({
            "event": event.get("event"),
            "payload": event.get("payload", {}),
        })
