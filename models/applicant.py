"""Applicant data structures with conservative validation."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApplicantWebfile(BaseModel):
    """Information that may be extracted from an Online Visa Application PDF."""

    model_config = ConfigDict(extra="allow")

    full_name: Optional[str] = Field(default=None, description="Applicant full name")
    passport_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    nationality: Optional[str] = None
    gender: Optional[str] = None
    webfile_number: Optional[str] = None
    visa_application_reference: Optional[str] = None


class IVACAccountProfile(BaseModel):
    """Portal sign-up/profile information; enter and confirm these manually."""

    model_config = ConfigDict(extra="allow")

    mobile_number: Optional[str] = None
    email: Optional[str] = None
    given_name: Optional[str] = None
    surname: Optional[str] = None
    passport_number: Optional[str] = None
    nid_or_citizenship_number: Optional[str] = None
    date_of_birth: Optional[date] = None


class ManualConfirmations(BaseModel):
    """Applicant attestations that cannot be inferred by PDF parsing."""

    webfiles_unmodified: Optional[bool] = None
    applicant_details_consistent: Optional[bool] = None
    centre_selection_reviewed: Optional[bool] = None
    appointment_date_reviewed: Optional[bool] = None
    payment_and_invoice_reviewed: Optional[bool] = None


class Applicant(ApplicantWebfile):
    """Backward-compatible name for Webfile applicant information."""
