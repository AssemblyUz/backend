"""Validation for the one write endpoint the API exposes."""

import re

from rest_framework import serializers

from core.models import LOCALES

from .models import Submission

MIN_MESSAGE_LENGTH = 10
MAX_MESSAGE_LENGTH = 5000

MIN_PHONE_DIGITS = 7
MAX_PHONE_DIGITS = 15  # E.164's ceiling.

# Deliberately permissive: digits, and the punctuation people write numbers
# with. Uzbek numbers arrive as +998 90 123 45 67, (90) 123-45-67 and every
# spacing in between, and a stricter pattern rejects real numbers.
PHONE_ALLOWED = re.compile(r"^[0-9+()\-.\s]+$")


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
        fields = ("name", "email", "phone", "message", "locale", "website")
        extra_kwargs = {
            # Either will do; `validate` below insists on one of them.
            "email": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
        }

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

    def validate_phone(self, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        if not PHONE_ALLOWED.match(value):
            raise serializers.ValidationError("Phone number contains invalid characters.")
        digits = sum(character.isdigit() for character in value)
        if not MIN_PHONE_DIGITS <= digits <= MAX_PHONE_DIGITS:
            raise serializers.ValidationError(
                f"Phone number must have between {MIN_PHONE_DIGITS} and "
                f"{MAX_PHONE_DIGITS} digits."
            )
        return value

    def validate_locale(self, value: str) -> str:
        if value and value not in LOCALES:
            raise serializers.ValidationError(f"Unknown locale: {value}")
        return value

    def validate(self, attrs):
        """
        One way to reply is required — either will do.

        A message with neither is a message nobody can answer, and the form
        asks for both as optional, so this is the only place the requirement
        can be stated. Raised against both fields so either input can show it.
        """
        if not attrs.get("email", "") and not attrs.get("phone", ""):
            message = "Leave an email address or a phone number so we can reply."
            raise serializers.ValidationError({"email": [message], "phone": [message]})
        return attrs
