"""
The "Editor" group: everything needed to run the website's content, nothing else.

Without this the only way to let somebody publish a news post is to hand them a
superuser account, which also grants user management and every other model in
the project. An editor gets `is_staff=True` plus this group instead:

    python manage.py createsuperuser        # you, once
    # then, in the admin: Users > Add > tick "Staff status" > add to "Editor"

Deliberately excluded: `auth` (users, groups), `admin` (log entries),
`contenttypes` and `sessions`. An editor cannot escalate their own permissions.

This runs from a `post_migrate` receiver rather than a data migration. A data
migration runs exactly once, so the group would freeze at whatever models
existed the day it ran: a database migrated in place would keep the old
permission set while a database built fresh would pick up every model added
since, and the two would drift apart permanently with no way to self-heal.
Reconciling on every `migrate` means both converge on the same set.
"""

from django.db import DEFAULT_DB_ALIAS

GROUP_NAME = "Editor"

# Apps whose models are website content an editor is expected to manage.
CONTENT_APPS = ("catalog", "core", "news", "pages")

# Contact messages are submissions from the public, not content. An editor
# reads and clears them but must not be able to forge or rewrite one.
INBOX_APP = "contact"
INBOX_ACTIONS = ("view", "delete")


def sync_editor_group(using: str = DEFAULT_DB_ALIAS) -> int:
    """
    Create or update the Editor group. Idempotent — safe to run on every deploy.

    Returns the number of permissions the group ends up holding.
    """
    from django.apps import apps
    from django.contrib.auth.management import create_permissions
    from django.contrib.auth.models import Group, Permission

    # `post_migrate` fires once per app config and the order is not guaranteed,
    # so a target app's permissions may not exist yet when this runs. Creating
    # them here is idempotent and makes the result independent of that order.
    for label in (*CONTENT_APPS, INBOX_APP):
        create_permissions(apps.get_app_config(label), using=using, verbosity=0)

    permissions = Permission.objects.using(using)

    wanted = list(permissions.filter(content_type__app_label__in=CONTENT_APPS))
    wanted += list(
        permissions.filter(
            content_type__app_label=INBOX_APP,
            codename__regex=r"^(" + "|".join(INBOX_ACTIONS) + r")_",
        )
    )

    group, _created = Group.objects.using(using).get_or_create(name=GROUP_NAME)
    group.permissions.set(wanted)
    return len(wanted)


def handle_post_migrate(sender, using=DEFAULT_DB_ALIAS, **kwargs):
    """Wired up in `CoreConfig.ready()`."""
    sync_editor_group(using=using)
