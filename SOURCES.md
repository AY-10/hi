# SOURCES

## SAP

I treated SAP as an IDoc / flat-file style export with mixed German and English column names, plant codes, booking dates, quantity fields, and a separate record kind for fuel versus procurement.

What I learned: SAP exports are usually not analysis-ready. They are transactional, verbose, and full of internal codes that need lookup context.

Sample data shape: `bukrs`, `werks`, `plant_code`, `transaction_text`, `quantity`, `uom`, `amount_local`, `currency_code`, and `document_date`.

What would break in real deployment: inconsistent units, custom column mappings per client, and plant/material codes that need a customer-specific reference table.

## Utility

I modeled electricity as a portal CSV / interval-data export with meter id, account number, billing start/end, kWh consumption, tariff, and demand.

What I learned: utility billing periods often do not align with calendar months, and review logic needs to understand the period rather than just the invoice date.

Sample data shape: `account_number`, `meter_id`, `billing_start`, `billing_end`, `consumption_kwh`, `demand_kw`, `tariff`, `provider`.

What would break in real deployment: PDF-only invoices, estimated reads, tariff line items, and utilities that split a bill across multiple meters or locations.

## Travel

I modeled travel after a Concur-style trip feed: trip id, category, origin and destination airport codes, cabin class, hotel nights, and ground transport distance.

What I learned: travel APIs rarely give a perfect emissions-ready number. Flights may only provide airport codes, and hotel/ground transport needs category-specific factors.

Sample data shape: `trip_id`, `category`, `origin_airport`, `destination_airport`, `distance_km`, `cabin_class`, `hotel_name`, `nights`, `vendor`.

What would break in real deployment: missing destination airports, canceled trips, rail or multi-leg itineraries, and vendor-specific fields that do not map cleanly to one record shape.
