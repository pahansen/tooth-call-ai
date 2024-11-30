import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import openai
from openai import OpenAI
from pydantic import BaseModel

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
                    "description": "Eine sehr kurze Zusammenfassung für welchen Anlass der Nutzer diesen Termin gebucht hat."
                },
                "start": {
                    "type": "string",
                    "description": "Datum des Termins. Beispiel des korrekten Formats: 2024-08-13T09:00:00Z"
                },
                "attendee_name": {
                    "type": "string",
                    "description": "Name des Kunden."
                },

            },
            "required": [
                "start", "attendee_name"
            ],
            "additionalProperties": False
        }
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
                    "description": "Frage den Nutzer NIEMALS nach diesem Parameter. Füge ihn nur hinzu, wenn er in der Konversation bereits auftaucht."
                },
                "start": {
                    "type": "string",
                    "description": "Datum des Termins. Beispiel des korrekten Formats: 2024-08-13"
                },
                "attendee_name": {
                    "type": "string",
                    "description": "Name des Kunden."
                },

            },
            "required": [
                "start", "attendee_name"
            ],
            "additionalProperties": False
        }
    }

    @classmethod
    def get_create_booking_description(self) -> str:
        return self.create_booking_description

    @classmethod
    def get_cancel_booking_description(self) -> str:
        return self.cancel_booking_description

    @classmethod
    def create_booking(self, start: str, attendee_name: str, additonal_notes: str = None):
        url = "https://api.cal.com/v2/bookings"
        payload = {
            "start": start,
            "eventTypeId": 1479842,
            "attendee": {
                "name": attendee_name,
                "email": "john.doe@example.com",
                "timeZone": "Europe/Berlin",
                "language": "de"
            }
        }
        if additonal_notes:
            payload["metadata"] = {"additonal_notes": additonal_notes}

        headers = {
            "cal-api-version": "2024-08-13",
            "Content-Type": "application/json",
            "Auhtorization": f"Bearer {CAL_API_KEY}"
        }

        response = requests.request("POST", url, json=payload, headers=headers)

        print(response.text)

        response = json.loads(response.text)
        return str({"status": response["status"], "bookingUid": response["data"]["uid"]})

    @classmethod
    def cancel_booking(self, uid: str = None, start: str = None, attendee_name: str = None):
        headers = {
            "cal-api-version": "2024-08-13",
            "Authorization": f"Bearer {CAL_API_KEY}"
        }

        # If uid is available from conversation, cancel directly
        if uid:
            url = f"https://api.cal.com/v2/bookings/{uid}/cancel"
            response = requests.request("POST", url, headers=headers)

        # Otherwise we have to find uid from date and name
        else:
            input_date = datetime.strptime(start, "%Y-%m-%d")
            start_datetime = input_date.replace(
                hour=7, minute=0, second=0, microsecond=0)
            end_datetime = input_date.replace(
                hour=22, minute=0, second=0, microsecond=0)
            start_datetime_str = start_datetime.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z")
            end_datetime_str = end_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            url = f"https://api.cal.com/v2/bookings?afterStart={start_datetime_str}&beforeEnd={end_datetime_str}"
            response = requests.request("GET", url, headers=headers)

            # Use OpenAI to find the correct entry from list of calendar entries
            # This allows fuzzy inputs for name
            client = OpenAI()
            response_text = str(response.text)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f""""
                            Du hilfst aus Kalendereinträgen notwendige Informationen zu extrahieren und diese als strukturierten output zurückzugeben. 
                            Als Input werden dir dafür mehrere Kalendereinträge gegeben. Finde mit Hilfe des Namens und des Datums den passenden 
                            Kalendereintrag. Wenn du vermutest, dass im Namen lediglich Tippfehler vorliegen, gebe den Termin trotzdem zum passenden 
                            Namen zurück. Falls du denkst der Name ist unter den Terminen nicht zu finden, gebe keine Antwort.
                            Name: {attendee_name}, Datum: {start}"""
                    },
                    {
                        "role": "user",
                        "content": response_text
                    }
                ],
                response_format=CalendarBookingInformation)
            calendar_booking_information = completion.choices[0].message.parsed

            url = f"https://api.cal.com/v2/bookings/{calendar_booking_information.uid}/cancel"
            response = requests.request("POST", url, headers=headers)

        print(response.text)

        response = json.loads(response.text)
        return str({"status": response["status"]})


if __name__ == "__main__":
    CalTool.cancel_booking(start="2024-12-10", attendee_name="Peter Muuhler")
