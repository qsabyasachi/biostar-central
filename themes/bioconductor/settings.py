from biostar.forum.settings import *
import os


DEBUG = True

#NAVBAR_TAGS = []

#END_CATEGORIES = []

# These are the tags that always show up in the tag recommendation dropdown.
#POST_TAG_LIST = NAVBAR_TAGS + ["software error"]

HTTP_PROTOCOL = "http"

CUSTOM_THEME = os.path.abspath(os.path.join(BASE_DIR, 'themes', 'bioconductor'))

STATICFILES_DIRS = [os.path.join(CUSTOM_THEME, 'static')]

if DEBUG:
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )
else:
    TEMPLATE_LOADERS = (
        'django.template.loaders.cached.Loader',
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )


# Template specific settings.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(CUSTOM_THEME, 'templates'), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'string_if_invalid': "**MISSING**",
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.messages.context_processors.messages',
                'biostar.context.main',
            ],
            #'loaders': [TEMPLATE_LOADERS]
        },
    },
]
# The site logo image on top navigation bar
SITE_LOGO = "bioconductor_logo.jpg"

# How many recent objects to show in the feed.
VOTE_FEED_COUNT = 5
LOCATION_FEED_COUNT = 5
AWARDS_FEED_COUNT = 5
REPLIES_FEED_COUNT = 5

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'biostar.wsgi.application'

# These parameters will be inserted into the database automatically.
SITE_NAME = "support.bioconductor.org"
SITE_DOMAIN = "support.bioconductor.org"

# What domain will handle the replies.
EMAIL_REPLY_PATTERN = "reply+%s+code@bioconductor.org"

# The format of the email that is sent
EMAIL_FROM_PATTERN = u'''"%s [bioc]" <%s>'''

# The subject of the reply goes here
EMAIL_REPLY_SUBJECT = u"[bioc] %s"


# On deployed servers the following must be set.
EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False

# Tries to load up secret settings from a predetermined module
try:
    from conf.run.secrets import *
    print(f"Loaded secrets from: conf.run.secrets")
except Exception as exc:
    print(f"Secrets module not imported: {exc}")
