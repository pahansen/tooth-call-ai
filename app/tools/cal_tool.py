import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

CAL_API_KEY = os.getenv("CAL_API_KEY")


class CalTool:
    booking_description = {
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

    @classmethod
    def get_booking_description(self) -> str:
        return self.booking_description

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
        return json.loads(response.text)["status"]


if __name__ == "__main__":
    CalTool.create_booking(
        "some random note", "2025-12-13T09:00:00Z", "John Doe")
