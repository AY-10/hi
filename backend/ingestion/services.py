from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, IngestionBatch, Organization, ReviewRecord, SourceSystem


def record_snapshot(record: ReviewRecord) -> dict:
    return {
        'id': record.id,
        'organization_id': record.organization_id,
        'source_id': record.source_id,
        'batch_id': record.batch_id,
        'source_record_id': record.source_record_id,
        'review_status': record.review_status,
        'activity_value': str(record.activity_value),
        'activity_unit': record.activity_unit,
        'normalized_value': str(record.normalized_value),
        'normalized_unit': record.normalized_unit,
        'emissions_kg_co2e': str(record.emissions_kg_co2e) if record.emissions_kg_co2e is not None else None,
        'confidence_score': record.confidence_score,
        'suspicion_flags': list(record.suspicion_flags),
        'review_note': record.review_note,
        'approved_by': record.approved_by,
        'approved_at': record.approved_at.isoformat() if record.approved_at else None,
        'locked_at': record.locked_at.isoformat() if record.locked_at else None,
        'version': record.version,
    }


def suspicion_flags_for(record_kind: str, activity_value: Decimal, raw_payload: dict) -> list[str]:
    flags: list[str] = []
    if activity_value <= 0:
        flags.append('non_positive_value')
    if record_kind == ReviewRecord.FLIGHT and not raw_payload.get('destination_airport'):
        flags.append('missing_destination_airport')
    if record_kind == ReviewRecord.ELECTRICITY and raw_payload.get('consumption_kwh', 0) and Decimal(str(raw_payload.get('consumption_kwh', 0))) > Decimal('100000'):
        flags.append('high_site_consumption')
    if record_kind == ReviewRecord.PROCUREMENT and raw_payload.get('amount_local', 0) and Decimal(str(raw_payload.get('amount_local', 0))) > Decimal('50000'):
        flags.append('large_procurement_spend')
    if raw_payload.get('estimated'):
        flags.append('estimated_value')
    return flags


def normalize_row_payload(source_type: str, raw_payload: dict) -> dict:
    if source_type == SourceSystem.SAP:
        record_kind = raw_payload.get('record_kind', ReviewRecord.FUEL)
        if record_kind == ReviewRecord.PROCUREMENT:
            activity_unit = raw_payload.get('currency_code', 'USD')
            activity_value = Decimal(str(raw_payload.get('amount_local', 0)))
            normalized_unit = activity_unit
            normalized_value = activity_value
            emissions = activity_value * Decimal('0.0012')
            factor_name = 'Spend-based procurement factor'
        else:
            activity_unit = raw_payload.get('uom', 'L')
            activity_value = Decimal(str(raw_payload.get('quantity', 0)))
            normalized_unit = 'L'
            normalized_value = activity_value
            emissions = activity_value * Decimal('2.68')
            factor_name = 'Fuel combustion factor'
        scope = ReviewRecord.SCOPE1 if record_kind == ReviewRecord.FUEL else ReviewRecord.SCOPE3
    elif source_type == SourceSystem.UTILITY:
        record_kind = ReviewRecord.ELECTRICITY
        activity_value = Decimal(str(raw_payload.get('consumption_kwh', 0)))
        activity_unit = 'kWh'
        normalized_unit = 'kWh'
        normalized_value = activity_value
        emissions = activity_value * Decimal('0.692')
        factor_name = 'Grid electricity factor'
        scope = ReviewRecord.SCOPE2
    else:
        category = raw_payload.get('category', 'flight')
        if category == 'hotel':
            record_kind = ReviewRecord.HOTEL
            activity_value = Decimal(str(raw_payload.get('nights', 0)))
            activity_unit = 'night'
            normalized_unit = 'night'
            emissions = Decimal(
                str(raw_payload.get('nights', 0))) * Decimal('14.5')
        elif category == 'ground_transport':
            record_kind = ReviewRecord.GROUND_TRANSPORT
            activity_value = Decimal(str(raw_payload.get('distance_km', 0)))
            activity_unit = 'km'
            normalized_unit = 'km'
            emissions = Decimal(
                str(raw_payload.get('distance_km', 0))) * Decimal('0.09')
        else:
            record_kind = ReviewRecord.FLIGHT
            activity_value = Decimal(str(raw_payload.get('distance_km', 0)))
            activity_unit = 'km'
            normalized_unit = 'km'
            emissions = Decimal(
                str(raw_payload.get('distance_km', 0))) * Decimal('0.115')
        normalized_value = activity_value
        factor_name = 'Travel emissions factor'
        scope = ReviewRecord.SCOPE3

    return {
        'record_kind': record_kind,
        'scope': scope,
        'activity_value': activity_value,
        'activity_unit': activity_unit,
        'normalized_value': normalized_value,
        'normalized_unit': normalized_unit,
        'emissions_kg_co2e': emissions,
        'emission_factor_name': factor_name,
        'emission_factor_source': raw_payload.get('factor_source', 'Prototype factor table'),
        'emission_factor_value': raw_payload.get('factor_value'),
    }


