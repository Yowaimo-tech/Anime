from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.pyromod import ListenerTimeout
import json

# Import the main settings panel to navigate back
from .settings import settings_panel

# Shortener service configurations
SHORTENER_SERVICES = {
    'custom': {
        'name': 'Custom Shortener',
        'requires_url': True,
        'requires_api': True,
        'fields': ['short_url', 'short_api']
    },
    'tinyurl': {
        'name': 'TinyURL',
        'requires_url': False,
        'requires_api': False,
        'fields': []
    },
    'dagd': {
        'name': 'da.gd',
        'requires_url': False,
        'requires_api': False,
        'fields': []
    },
    'isgd': {
        'name': 'is.gd',
        'requires_url': False,
        'requires_api': False,
        'fields': []
    },
    'cuttly': {
        'name': 'Cutt.ly',
        'requires_url': False,
        'requires_api': True,
        'fields': ['cuttly_api_key']
    },
    'shortio': {
        'name': 'Short.io',
        'requires_url': False,
        'requires_api': True,
        'fields': ['shortio_api_key', 'shortio_domain']
    }
}

# Shortener modes
SHORTENER_MODES = {
    'sequential': 'Sequential (Try in order)',
    'random': 'Random Selection',
    'priority': 'Priority (Fastest first)',
    'fallback': 'Primary + Fallback'
}

# This function displays the shortener sub-menu
async def shortner_settings_main(client: Client, query: CallbackQuery):
    await query.answer()
    
    # Get current settings
    current_service = getattr(client, 'shortener_service', 'custom')
    current_mode = getattr(client, 'shortener_mode', 'sequential')
    enabled_services = getattr(client, 'enabled_services', ['tinyurl', 'dagd', 'isgd', 'cuttly', 'shortio', 'custom'])
    
    # Display API keys (masked)
    api_key_display = f"{'*' * (len(client.short_api) - 4)}{client.short_api[-4:]}" if client.short_api and len(client.short_api) > 4 else "Not Set"
    cuttly_api_display = f"{'*' * (len(client.cuttly_api_key) - 4)}{client.cuttly_api_key[-4:]}" if hasattr(client, 'cuttly_api_key') and client.cuttly_api_key and len(client.cuttly_api_key) > 4 else "Not Set"
    shortio_api_display = f"{'*' * (len(client.shortio_api_key) - 4)}{client.shortio_api_key[-4:]}" if hasattr(client, 'shortio_api_key') and client.shortio_api_key and len(client.shortio_api_key) > 4 else "Not Set"
    
    msg = f"""<blockquote>**Shortener Settings:**</blockquote>

**Current Service:** `{SHORTENER_SERVICES.get(current_service, {}).get('name', 'Custom')}`
**Current Mode:** `{SHORTENER_MODES.get(current_mode, 'Sequential')}`

**🔧 Configuration:**
• Custom URL: `{client.short_url or "Not Set"}`
• Custom API: `{api_key_display}`
• Cutt.ly API: `{cuttly_api_display}`
• Short.io API: `{shortio_api_display}`
• Short.io Domain: `{getattr(client, 'shortio_domain', 'Not Set')}`

**Enabled Services:** {', '.join(enabled_services)}

__Manage your URL shortener configuration. Changes are saved instantly.__
"""
    
    # Create service selection buttons
    service_buttons = []
    for service_id, service_info in SHORTENER_SERVICES.items():
        is_active = current_service == service_id
        prefix = "✅" if is_active else "☑️"
        service_buttons.append(
            InlineKeyboardButton(
                f"{prefix} {service_info['name']}", 
                callback_data=f"set_service_{service_id}"
            )
        )
    
    # Create mode selection buttons
    mode_buttons = []
    for mode_id, mode_name in SHORTENER_MODES.items():
        is_active = current_mode == mode_id
        prefix = "🔘" if is_active else "⚪"
        mode_buttons.append(
            InlineKeyboardButton(
                f"{prefix} {mode_name}", 
                callback_data=f"set_mode_{mode_id}"
            )
        )
    
    reply_markup = InlineKeyboardMarkup([
        # Service selection row
        [InlineKeyboardButton('🎯 Select Service', 'service_selection')],
        
        # Mode selection row
        [InlineKeyboardButton('⚙️ Shortener Mode', 'mode_selection')],
        
        # Configuration buttons
        [
            InlineKeyboardButton('🔧 Custom URL', 'change_short_url'),
            InlineKeyboardButton('🔑 Custom API', 'change_short_api')
        ],
        [
            InlineKeyboardButton('🔑 Cutt.ly API', 'change_cuttly_api'),
            InlineKeyboardButton('🌐 Short.io Config', 'shortio_config')
        ],
        [
            InlineKeyboardButton('📋 Manage Services', 'manage_services'),
            InlineKeyboardButton('⚡ Test Shortener', 'test_shortener')
        ],
        [InlineKeyboardButton('◂ Back to Settings', 'settings')]
    ])
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

