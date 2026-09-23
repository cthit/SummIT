"""Tiny dictionary-based i18n.

t(key) returns the string in the visitor's language: an explicit choice in
session["lang"] (set via the navbar toggle), otherwise the browser's
Accept-Language, otherwise English. Deliberately no extraction tooling -
just keep this dictionary alphabetical and add both languages for every key.
"""

from flask import has_request_context, request, session

LANGUAGES = ("en", "sv")

TRANSLATIONS = {
    # Navigation
    "nav.home": {"en": "Home", "sv": "Hem"},
    "nav.documents": {"en": "Documents", "sv": "Dokument"},
    "nav.meeting_admin": {"en": "Meeting Admin", "sv": "Mötesadmin"},
    "nav.liberation_admin": {"en": "Liberation Admin", "sv": "Ansvarsfrihetsadmin"},
    "nav.profile": {"en": "Profile", "sv": "Profil"},
    "nav.login": {"en": "Login", "sv": "Logga in"},
    "nav.logout": {"en": "Logout", "sv": "Logga ut"},
    # Index
    "index.title": {"en": "Welcome to SummIT", "sv": "Välkommen till SummIT"},
    "index.subtitle": {
        "en": "Easy handling of meeting related things and stuff.",
        "sv": "Enkel hantering av mötesrelaterade saker och ting.",
    },
    # Login
    "login.title": {"en": "Login", "sv": "Logga in"},
    "login.extra_groups": {
        "en": "Select Extra Access Groups:",
        "sv": "Välj extra åtkomstgrupper:",
    },
    "login.button": {"en": "Login", "sv": "Logga in"},
    # Profile
    "profile.welcome": {"en": "Welcome, {name}!", "sv": "Välkommen, {name}!"},
    "profile.info": {"en": "Profile Information", "sv": "Profilinformation"},
    "profile.user_id": {"en": "User ID", "sv": "Användar-ID"},
    "profile.name": {"en": "Name", "sv": "Namn"},
    "profile.email": {"en": "Email", "sv": "E-post"},
    "profile.nickname": {"en": "Nickname", "sv": "Smeknamn"},
    "profile.groups": {"en": "Groups", "sv": "Grupper"},
    "profile.not_logged_in": {
        "en": "You are not logged in.",
        "sv": "Du är inte inloggad.",
    },
    # Meetings / study periods
    "meeting.study_period": {"en": "Study Period {lp}", "sv": "Läsperiod {lp}"},
    "meeting.summer": {"en": "Summer", "sv": "Sommar"},
    "meeting.select": {"en": "Choose meeting:", "sv": "Välj möte:"},
    "meeting.select_placeholder": {
        "en": "Select a meeting...",
        "sv": "Välj ett möte...",
    },
    # Meeting admin
    "admin.title": {"en": "Meeting Admin", "sv": "Mötesadmin"},
    "admin.create_meeting": {"en": "Create Meeting", "sv": "Skapa möte"},
    "admin.edit_meeting": {"en": "Edit Meeting", "sv": "Redigera möte"},
    "admin.update_meeting": {"en": "Update Meeting", "sv": "Uppdatera möte"},
    "admin.delete_meeting": {"en": "Delete Meeting", "sv": "Ta bort möte"},
    "admin.download_documents": {
        "en": "Download Meeting Documents",
        "sv": "Ladda ner mötesdokument",
    },
    "admin.send_announcement": {"en": "Send Announcement", "sv": "Skicka utskick"},
    "admin.confirm_delete": {
        "en": "Delete this meeting and all associated documents?",
        "sv": "Ta bort detta möte och alla tillhörande dokument?",
    },
    "admin.confirm_announcement": {
        "en": "Send announcement mail to all groups with requirements?",
        "sv": "Skicka utskick till alla grupper med dokumentkrav?",
    },
    "admin.requirements": {"en": "Document Requirements", "sv": "Dokumentkrav"},
    "admin.group": {"en": "Group", "sv": "Grupp"},
    "admin.meeting_date": {"en": "Meeting Date", "sv": "Mötesdatum"},
    "admin.deadline": {"en": "Upload Deadline", "sv": "Uppladdningsdeadline"},
    "admin.study_period_label": {"en": "Study Period:", "sv": "Läsperiod:"},
    "admin.pick_a_date": {"en": "pick a date", "sv": "välj ett datum"},
    "admin.cancel": {"en": "Cancel", "sv": "Avbryt"},
    # Liberation admin
    "liberation.title": {"en": "Liberation Admin", "sv": "Ansvarsfrihetsadmin"},
    "liberation.required_documents": {
        "en": "Required Liberation Documents",
        "sv": "Krävda ansvarsfrihetsdokument",
    },
    "liberation.grid_hint": {
        "en": "Choose a committee and the year of the sitting group that must submit liberation documents (e.g. digIT + 25 = digit25).",
        "sv": "Välj en kommitté och året för den sittande grupp som ska lämna in ansvarsfrihetsdokument (t.ex. digIT + 25 = digit25).",
    },
    "liberation.committee": {"en": "Committee", "sv": "Kommitté"},
    "liberation.select_committee": {
        "en": "Select committee...",
        "sv": "Välj kommitté...",
    },
    "liberation.year": {"en": "Year", "sv": "År"},
    "liberation.all_types": {"en": "All document types", "sv": "Alla dokumenttyper"},
    "liberation.add_requirement": {"en": "Add Requirement", "sv": "Lägg till krav"},
    "liberation.remove": {"en": "Remove", "sv": "Ta bort"},
    "liberation.all_uploaded": {"en": "All uploaded", "sv": "Allt uppladdat"},
    "liberation.no_requirements": {
        "en": "No liberation requirements set yet.",
        "sv": "Inga ansvarsfrihetskrav har satts ännu.",
    },
    "liberation.missing": {"en": "Missing Documents", "sv": "Saknade dokument"},
    "liberation.send_reminders": {
        "en": "Send Liberation Reminders",
        "sv": "Skicka ansvarsfrihetspåminnelser",
    },
    "liberation.confirm_send": {
        "en": "Send duty liberation reminders to groups with missing documents?",
        "sv": "Skicka ansvarsfrihetspåminnelser till grupper med saknade dokument?",
    },
    # Documents page
    "doc.title": {"en": "Documents", "sv": "Dokument"},
    "doc.upload_prompt": {
        "en": "Need to upload a document?",
        "sv": "Behöver du ladda upp ett dokument?",
    },
    "doc.click_here": {"en": "Click here", "sv": "Klicka här"},
    "doc.selected_meeting": {"en": "Selected Meeting:", "sv": "Valt möte:"},
    "doc.deadline": {"en": "Upload deadline:", "sv": "Uppladdningsdeadline:"},
    "doc.my_documents": {"en": "My Documents", "sv": "Mina dokument"},
    "doc.delete": {"en": "(delete)", "sv": "(ta bort)"},
    "doc.confirm_delete": {
        "en": "Are you sure you want to delete this document?",
        "sv": "Är du säker på att du vill ta bort detta dokument?",
    },
    "doc.none_found": {
        "en": "No documents found for this meeting.",
        "sv": "Inga dokument hittades för detta möte.",
    },
    # Upload page
    "upload.title": {"en": "Upload File", "sv": "Ladda upp fil"},
    "upload.as": {"en": "Upload as:", "sv": "Ladda upp som:"},
    "upload.select_owner": {"en": "Select owner...", "sv": "Välj ägare..."},
    "upload.myself": {"en": "Myself", "sv": "Jag själv"},
    "upload.document_type": {"en": "Document type:", "sv": "Dokumenttyp:"},
    "upload.meeting_document": {"en": "Meeting Document", "sv": "Mötesdokument"},
    "upload.division_document": {"en": "Division Document", "sv": "Sektionsdokument"},
    "upload.liberation_document": {
        "en": "Liberation Document",
        "sv": "Ansvarsfrihetsdokument",
    },
    "upload.meeting_subtype": {
        "en": "Meeting document type:",
        "sv": "Typ av mötesdokument:",
    },
    "upload.division_subtype": {
        "en": "Division document type:",
        "sv": "Typ av sektionsdokument:",
    },
    "upload.liberation_subtype": {
        "en": "Liberation document type:",
        "sv": "Typ av ansvarsfrihetsdokument:",
    },
    "upload.select_type": {"en": "Select type...", "sv": "Välj typ..."},
    "upload.choose_file": {"en": "Choose file (PDF):", "sv": "Välj fil (PDF):"},
    "upload.submit": {"en": "Upload", "sv": "Ladda upp"},
    "upload.required_suffix": {"en": " (required)", "sv": " (krävs)"},
    "upload.not_required_warning": {
        "en": "This document type is not required from this group for this meeting - upload anyway if intentional.",
        "sv": "Denna dokumenttyp krävs inte av denna grupp för detta möte - ladda upp ändå om det är avsiktligt.",
    },
    "upload.deadline_banner": {
        "en": "The upload deadline for this meeting has passed. Only meeting admins can upload meeting or division documents now (liberation documents are unaffected).",
        "sv": "Uppladdningsdeadline för detta möte har passerat. Endast mötesadministratörer kan ladda upp mötes- eller sektionsdokument nu (ansvarsfrihetsdokument påverkas inte).",
    },
    # Flash messages: forms and meetings
    "flash.required_fields": {
        "en": "Meeting date and upload deadline are required.",
        "sv": "Mötesdatum och uppladdningsdeadline krävs.",
    },
    "flash.invalid_date_or_deadline": {
        "en": "Invalid meeting date or deadline.",
        "sv": "Ogiltigt mötesdatum eller deadline.",
    },
    "flash.invalid_deadline": {"en": "Invalid deadline.", "sv": "Ogiltig deadline."},
    "flash.deadline_after_meeting": {
        "en": "Deadline must be on or before the meeting date.",
        "sv": "Deadline måste vara samma dag som mötet eller tidigare.",
    },
    "flash.study_period_failed": {
        "en": "Failed to create study period.",
        "sv": "Kunde inte skapa läsperiod.",
    },
    "flash.meeting_exists": {
        "en": "A meeting already exists on {date}.",
        "sv": "Det finns redan ett möte den {date}.",
    },
    "flash.meeting_created": {
        "en": "Meeting created successfully.",
        "sv": "Mötet har skapats.",
    },
    "flash.meeting_updated": {
        "en": "Meeting updated successfully.",
        "sv": "Mötet har uppdaterats.",
    },
    "flash.meeting_not_found": {
        "en": "Meeting not found.",
        "sv": "Mötet hittades inte.",
    },
    "flash.meeting_deleted": {
        "en": "Meeting and associated documents deleted successfully.",
        "sv": "Mötet och tillhörande dokument har tagits bort.",
    },
    "flash.meeting_delete_failed": {
        "en": "Failed to delete meeting.",
        "sv": "Kunde inte ta bort mötet.",
    },
    "flash.deadline_update_failed": {
        "en": "Failed to update deadline.",
        "sv": "Kunde inte uppdatera deadline.",
    },
    "flash.no_meeting_documents": {
        "en": "No documents have been uploaded for this meeting yet.",
        "sv": "Inga dokument har laddats upp för detta möte ännu.",
    },
    "flash.liberation_requirement_added": {
        "en": "Liberation requirement added.",
        "sv": "Ansvarsfrihetskrav tillagt.",
    },
    "flash.liberation_requirement_removed": {
        "en": "Liberation requirement removed.",
        "sv": "Ansvarsfrihetskrav borttaget.",
    },
    "flash.liberation_invalid": {
        "en": "Invalid group selection.",
        "sv": "Ogiltigt gruppval.",
    },
    # Flash messages: upload
    "flash.no_file": {"en": "No file selected.", "sv": "Ingen fil vald."},
    "flash.invalid_meeting": {
        "en": "Please select a valid meeting.",
        "sv": "Välj ett giltigt möte.",
    },
    "flash.no_owner": {
        "en": "Please select who to upload as.",
        "sv": "Välj vem du laddar upp som.",
    },
    "flash.no_type": {
        "en": "Please select a document type.",
        "sv": "Välj en dokumenttyp.",
    },
    "flash.self_meeting_only": {
        "en": "You can only upload meeting documents as yourself.",
        "sv": "Du kan bara ladda upp mötesdokument som dig själv.",
    },
    "flash.self_motion_only": {
        "en": "You can only upload motions or other documents as yourself.",
        "sv": "Du kan bara ladda upp motioner eller övriga dokument som dig själv.",
    },
    "flash.no_subtype": {
        "en": "Please select a document subtype.",
        "sv": "Välj en dokumentundertyp.",
    },
    "flash.invalid_subtype": {
        "en": "Please select a valid document subtype.",
        "sv": "Välj en giltig dokumentundertyp.",
    },
    "flash.deadline_passed": {
        "en": "The upload deadline for this meeting has passed.",
        "sv": "Uppladdningsdeadline för detta möte har passerat.",
    },
    "flash.not_group_member": {
        "en": "You are not a member of that group.",
        "sv": "Du är inte medlem i den gruppen.",
    },
    "flash.pdf_only": {
        "en": "Only PDF files are allowed.",
        "sv": "Endast PDF-filer är tillåtna.",
    },
    "flash.duplicate_file": {
        "en": "This exact file has already been uploaded.",
        "sv": "Exakt samma fil har redan laddats upp.",
    },
    "flash.upload_success": {
        "en": "Document uploaded successfully.",
        "sv": "Dokumentet har laddats upp.",
    },
    # Flash messages: documents
    "flash.file_missing": {
        "en": "The file for this document is missing on the server. Please contact the meeting admins.",
        "sv": "Filen för detta dokument saknas på servern. Kontakta mötesadministratörerna.",
    },
    "flash.document_deleted": {
        "en": "Document deleted successfully.",
        "sv": "Dokumentet har tagits bort.",
    },
    "flash.document_delete_denied": {
        "en": "Document not found, or you do not have permission to delete it.",
        "sv": "Dokumentet hittades inte, eller så saknar du behörighet att ta bort det.",
    },
    # Flash messages: mail
    "flash.mail_no_requirements": {
        "en": "This meeting has no document requirements - no mail sent.",
        "sv": "Detta möte har inga dokumentkrav - inget utskick gjordes.",
    },
    "flash.mail_gamma_failed": {
        "en": "Could not fetch groups from Gamma - no mail sent.",
        "sv": "Kunde inte hämta grupper från Gamma - inget utskick gjordes.",
    },
    "flash.mail_announce_failed": {
        "en": "Failed to send announcement to {group}. Check that the mail service is running.",
        "sv": "Kunde inte skicka utskick till {group}. Kontrollera att mailtjänsten är igång.",
    },
    "flash.mail_groups_skipped": {
        "en": "{count} group(s) were unknown to Gamma and skipped.",
        "sv": "{count} grupp(er) var okända för Gamma och hoppades över.",
    },
    "flash.mail_announce_sent": {
        "en": "Announcement mail sent to {count} group(s).",
        "sv": "Utskick skickat till {count} grupp(er).",
    },
    "flash.mail_liberation_failed": {
        "en": "Failed to send liberation mail to {group}.",
        "sv": "Kunde inte skicka ansvarsfrihetspåminnelse till {group}.",
    },
    "flash.mail_liberation_sent": {
        "en": "Liberation reminder sent to {count} group(s).",
        "sv": "Ansvarsfrihetspåminnelse skickad till {count} grupp(er).",
    },
    "flash.mail_liberation_none": {
        "en": "No liberation reminders to send - nothing missing, or already sent this year.",
        "sv": "Inga ansvarsfrihetspåminnelser att skicka - inget saknas, eller redan skickat i år.",
    },
    # Error pages
    "error.title": {"en": "An error occurred", "sv": "Ett fel uppstod"},
    "error.code": {"en": "Error code:", "sv": "Felkod:"},
    "error.back_home": {"en": "Back to home", "sv": "Tillbaka till startsidan"},
    "error.forbidden": {
        "en": "You do not have permission to do that.",
        "sv": "Du har inte behörighet att göra det.",
    },
    "error.not_found": {
        "en": "The page or document you asked for does not exist.",
        "sv": "Sidan eller dokumentet du sökte finns inte.",
    },
    "error.server": {
        "en": "Something went wrong on our end. Please try again.",
        "sv": "Något gick fel hos oss. Försök igen.",
    },
    "error.file_too_large": {
        "en": "File is too large. Maximum size is {max_mb} MB.",
        "sv": "Filen är för stor. Maxstorleken är {max_mb} MB.",
    },
    "error.denied": {
        "en": "You cannot access this page >:(",
        "sv": "Du har inte åtkomst till den här sidan >:(",
    },
}


def get_locale() -> str:
    if not has_request_context():
        return "en"
    lang = session.get("lang")
    if lang in LANGUAGES:
        return lang
    return request.accept_languages.best_match(LANGUAGES) or "en"


def t(key: str, **kwargs) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(get_locale()) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
