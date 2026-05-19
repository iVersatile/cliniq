from cliniq.extraction.prompts.appointment import extract_appointments
from cliniq.extraction.prompts.contact import extract_contacts
from cliniq.extraction.prompts.medical_note import extract_medical_note
from cliniq.extraction.prompts.medication import extract_medications


def extract_all(doc, adapter, result) -> None:  # type: ignore[no-untyped-def]
    extract_contacts(doc, adapter, result)
    extract_medications(doc, adapter, result)
    extract_appointments(doc, adapter, result)
    extract_medical_note(doc, adapter, result)