# Service selection menu
async def service_selection_menu(client: Client, query: CallbackQuery):
    await query.answer()
    
    current_service = getattr(client, 'shortener_service', 'custom')
    
    msg = "**Select Shortener Service:**\n\nChoose your preferred URL shortening service. Services marked with ✅ are currently active."
    
    buttons = []
    for service_id, service_info in SHORTENER_SERVICES.items():
        is_active = current_service == service_id
        prefix = "✅" if is_active else "☑️"
        buttons.append([
            InlineKeyboardButton(
                f"{prefix} {service_info['name']}", 
                callback_data=f"set_service_{service_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("◂ Back", "shortner_settings")])
    
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

# Mode selection menu
async def mode_selection_menu(client: Client, query: CallbackQuery):
    await query.answer()
    
    current_mode = getattr(client, 'shortener_mode', 'sequential')
    
    msg = """**Select Shortener Mode:**

• **Sequential**: Try services in order until one works
• **Random**: Randomly select from available services  
• **Priority**: Use fastest/most reliable service first
• **Fallback**: Use primary service, fallback to others
"""
    
    buttons = []
    for mode_id, mode_name in SHORTENER_MODES.items():
        is_active = current_mode == mode_id
        prefix = "🔘" if is_active else "⚪"
        buttons.append([
            InlineKeyboardButton(
                f"{prefix} {mode_name}", 
                callback_data=f"set_mode_{mode_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("◂ Back", "shortner_settings")])
    
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

# Manage enabled services menu
async def manage_services_menu(client: Client, query: CallbackQuery):
    await query.answer()
    
    enabled_services = getattr(client, 'enabled_services', ['tinyurl', 'dagd', 'isgd', 'cuttly', 'shortio', 'custom'])
    
    msg = "**Manage Enabled Services:**\n\nToggle services on/off. Only enabled services will be used for shortening."
    
    buttons = []
    for service_id, service_info in SHORTENER_SERVICES.items():
        is_enabled = service_id in enabled_services
        prefix = "✅" if is_enabled else "❌"
        buttons.append([
            InlineKeyboardButton(
                f"{prefix} {service_info['name']}", 
                callback_data=f"toggle_service_{service_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Reset to Default", "reset_services")])
    buttons.append([InlineKeyboardButton("◂ Back", "shortner_settings")])
    
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

# Short.io configuration menu
async def shortio_config_menu(client: Client, query: CallbackQuery):
    await query.answer()
    
    api_key = getattr(client, 'shortio_api_key', 'Not Set')
    domain = getattr(client, 'shortio_domain', 'Not Set')
    
    api_display = f"{'*' * (len(api_key) - 4)}{api_key[-4:]}" if api_key and api_key != 'Not Set' else "Not Set"
    
    msg = f"""**Short.io Configuration:**

**API Key:** `{api_display}`
**Domain:** `{domain}`

Configure your Short.io settings for URL shortening.
"""
    
    buttons = [
        [InlineKeyboardButton("🔑 Change API Key", "change_shortio_api")],
        [InlineKeyboardButton("🌐 Change Domain", "change_shortio_domain")],
        [InlineKeyboardButton("◂ Back", "shortner_settings")]
    ]
    
    await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

# Test shortener functionality
async def test_shortener_func(client: Client, query: CallbackQuery):
    await query.answer()
    
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the URL you want to test shortening:\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
            return await shortner_settings_main(client, query)
        
        test_url = ask_msg.text.strip()
        
        # Import the shortener function
        from .url_shortener import URLShortener, ShortenerSettings, ShortenerMode
        
        current_mode = getattr(client, 'shortener_mode', 'sequential')
        settings = ShortenerSettings(mode=ShortenerMode(current_mode))
        shortener = URLShortener(client, settings)
        
        await ask_msg.reply("🔄 Testing URL shortening...")
        
        result = shortener.get_short(test_url)
        
        if result != test_url:
            await ask_msg.reply(f"✅ **Shortening Successful!**\n\n**Original:** `{test_url}`\n**Shortened:** `{result}`")
        else:
            await ask_msg.reply(f"❌ **Shortening Failed!**\n\nAll services failed to shorten the URL: `{test_url}`")
            
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    except Exception as e:
        await query.message.reply(f"❌ Error testing shortener: {str(e)}")
    
    await shortner_settings_main(client, query)

# Callback handlers
@Client.on_callback_query(filters.regex("^shortner_settings$"))
async def shortner_settings_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await shortner_settings_main(client, query)

@Client.on_callback_query(filters.regex("^service_selection$"))
async def service_selection_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await service_selection_menu(client, query)

@Client.on_callback_query(filters.regex("^mode_selection$"))
async def mode_selection_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await mode_selection_menu(client, query)

@Client.on_callback_query(filters.regex("^manage_services$"))
async def manage_services_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await manage_services_menu(client, query)

@Client.on_callback_query(filters.regex("^shortio_config$"))
async def shortio_config_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await shortio_config_menu(client, query)

@Client.on_callback_query(filters.regex("^test_shortener$"))
async def test_shortener_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    await test_shortener_func(client, query)

@Client.on_callback_query(filters.regex("^set_service_(.+)$"))
async def set_service_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    
    service_id = query.matches[0].group(1)
    client.shortener_service = service_id
    
    # Save settings
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    
    await query.answer(f"Service set to {SHORTENER_SERVICES[service_id]['name']}", show_alert=True)
    await shortner_settings_main(client, query)

@Client.on_callback_query(filters.regex("^set_mode_(.+)$"))
async def set_mode_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    
    mode_id = query.matches[0].group(1)
    client.shortener_mode = mode_id
    
    # Save settings
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    
    await query.answer(f"Mode set to {SHORTENER_MODES[mode_id]}", show_alert=True)
    await shortner_settings_main(client, query)

@Client.on_callback_query(filters.regex("^toggle_service_(.+)$"))
async def toggle_service_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    
    service_id = query.matches[0].group(1)
    enabled_services = getattr(client, 'enabled_services', ['tinyurl', 'dagd', 'isgd', 'cuttly', 'shortio', 'custom'])
    
    if service_id in enabled_services:
        enabled_services.remove(service_id)
        action = "disabled"
    else:
        enabled_services.append(service_id)
        action = "enabled"
    
    client.enabled_services = enabled_services
    
    # Save settings
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    
    await query.answer(f"{SHORTENER_SERVICES[service_id]['name']} {action}", show_alert=True)
    await manage_services_menu(client, query)

@Client.on_callback_query(filters.regex("^reset_services$"))
async def reset_services_callback(client: Client, query: CallbackQuery):
    if not (query.from_user.id == client.owner):
        return await query.answer('This can only be used by the owner.', show_alert=True)
    
    client.enabled_services = ['tinyurl', 'dagd', 'isgd', 'cuttly', 'shortio', 'custom']
    
    # Save settings
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    
    await query.answer("Services reset to default", show_alert=True)
    await manage_services_menu(client, query)

# Existing handlers with upgrades
@Client.on_callback_query(filters.regex("^change_short_url$"))
async def change_short_url(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new shortener URL (e.g., `your.domain.com`).\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.short_url = ask_msg.text.strip()
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply(f"✅ Shortener URL updated to: `{client.short_url}`")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    await shortner_settings_main(client, query)

@Client.on_callback_query(filters.regex("^change_short_api$"))
async def change_short_api(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new shortener API key.\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.short_api = ask_msg.text.strip()
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("✅ Shortener API key updated successfully.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    await shortner_settings_main(client, query)

# New handlers for additional services
@Client.on_callback_query(filters.regex("^change_cuttly_api$"))
async def change_cuttly_api(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new Cutt.ly API key.\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.cuttly_api_key = ask_msg.text.strip()
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("✅ Cutt.ly API key updated successfully.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    await shortner_settings_main(client, query)

@Client.on_callback_query(filters.regex("^change_shortio_api$"))
async def change_shortio_api(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new Short.io API key.\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.shortio_api_key = ask_msg.text.strip()
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("✅ Short.io API key updated successfully.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    await shortio_config_menu(client, query)

@Client.on_callback_query(filters.regex("^change_shortio_domain$"))
async def change_shortio_domain(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text="Please send the new Short.io domain (e.g., `your-domain.com`).\n\nType `cancel` to abort.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.shortio_domain = ask_msg.text.strip()
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply(f"✅ Short.io domain updated to: `{client.shortio_domain}`")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout! Operation cancelled.")
    await shortio_config_menu(client, query)
