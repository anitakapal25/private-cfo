"""Regression coverage for timezone and Pydantic API modernization."""

from datetime import datetime, timezone

from app.core.time import legacy_utc_isoformat, utc_now
from app.models.advisor import AdvisorConsent
from app.models.community import CommunityBenchmark
from app.models.export import TaxExportTemplate
from app.models.webhook import WebhookDelivery, WebhookSubscription
from app.models.wellness_program import EmployerWellnessProgram, UserWellnessParticipation
from app.routers.community import CommunityBenchmarkBase
from app.routers.export import TaxExportTemplateBase
from app.routers.wellness_program import (
    EmployerWellnessProgramBase,
    UserWellnessParticipationBase,
)


def test_utc_helpers_preserve_database_and_legacy_wire_formats():
    persisted = utc_now()
    legacy = legacy_utc_isoformat()

    assert persisted.tzinfo is timezone.utc
    assert persisted.utcoffset().total_seconds() == 0
    assert "+" not in legacy and not legacy.endswith("Z")
    assert datetime.fromisoformat(legacy + "+00:00").tzinfo is timezone.utc


def test_timestamp_column_defaults_return_timezone_aware_utc():
    columns = (
        AdvisorConsent.granted_at,
        CommunityBenchmark.calculated_at,
        TaxExportTemplate.created_at,
        WebhookSubscription.created_at,
        WebhookDelivery.attempted_at,
        EmployerWellnessProgram.created_at,
        UserWellnessParticipation.enrollment_date,
    )

    for column in columns:
        value = column.property.columns[0].default.arg({})
        assert value.tzinfo is timezone.utc
        assert value.utcoffset().total_seconds() == 0


def test_model_dump_exclude_unset_preserves_omitted_and_explicit_null_fields():
    cases = (
        (
            CommunityBenchmarkBase,
            {
                "age_group": "25-34",
                "income_bracket": "5-10L",
                "metric_type": "savings_rate",
                "metric_value": 0.2,
                "sample_size": 10,
            },
            "region",
        ),
        (
            TaxExportTemplateBase,
            {"template_name": "Synthetic", "assessment_year": "2026-27"},
            "description",
        ),
        (
            EmployerWellnessProgramBase,
            {"employer_name": "Synthetic", "program_name": "Test"},
            "description",
        ),
        (
            UserWellnessParticipationBase,
            {"program_id": "00000000-0000-0000-0000-000000000001"},
            "progress_percentage",
        ),
    )

    for model, values, optional_field in cases:
        omitted = model(**values).model_dump(exclude_unset=True)
        explicit_null = model(**values, **{optional_field: None}).model_dump(
            exclude_unset=True
        )
        assert optional_field not in omitted
        assert explicit_null[optional_field] is None
