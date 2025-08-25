from aiohttp import web
import markdown
import os
import asyncio
from helper.helper_func import send_files # Import the refactored function

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    # Correct the path to point to the project's root README.md
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    if not os.path.exists(readme_path):
        return web.Response(text="README.md not found", status=404)

    with open(readme_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html = markdown.markdown(md_text, extensions=["fenced_code", "codehilite", "tables"])

    html_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>README</title>
        <style>
            body {{ font-family: sans-serif; max-width: 900px; margin: auto; padding: 2rem; background: #f9f9f9; color: #333; }}
            pre {{ background: #282c34; color: #f8f8f2; padding: 1em; overflow-x: auto; border-radius: 8px; }}
            code {{ font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace; }}
            table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
            th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
            h1, h2, h3 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
        </style>
    </head>
    <body>{html}</body>
    </html>
    """
    return web.Response(text=html_page, content_type="text/html")


# --- NEW WEB HANDLER FOR SECURE FILE RETRIEVAL ---
@routes.get("/get/{token}")
async def get_file_handler(request):
    token = request.match_info.get("token")
    if not token:
        return web.Response(text="Missing token.", status=400)

    bots = request.app.get('bots')
    if not bots:
        return web.Response(text="Bot service is temporarily unavailable.", status=503)

    # Use the first bot's DB instance for the initial lookup.
    # The session_name stored with the token ensures we use the correct bot later.
    db = bots[0].mongodb 
    req_data = await db.get_webrequest(token)

    if not req_data:
        return web.Response(
            text="<h1>Link Expired or Invalid</h1><p>This verification link has already been used or is older than 5 minutes. Please request a new link from the bot.</p>",
            content_type="text/html",
            status=403
        )

    # Immediately delete the token on first use to prevent replay attacks.
    await db.delete_webrequest(token)

    # Extract data needed to process the request
    user_id = req_data['user_id']
    b64_string = req_data['b64_string']
    session_name = req_data['session']
    
    # Find the specific bot instance that this request belongs to
    target_bot = next((b for b in bots if b.session_name == session_name), None)
    
    if not target_bot:
        return web.Response(text=f"Bot instance '{session_name}' is currently offline.", status=503)
        
    # Log the user's IP address using their specific bot's DB connection
    ip_address = request.headers.get("X-Forwarded-For") or request.remote
    await target_bot.mongodb.log_user_ip(user_id, ip_address, target_bot.session_name)
    
    # Schedule the file sending as a background task. This immediately frees up
    # the web server to respond to the user without waiting for files to send.
    asyncio.create_task(send_files(target_bot, user_id, b64_string))
    
    # Return a success page to the user's browser.
    return web.Response(
        text="<h1>✅ Success!</h1><p>Your file is being sent to you on Telegram. Please check your chat with the bot.</p>",
        content_type="text/html",
        status=200
    )
