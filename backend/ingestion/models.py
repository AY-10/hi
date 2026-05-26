from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class SourceSystem(models.Model):
    SAP = 'sap'
    UTILITY = 'utility'
    TRAVEL = 'travel'

    SOURCE_TYPES = [
        (SAP, 'SAP'),
        (UTILITY, 'Utility portal'),
        (TRAVEL, 'Travel platform'),
    ]

    CSV_UPLOAD = 'csv_upload'
    JSON_UPLOAD = 'json_upload'
    API_PULL = 'api_pull'

    INGESTION_MODES = [
        (CSV_UPLOAD, 'CSV upload'),
        (JSON_UPLOAD, 'JSON upload'),
        (API_PULL, 'API pull'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    name = models.CharField(max_length=200)
    ingestion_mode = models.CharField(max_length=20, choices=INGESTION_MODES)
    description = models.TextField(blank=True)
    external_system_ref = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.name} ({self.get_source_type_display()})'


class IngestionBatch(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='batches')
    source = models.ForeignKey(
        SourceSystem, on_delete=models.CASCADE, related_name='batches')
    file_name = models.CharField(max_length=255, blank=True)
    raw_format = models.CharField(max_length=80)
    status = models.CharField(max_length=20, default='complete')
    record_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.source.name} batch {self.id}'


class ReviewRecord(models.Model):
    STAGED = 'staged'
    NEEDS_REVIEW = 'needs_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    LOCKED = 'locked'

    REVIEW_STATUSES = [
        (STAGED, 'Staged'),
        (NEEDS_REVIEW, 'Needs review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (LOCKED, 'Locked'),
    ]

    SCOPE1 = 'scope1'
    SCOPE2 = 'scope2'
    SCOPE3 = 'scope3'

    SCOPE_CHOICES = [
        (SCOPE1, 'Scope 1'),
        (SCOPE2, 'Scope 2'),
        (SCOPE3, 'Scope 3'),
    ]

    FUEL = 'fuel'
    PROCUREMENT = 'procurement'
    ELECTRICITY = 'electricity'
    FLIGHT = 'flight'
    HOTEL = 'hotel'
    GROUND_TRANSPORT = 'ground_transport'

    RECORD_KINDS = [
        (FUEL, 'Fuel'),
        (PROCUREMENT, 'Procurement'),
        (ELECTRICITY, 'Electricity'),
        (FLIGHT, 'Flight'),
        (HOTEL, 'Hotel'),
        (GROUND_TRANSPORT, 'Ground transport'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='records')
    source = models.ForeignKey(
        SourceSystem, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.CASCADE, related_name='records')
    source_record_id = models.CharField(max_length=120)
    source_row_number = models.PositiveIntegerField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    source_payload = models.JSONField(default=dict)
    record_kind = models.CharField(max_length=40, choices=RECORD_KINDS)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    activity_date = models.DateField()
    service_period_start = models.DateField(null=True, blank=True)
    service_period_end = models.DateField(null=True, blank=True)
    location_code = models.CharField(max_length=80, blank=True)
    counterparty = models.CharField(max_length=200, blank=True)
    activity_value = models.DecimalField(max_digits=14, decimal_places=3)
    activity_unit = models.CharField(max_length=20)
    normalized_value = models.DecimalField(max_digits=14, decimal_places=3)
    normalized_unit = models.CharField(max_length=20)
    emission_factor_name = models.CharField(max_length=200, blank=True)
    emission_factor_source = models.CharField(max_length=200, blank=True)
    emission_factor_value = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True)
    emissions_kg_co2e = models.DecimalField(
        max_digits=14, decimal_places=3, null=True, blank=True)
    confidence_score = models.PositiveSmallIntegerField(default=100)
    suspicion_flags = models.JSONField(default=list, blank=True)
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUSES, default=NEEDS_REVIEW)
    review_note = models.TextField(blank=True)
    approved_by = models.CharField(max_length=120, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-activity_date', '-id']
        constraints = [
            models.UniqueConstraint(fields=[
                                    'organization', 'source', 'source_record_id'], name='unique_source_record_per_org'),
        ]

    def __str__(self) -> str:
        return f'{self.record_kind} {self.source_record_id}'


class AuditEvent(models.Model):
    record = models.ForeignKey(
        ReviewRecord, on_delete=models.CASCADE, related_name='audit_events')
    action = models.CharField(max_length=40)
    actor = models.CharField(max_length=120, blank=True)
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return f'{self.action} on {self.record_id}'
