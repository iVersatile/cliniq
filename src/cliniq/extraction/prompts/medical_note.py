_SYSTEM = """\
You are a clinical record parser. Extract structured data from the clinical text.
Return JSON only. Never hallucinate — if a field is absent, use null.
For every medication or diagnosis extracted, include the verbatim source sentence
in a 'source' field.
"""


def extract_medical_note(doc, adapter, result) -> None:  # type: ignore[no-untyped-def]
    # TODO: implement prompt + schema call
    pass