def create_demo_record(*, organization: Organization, source: SourceSystem, batch: IngestionBatch, source_record_id: str, source_row_number: int, raw_payload: dict, activity_date: date, source_updated_at: datetime | None = None, location_code: str = '', counterparty: str = '', review_note: str = '') -> ReviewRecord:
    normalized = normalize_row_payload(source.source_type, raw_payload)
    flags = suspicion_flags_for(
        normalized['record_kind'], normalized['activity_value'], raw_payload)
    confidence = 95 if not flags else max(60, 95 - 10 * len(flags))

    record = ReviewRecord.objects.create(
        organization=organization,
        source=source,
        batch=batch,
        source_record_id=source_record_id,
        source_row_number=source_row_number,
        source_updated_at=source_updated_at,
        source_payload=raw_payload,
        record_kind=normalized['record_kind'],
        scope=normalized['scope'],
        activity_date=activity_date,
        service_period_start=raw_payload.get('period_start') or activity_date,
        service_period_end=raw_payload.get('period_end') or activity_date,
        location_code=location_code or raw_payload.get('plant_code', '') or raw_payload.get(
            'meter_id', '') or raw_payload.get('origin_airport', ''),
        counterparty=counterparty or raw_payload.get('vendor', '') or raw_payload.get(
            'provider', '') or raw_payload.get('airline', ''),
        activity_value=normalized['activity_value'],
        activity_unit=normalized['activity_unit'],
        normalized_value=normalized['normalized_value'],
        normalized_unit=normalized['normalized_unit'],
        emission_factor_name=normalized['emission_factor_name'],
        emission_factor_source=normalized['emission_factor_source'],
        emission_factor_value=normalized['emission_factor_value'],
        emissions_kg_co2e=normalized['emissions_kg_co2e'],
        confidence_score=confidence,
        suspicion_flags=flags,
        review_status=ReviewRecord.NEEDS_REVIEW,
        review_note=review_note,
    )
    AuditEvent.objects.create(
        record=record,
        action='imported',
        actor='system',
        after_snapshot=record_snapshot(record),
        note='Imported from prototype ingestion feed.',
    )
    return record


