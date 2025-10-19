from pathlib import Path

# Project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # ensure this is present
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # keep your context processors here
            ],
        },
    },
]