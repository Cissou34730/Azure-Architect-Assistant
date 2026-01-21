import importlib
mods = [
    'backend.app.services.ai.ai_config',
    'backend.app.core.app_settings',
    'backend.config.settings'
]
for m in mods:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'ERR', e)

