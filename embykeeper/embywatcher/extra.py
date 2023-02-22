from embypy import Emby
from embypy.objects import EmbyObject
from embypy.utils.asyncio import async_func


@async_func
async def _mark(self, type, value):
    url = "/Users/{{UserId}}/{type}/{id}".format(type=type, id=self.id)
    if value:
        await self.connector.post(url)
    else:
        await self.connector.delete(url)


def patch():
    EmbyObject._mark = _mark
