"""Validation for the one write endpoint the API exposes."""

from rest_framework import serializers

from core.models import LOCALES

from .models import Submission

MIN_MESSAGE_LENGTH = 10
MAX_MESSAGE_LENGTH = 5000


class SubmissionSerializer(serializers.ModelSerializer):
    """
    Validates a contact submission.

    `website` is a honeypot: it is not rendered to humans, so anything that
    fills it is a bot. The view drops those without persisting.
    """

    website = serializers.CharField(
        required=False, allow_blank=True, write_only=True, trim_whitespace=True
    )

    class Meta:
        model = Submission
        fields = ("name", "email", "message", "locale", "website")

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name is too short.")
        return value

    def validate_message(self, value: str) -> str:
        value = value.strip()
        if len(value) < MIN_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f"Message must be at least {MIN_MESSAGE_LENGTH} characters."
            )
        if len(value) > MAX_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f"Message must be at most {MAX_MESSAGE_LENGTH} characters."
            )
        return value

    def validate_locale(self, value: str) -> str:
        if value and value not in LOCALES:
            raise serializers.ValidationError(f"Unknown locale: {value}")
        return value
