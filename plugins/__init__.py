from aiohttp import web
from .route import routes

# --- MODIFIED THIS FUNCTION ---
async def web_server(bots):
    web_app = web.Application(client_max_size=30000000)
    web_app['bots'] = bots  # Attach the list of bot instances to the app
    web_app.add_routes(routes)
    return web_app
