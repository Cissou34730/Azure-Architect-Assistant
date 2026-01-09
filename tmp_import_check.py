import importlib
mods = [
    'backend.app.services.ai.config',
    'backend.app.core.config',
    'backend.config.settings'
]
for m in mods:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'ERR', e)
