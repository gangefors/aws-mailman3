# All Social login providers has been removed
INSTALLED_APPS = [
    'hyperkitty',
    'postorius',
    'django_mailman3',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_gravatar',
    'compressor',
    'haystack',
    'django_extensions',
    'django_q',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
]

# Enable full text search in Hyperkitty
# If this is added after first launch you must run:
#   docker-compose exec mailman-web ./manage.py rebuild_index
# to rebuild the index.
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'xapian_backend.XapianEngine',
        'PATH': "/opt/mailman-web-data/fulltext_index",
    },
}
