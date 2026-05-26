from __future__ import annotations
from django.shortcuts import render

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AuditEvent, Organization, ReviewRecord, SourceSystem
from .serializers import DashboardPayloadSerializer, ReviewRecordSerializer, SourceSystemSerializer
from .services import record_snapshot, seed_demo_data


def dashboard_payload(organization: Organization) -> dict:
    rows = ReviewRecord.objects.select_related('source', 'batch', 'organization').prefetch_related(
        'audit_events').filter(organization=organization)
    summary = {
        'total_rows': rows.count(),
        'needs_review': rows.filter(review_status=ReviewRecord.NEEDS_REVIEW).count(),
        'approved': rows.filter(review_status=ReviewRecord.APPROVED).count(),
        'rejected': rows.filter(review_status=ReviewRecord.REJECTED).count(),
        'suspicious': rows.exclude(suspicion_flags=[]).count(),
        'locked': rows.filter(review_status=ReviewRecord.LOCKED).count(),
    }
    recent_batches = organization.batches.select_related(
        'source').order_by('-received_at')[:5]
    return {
        'organization': organization,
        'summary': summary,
        'sources': organization.sources.order_by('source_type', 'name'),
        'recent_batches': recent_batches,
        'rows': rows[:12],
    }


@api_view(['GET'])
def dashboard_view(_request):
    organization = seed_demo_data()
    payload = dashboard_payload(organization)
    serializer = DashboardPayloadSerializer(payload)
    return Response(serializer.data)


@api_view(['GET'])
def records_view(_request):
    organization = seed_demo_data()
    rows = ReviewRecord.objects.select_related('source', 'batch', 'organization').prefetch_related(
        'audit_events').filter(organization=organization)
    return Response(ReviewRecordSerializer(rows, many=True).data)


@api_view(['GET'])
def sources_view(_request):
    organization = seed_demo_data()
    sources = SourceSystem.objects.filter(
        organization=organization).order_by('source_type', 'name')
    return Response(SourceSystemSerializer(sources, many=True).data)


@api_view(['POST'])
def seed_demo_view(_request):
    organization = seed_demo_data()
    return Response(DashboardPayloadSerializer(dashboard_payload(organization)).data)


@api_view(['PATCH'])
def record_detail_view(_request, record_id: int):
    record = get_object_or_404(ReviewRecord.objects.select_related(
        'source', 'batch', 'organization').prefetch_related('audit_events'), pk=record_id)
    payload = _request.data
    before = record_snapshot(record)

    for field in ['activity_value', 'activity_unit', 'normalized_value', 'normalized_unit', 'review_note', 'confidence_score']:
        if field in payload:
            setattr(record, field, payload[field])

    if 'suspicion_flags' in payload:
        record.suspicion_flags = payload['suspicion_flags']
    if 'review_status' in payload:
        record.review_status = payload['review_status']
    if 'approved_by' in payload:
        record.approved_by = payload['approved_by']
    if 'approved_at' in payload:
        record.approved_at = payload['approved_at'] or None

    record.version += 1
    record.edited_at = timezone.now()
    record.save()

    AuditEvent.objects.create(
        record=record,
        action='edited',
        actor=payload.get('actor', 'analyst'),
        before_snapshot=before,
        after_snapshot=record_snapshot(record),
        note=payload.get('note', 'Edited from review dashboard.'),
    )

    return Response(ReviewRecordSerializer(record).data)


def _apply_status(record: ReviewRecord, status: str, actor: str, note: str) -> ReviewRecord:
    before = record_snapshot(record)
    record.review_status = status
    if status == ReviewRecord.APPROVED:
        record.approved_by = actor
        record.approved_at = timezone.now()
        record.locked_at = timezone.now()
    elif status == ReviewRecord.REJECTED:
        record.locked_at = timezone.now()
    elif status == ReviewRecord.LOCKED:
        record.locked_at = timezone.now()
    record.version += 1
    record.save()
    AuditEvent.objects.create(
        record=record,
        action=status,
        actor=actor,
        before_snapshot=before,
        after_snapshot=record_snapshot(record),
        note=note,
    )
    return record


@api_view(['POST'])
def approve_view(_request, record_id: int):
    record = get_object_or_404(ReviewRecord, pk=record_id)
    actor = _request.data.get('actor', 'analyst')
    note = _request.data.get('note', 'Approved from analyst review queue.')
    return Response(ReviewRecordSerializer(_apply_status(record, ReviewRecord.APPROVED, actor, note)).data)


@api_view(['POST'])
def reject_view(_request, record_id: int):
    record = get_object_or_404(ReviewRecord, pk=record_id)
    actor = _request.data.get('actor', 'analyst')
    note = _request.data.get('note', 'Rejected from analyst review queue.')
    return Response(ReviewRecordSerializer(_apply_status(record, ReviewRecord.REJECTED, actor, note)).data)


@api_view(['POST'])
def flag_view(_request, record_id: int):
    record = get_object_or_404(ReviewRecord, pk=record_id)
    flag = _request.data.get('flag', 'manual_review')
    if flag not in record.suspicion_flags:
        record.suspicion_flags.append(flag)
    record.review_status = ReviewRecord.NEEDS_REVIEW
    record.version += 1
    record.save()
    AuditEvent.objects.create(
        record=record,
        action='flagged',
        actor=_request.data.get('actor', 'analyst'),
        before_snapshot={},
        after_snapshot=record_snapshot(record),
        note=_request.data.get('note', f'Flagged with {flag}.'),
    )
    return Response(ReviewRecordSerializer(record).data)


# Create your views here.
