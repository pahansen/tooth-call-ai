"""Interact with calendars from cal.com.
"""

import json
import os
from datetime import datetime

import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from app.prompts.prompt_file_paths import FIND_CALENDAR_ENTRIES

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CAL_API_KEY = os.getenv("CAL_API_KEY")

openai.api_key = OPENAI_API_KEY


class CalendarBookingInformation(BaseModel):
    uid: str
    attendee_name: str
    start: str


class CalTool:
    create_booking_description = {
        "type": "function",
        "name": "create_booking",
        "description": "Erstellt eine Buchung im Kalender.",
        "parameters": {
            "type": "object",
            "properties": {
                "additonal_notes": {
                    "type": "string",
                    "description": "Eine sehr kurze Zusammenfassung für welchen Anlass der Nutzer diesen Termin gebucht hat.",
                },
                "start": {
                    "type": "string",
                    "description": "Datum des Termins. Beispiel des korrekten Formats: 2024-08-13T09:00:00Z",
                },
                "attendee_name": {"type": "string", "description": "Name des Kunden."},
            },
            "required": ["start", "attendee_name"],
            "additionalProperties": False,
        },
    }

    cancel_booking_description = {
        "type": "function",
        "name": "cancel_booking",
        "description": "Storniert eine Buchung aus dem Kalender.",
        "parameters": {
            "type": "object",
            "properties": {
                "uid": {
                    "type": "string",
                    "description": "Frage den Nutzer NIEMALS nach diesem Parameter. Füge ihn nur hinzu, wenn er in der Konversation bereits auftaucht.",
                },
                "start": {
                    "type": "string",
                    "description": "Datum des Termins. Beispiel des korrekten Formats: 2024-08-13",
                },
                "attendee_name": {"type": "string", "description": "Name des Kunden."},
            },
            "required": ["start", "attendee_name"],
            "additionalProperties": False,
        },
    }

    @classmethod
    def get_create_booking_description(self) -> str:
        return self.create_booking_description

    @classmethod
    def get_cancel_booking_description(self) -> str:
        return self.cancel_booking_description

    @classmethod
    def create_booking(
        self, start: str, attendee_name: str, additonal_notes: str = None
    ):
        url = "https://api.cal.com/v2/bookings"
        payload = {
            "start": start,
            "eventTypeId": 1479842,
            "attendee": {
                "name": attendee_name,
                "email": "john.doe@example.com",
                "timeZone": "Europe/Berlin",
                "language": "de",
            },
        }
        if additonal_notes:
            payload["metadata"] = {"additonal_notes": additonal_notes}

        headers = {
            "cal-api-version": "2024-08-13",
            "Content-Type": "application/json",
            "Auhtorization": f"Bearer {CAL_API_KEY}",
        }

        response = requests.request("POST", url, json=payload, headers=headers)

        response = json.loads(response.text)
        response_result = response.get("status")

        if response_result == "error":
            return "Kalendereintrag konnte nicht gebucht werden. Anderes Datum oder Uhrzeit versuchen."

        booking_uid = response["data"]["uid"]
        return f"Kalendereintrag konnte erfolgreich gebucht werden. bookingUid: {booking_uid}"

    @classmethod
    def cancel_booking(
        self, uid: str = None, start: str = None, attendee_name: str = None
    ):
        headers = {
            "cal-api-version": "2024-08-13",
            "Authorization": f"Bearer {CAL_API_KEY}",
        }

        # If uid is available from conversation, cancel directly
        if uid:
            url = f"https://api.cal.com/v2/bookings/{uid}/cancel"
            response = requests.request("POST", url, headers=headers)

        # Otherwise we have to find uid from date and name
        # We assume that we at least have the correct date
        # However, name might not be spelled correctly
        else:
            input_date = datetime.strptime(start, "%Y-%m-%d")
            start_datetime = input_date.replace(
                hour=7, minute=0, second=0, microsecond=0
            )
            end_datetime = input_date.replace(
                hour=22, minute=0, second=0, microsecond=0
            )
            start_datetime_str = start_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_datetime_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            url = f"https://api.cal.com/v2/bookings?afterStart={start_datetime_str}&beforeEnd={end_datetime_str}"
            response = requests.request("GET", url, headers=headers)

            # Use OpenAI to find the correct entry from list of calendar entries
            # This allows fuzzy inputs for name and accounts for misspelling
            client = OpenAI()
            response_text = str(response.text)

            with open(FIND_CALENDAR_ENTRIES) as file:
                find_calendar_entries_prompt = file.read()
            find_calendar_entries_prompt = find_calendar_entries_prompt.replace(
                "{{attendee_name}}", attendee_name
            )
            find_calendar_entries_prompt = find_calendar_entries_prompt.replace(
                "{{start}}", start
            )

            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": find_calendar_entries_prompt},
                    {"role": "user", "content": response_text},
                ],
                response_format=CalendarBookingInformation,
            )
            calendar_booking_information = completion.choices[0].message.parsed

            url = f"https://api.cal.com/v2/bookings/{calendar_booking_information.uid}/cancel"
            response = requests.request("POST", url, headers=headers)

        response = json.loads(response.text)
        response_result = response.get("status")
        if response_result != "success":
            return "Kalendereintrag konnte nicht storniert werden."

        return "Kalendereintrag wurde erfolgreich storniert."


if __name__ == "__main__":
    # Function calls for quick integration testing
    CalTool.create_booking(
        start="2024-12-08T10:00:00Z",
        attendee_name="Peter Müller",
        additonal_notes="Zahnreinigung",
    )
    CalTool.cancel_booking(start="2024-12-10", attendee_name="Peter Muuhler")
