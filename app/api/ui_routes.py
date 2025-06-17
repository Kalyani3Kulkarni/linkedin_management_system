"""
UI routes for serving dashboard templates.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.models.database import get_db

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Create router
ui_router = APIRouter(tags=["ui"])


@ui_router.get("/", response_class=HTMLResponse)
async def dashboard_redirect():
    """Redirect root to dashboard."""
    return """
    <html>
        <head>
            <meta http-equiv="refresh" content="0; url=/dashboard">
        </head>
        <body>
            <p>Redirecting to dashboard...</p>
        </body>
    </html>
    """


@ui_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page_title": "Dashboard"
    })


@ui_router.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request, db: Session = Depends(get_db)):
    """Trends analysis page."""
    return templates.TemplateResponse("trends.html", {
        "request": request,
        "page_title": "Trends Analysis"
    })


@ui_router.get("/content", response_class=HTMLResponse)
async def content_page(request: Request, db: Session = Depends(get_db)):
    """Content management page."""
    return templates.TemplateResponse("content.html", {
        "request": request,
        "page_title": "Content Management"
    })


@ui_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings and configuration page."""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page_title": "Settings"
    })