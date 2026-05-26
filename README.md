# Breathe ESG Prototype

A full-stack ESG review and audit platform built with Django REST Framework and React for the Breathe ESG Tech Internship assignment.

## Live Demo

🔗 https://hi-1ibh.onrender.com/

## Features

- ESG data ingestion pipeline
- Analyst review queue
- Edit & approval workflows
- Audit trail inspection
- Seeded demo datasets
- RESTful backend APIs
- React dashboard frontend

## Tech Stack

### Backend
- Django
- Django REST Framework
- SQLite

### Frontend
- React.js
- TypeScript
- Vite

## Local Setup

### Backend

```bash
Push-Location backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
Pop-Location
