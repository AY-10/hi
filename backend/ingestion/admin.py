from django.contrib import admin

from .models import AuditEvent, IngestionBatch, Organization, ReviewRecord, SourceSystem


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')


@admin.register(SourceSystem)
class SourceSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'source_type',
                    'ingestion_mode', 'active')
    list_filter = ('source_type', 'ingestion_mode', 'active')
    search_fields = ('name', 'external_system_ref')


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'source', 'status',
                    'record_count', 'received_at')
    list_filter = ('status', 'source__source_type')


@admin.register(ReviewRecord)
class ReviewRecordAdmin(admin.ModelAdmin):
    list_display = ('source_record_id', 'record_kind', 'scope',
                    'review_status', 'activity_date', 'confidence_score')
    list_filter = ('review_status', 'record_kind',
                   'scope', 'source__source_type')
    search_fields = ('source_record_id', 'location_code', 'counterparty')


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('record', 'action', 'actor', 'created_at')
    search_fields = ('action', 'actor', 'note')


# Register your models here.
