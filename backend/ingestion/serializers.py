from rest_framework import serializers

from .models import AuditEvent, IngestionBatch, Organization, ReviewRecord, SourceSystem


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'created_at']


class SourceSystemSerializer(serializers.ModelSerializer):
    source_type_label = serializers.CharField(
        source='get_source_type_display', read_only=True)
    ingestion_mode_label = serializers.CharField(
        source='get_ingestion_mode_display', read_only=True)

    class Meta:
        model = SourceSystem
        fields = [
            'id',
            'organization',
            'source_type',
            'source_type_label',
            'name',
            'ingestion_mode',
            'ingestion_mode_label',
            'description',
            'external_system_ref',
            'active',
            'created_at',
        ]


class IngestionBatchSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            'id',
            'organization',
            'source',
            'source_name',
            'file_name',
            'raw_format',
            'status',
            'record_count',
            'notes',
            'received_at',
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'record', 'action', 'actor',
                  'before_snapshot', 'after_snapshot', 'note', 'created_at']


class ReviewRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(
        source='source.source_type', read_only=True)
    batch_file_name = serializers.CharField(
        source='batch.file_name', read_only=True)
    batch_received_at = serializers.DateTimeField(
        source='batch.received_at', read_only=True)
    source_type_label = serializers.CharField(
        source='source.get_source_type_display', read_only=True)
    record_kind_label = serializers.CharField(
        source='get_record_kind_display', read_only=True)
    scope_label = serializers.CharField(
        source='get_scope_display', read_only=True)
    review_status_label = serializers.CharField(
        source='get_review_status_display', read_only=True)
    audit_events = AuditEventSerializer(many=True, read_only=True)

    class Meta:
        model = ReviewRecord
        fields = [
            'id',
            'organization',
            'source',
            'source_name',
            'source_type',
            'source_type_label',
            'batch',
            'batch_file_name',
            'batch_received_at',
            'source_record_id',
            'source_row_number',
            'source_updated_at',
            'source_payload',
            'record_kind',
            'record_kind_label',
            'scope',
            'scope_label',
            'activity_date',
            'service_period_start',
            'service_period_end',
            'location_code',
            'counterparty',
            'activity_value',
            'activity_unit',
            'normalized_value',
            'normalized_unit',
            'emission_factor_name',
            'emission_factor_source',
            'emission_factor_value',
            'emissions_kg_co2e',
            'confidence_score',
            'suspicion_flags',
            'review_status',
            'review_status_label',
            'review_note',
            'approved_by',
            'approved_at',
            'locked_at',
            'edited_at',
            'version',
            'audit_events',
        ]


class DashboardSummarySerializer(serializers.Serializer):
    total_rows = serializers.IntegerField()
    needs_review = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    suspicious = serializers.IntegerField()
    locked = serializers.IntegerField()


class DashboardPayloadSerializer(serializers.Serializer):
    organization = OrganizationSerializer()
    summary = DashboardSummarySerializer()
    sources = SourceSystemSerializer(many=True)
    recent_batches = IngestionBatchSerializer(many=True)
    rows = ReviewRecordSerializer(many=True)