@transaction.atomic
def seed_demo_data() -> Organization:
    organization, _ = Organization.objects.get_or_create(
        slug='northwind-industries', defaults={'name': 'Northwind Industries'})

    sap_source, _ = SourceSystem.objects.get_or_create(
        organization=organization,
        source_type=SourceSystem.SAP,
        name='SAP ECC export',
        defaults={
            'ingestion_mode': SourceSystem.CSV_UPLOAD,
            'description': 'Flat-file extract from SAP logistics and finance tables.',
            'external_system_ref': 'sap_ecc_fuel_procurement_001',
        },
    )
    utility_source, _ = SourceSystem.objects.get_or_create(
        organization=organization,
        source_type=SourceSystem.UTILITY,
        name='Utility portal export',
        defaults={
            'ingestion_mode': SourceSystem.CSV_UPLOAD,
            'description': 'Facilities team portal CSV for monthly electricity invoices.',
            'external_system_ref': 'utility_portal_electricity_001',
        },
    )
    travel_source, _ = SourceSystem.objects.get_or_create(
        organization=organization,
        source_type=SourceSystem.TRAVEL,
        name='Concur trips feed',
        defaults={
            'ingestion_mode': SourceSystem.API_PULL,
            'description': 'Travel expense API feed for flights, hotels, and ground transport.',
            'external_system_ref': 'concur_travel_api_001',
        },
    )

    if ReviewRecord.objects.filter(organization=organization).exists():
        return organization

    sap_batch = IngestionBatch.objects.create(
        organization=organization,
        source=sap_source,
        file_name='sap_fuel_procurement_export_2026_04.csv',
        raw_format='sap_flat_file',
        notes='Mixed German and English column labels from a finance extract.',
        record_count=3,
    )
    utility_batch = IngestionBatch.objects.create(
        organization=organization,
        source=utility_source,
        file_name='utility_portal_april_2026.csv',
        raw_format='utility_csv',
        notes='Billing periods do not align to calendar months.',
        record_count=3,
    )
    travel_batch = IngestionBatch.objects.create(
        organization=organization,
        source=travel_source,
        file_name='concur_travel_april_2026.json',
        raw_format='travel_api_json',
        notes='Trip feed includes airport codes and missing distances on some rows.',
        record_count=4,
    )

    create_demo_record(
        organization=organization,
        source=sap_source,
        batch=sap_batch,
        source_record_id='sap-0001',
        source_row_number=1,
        raw_payload={
            'record_kind': ReviewRecord.FUEL,
            'bukrs': '1000',
            'werks': 'DE-BER-01',
            'transaction_text': 'Diesel for generator testing',
            'quantity': '1840.0',
            'uom': 'L',
            'plant_code': 'BER-FAC-01',
            'vendor': 'TotalEnergies',
            'document_date': '2026-04-12',
            'factor_source': 'Prototype emission factor table',
            'factor_value': '2.68',
        },
        activity_date=date(2026, 4, 12),
        source_updated_at=timezone.now(),
        location_code='BER-FAC-01',
        counterparty='TotalEnergies',
    )
    create_demo_record(
        organization=organization,
        source=sap_source,
        batch=sap_batch,
        source_record_id='sap-0002',
        source_row_number=2,
        raw_payload={
            'record_kind': ReviewRecord.PROCUREMENT,
            'bukrs': '1000',
            'werks': 'IN-HYD-02',
            'transaction_text': 'Office consumables purchase',
            'amount_local': '41250.00',
            'currency_code': 'USD',
            'vendor': 'OfficeMart',
            'document_date': '2026-04-18',
            'factor_source': 'Spend-based procurement factor',
        },
        activity_date=date(2026, 4, 18),
        source_updated_at=timezone.now(),
        location_code='IN-HYD-02',
        counterparty='OfficeMart',
    )
    create_demo_record(
        organization=organization,
        source=sap_source,
        batch=sap_batch,
        source_record_id='sap-0003',
        source_row_number=3,
        raw_payload={
            'record_kind': ReviewRecord.FUEL,
            'bukrs': '1000',
            'werks': 'DE-HAM-03',
            'transaction_text': 'LPG top-up for warehouse heater',
            'quantity': '0',
            'uom': 'L',
            'plant_code': 'HAM-WHS-03',
            'vendor': 'Shell',
            'document_date': '2026-04-21',
            'estimated': True,
        },
        activity_date=date(2026, 4, 21),
        source_updated_at=timezone.now(),
        location_code='HAM-WHS-03',
        counterparty='Shell',
        review_note='Zero quantity and estimated flag should be reviewed before audit.',
    )

    create_demo_record(
        organization=organization,
        source=utility_source,
        batch=utility_batch,
        source_record_id='util-0001',
        source_row_number=1,
        raw_payload={
            'account_number': 'ACC-77421',
            'meter_id': 'MTR-9912',
            'billing_start': '2026-03-15',
            'billing_end': '2026-04-14',
            'consumption_kwh': '18340',
            'demand_kw': '312',
            'tariff': 'C&I TOU',
            'provider': 'State Grid',
        },
        activity_date=date(2026, 4, 14),
        source_updated_at=timezone.now(),
        location_code='MTR-9912',
        counterparty='State Grid',
    )
    create_demo_record(
        organization=organization,
        source=utility_source,
        batch=utility_batch,
        source_record_id='util-0002',
        source_row_number=2,
        raw_payload={
            'account_number': 'ACC-77421',
            'meter_id': 'MTR-9912',
            'billing_start': '2026-04-15',
            'billing_end': '2026-05-14',
            'consumption_kwh': '107450',
            'demand_kw': '521',
            'tariff': 'C&I TOU',
            'provider': 'State Grid',
        },
        activity_date=date(2026, 5, 14),
        source_updated_at=timezone.now(),
        location_code='MTR-9912',
        counterparty='State Grid',
        review_note='High usage spike is plausible for a full month but still worth analyst review.',
    )
    create_demo_record(
        organization=organization,
        source=utility_source,
        batch=utility_batch,
        source_record_id='util-0003',
        source_row_number=3,
        raw_payload={
            'account_number': 'ACC-11378',
            'meter_id': 'MTR-7721',
            'billing_start': '2026-03-20',
            'billing_end': '2026-04-22',
            'consumption_kwh': '0',
            'estimated': True,
            'provider': 'Metro Power',
        },
        activity_date=date(2026, 4, 22),
        source_updated_at=timezone.now(),
        location_code='MTR-7721',
        counterparty='Metro Power',
        review_note='Estimated zero-consumption bill is intentionally suspicious for the reviewer flow.',
    )

    create_demo_record(
        organization=organization,
        source=travel_source,
        batch=travel_batch,
        source_record_id='trav-0001',
        source_row_number=1,
        raw_payload={
            'trip_id': 'TRIP-8891',
            'category': 'flight',
            'origin_airport': 'BLR',
            'destination_airport': 'SFO',
            'distance_km': '13546',
            'airline': 'United',
            'cabin_class': 'business',
            'ticket_number': '016-9981122334',
        },
        activity_date=date(2026, 4, 9),
        source_updated_at=timezone.now(),
        location_code='BLR-SFO',
        counterparty='United',
    )
    create_demo_record(
        organization=organization,
        source=travel_source,
        batch=travel_batch,
        source_record_id='trav-0002',
        source_row_number=2,
        raw_payload={
            'trip_id': 'TRIP-8892',
            'category': 'hotel',
            'hotel_name': 'Aloft San Francisco Airport',
            'nights': '3',
            'city': 'San Francisco',
            'country': 'US',
        },
        activity_date=date(2026, 4, 12),
        source_updated_at=timezone.now(),
        location_code='SFO',
        counterparty='Aloft San Francisco Airport',
    )
    create_demo_record(
        organization=organization,
        source=travel_source,
        batch=travel_batch,
        source_record_id='trav-0003',
        source_row_number=3,
        raw_payload={
            'trip_id': 'TRIP-8893',
            'category': 'ground_transport',
            'distance_km': '28',
            'vendor': 'Uber',
            'city': 'Bangalore',
        },
        activity_date=date(2026, 4, 13),
        source_updated_at=timezone.now(),
        location_code='BLR',
        counterparty='Uber',
    )
    create_demo_record(
        organization=organization,
        source=travel_source,
        batch=travel_batch,
        source_record_id='trav-0004',
        source_row_number=4,
        raw_payload={
            'trip_id': 'TRIP-8894',
            'category': 'flight',
            'origin_airport': 'BLR',
            'distance_km': '0',
            'airline': 'IndiGo',
            'cabin_class': 'economy',
            'estimated': True,
        },
        activity_date=date(2026, 4, 20),
        source_updated_at=timezone.now(),
        location_code='BLR',
        counterparty='IndiGo',
        review_note='Missing destination airport is the kind of sparse travel row we want to catch.',
    )

    return organization
