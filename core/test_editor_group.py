"""
Tests for the "Editor" group reconciled by `core.groups.sync_editor_group`.

The point of the group is that an editor can run the website's content without
holding a superuser account. These tests pin both halves of that: what an
editor can reach, and — more importantly — what they cannot.
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from core.groups import GROUP_NAME, sync_editor_group


class EditorGroupExistsTests(TestCase):
    def test_post_migrate_created_the_group(self):
        self.assertTrue(Group.objects.filter(name=GROUP_NAME).exists())

    def test_group_is_not_empty(self):
        """A silent failure mode: permissions not created when the sync ran."""
        group = Group.objects.get(name=GROUP_NAME)
        self.assertGreater(group.permissions.count(), 0)

    def test_can_manage_articles(self):
        group = Group.objects.get(name=GROUP_NAME)
        codenames = set(
            group.permissions.filter(content_type__app_label="news").values_list(
                "codename", flat=True
            )
        )
        self.assertEqual(
            codenames,
            {"add_article", "change_article", "delete_article", "view_article"},
        )

    def test_cannot_manage_users_or_groups(self):
        """The escalation path: an editor who can edit users can make themselves root."""
        group = Group.objects.get(name=GROUP_NAME)
        self.assertFalse(group.permissions.filter(content_type__app_label="auth").exists())

    def test_cannot_forge_contact_messages(self):
        """Inbox submissions are evidence of what the public sent, not content."""
        group = Group.objects.get(name=GROUP_NAME)
        codenames = set(
            group.permissions.filter(content_type__app_label="contact").values_list(
                "codename", flat=True
            )
        )
        self.assertEqual(codenames, {"view_submission", "delete_submission"})


class EditorGroupConvergenceTests(TestCase):
    """
    The reason this lives in a `post_migrate` receiver and not a data migration.

    A data migration runs once, so a database upgraded in place keeps whatever
    permission set existed the day it ran, while a fresh database picks up every
    model added since — and the two drift apart permanently. Re-running the sync
    must always land on the same set, and must repair a group somebody edited.
    """

    def test_running_twice_is_idempotent(self):
        first = sync_editor_group()
        second = sync_editor_group()
        self.assertEqual(first, second)
        self.assertEqual(Group.objects.filter(name=GROUP_NAME).count(), 1)

    def test_repairs_a_group_that_lost_permissions(self):
        group = Group.objects.get(name=GROUP_NAME)
        expected = group.permissions.count()

        group.permissions.clear()
        self.assertEqual(group.permissions.count(), 0)

        sync_editor_group()
        self.assertEqual(Group.objects.get(name=GROUP_NAME).permissions.count(), expected)

    def test_revokes_permissions_that_should_not_be_there(self):
        """An escalation an admin could grant by hand must not survive a sync."""
        group = Group.objects.get(name=GROUP_NAME)
        group.permissions.add(Permission.objects.get(codename="add_user"))
        self.assertTrue(group.permissions.filter(codename="add_user").exists())

        sync_editor_group()
        self.assertFalse(
            Group.objects.get(name=GROUP_NAME).permissions.filter(codename="add_user").exists()
        )


class EditorAdminAccessTests(TestCase):
    """An editor account is `is_staff` plus the group — never `is_superuser`."""

    def setUp(self):
        self.editor = User.objects.create_user(
            username="editor", password="editor-pw-for-tests", is_staff=True
        )
        self.editor.groups.add(Group.objects.get(name=GROUP_NAME))
        self.client.force_login(self.editor)

    def test_can_open_the_article_changelist(self):
        response = self.client.get(reverse("admin:news_article_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_can_open_the_add_article_form(self):
        response = self.client.get(reverse("admin:news_article_add"))
        self.assertEqual(response.status_code, 200)

    def test_cannot_open_the_user_changelist(self):
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertIn(response.status_code, (302, 403))

    def test_cannot_open_the_add_user_form(self):
        response = self.client.get(reverse("admin:auth_user_add"))
        self.assertIn(response.status_code, (302, 403))
