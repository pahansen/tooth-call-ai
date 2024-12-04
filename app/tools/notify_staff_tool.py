class NotifyStaffTool():
    create_call_back_description = {
        "type": "function",
        "name": "create_call_back",
        "description": "Notiert eine Rückrufbitte für das Praxisteam.",
        "parameters": {
            "type": "object",
            "properties": {
                "preferred_contact": {
                    "type": "string",
                    "description": "Auf welche Weise soll das Praxisteam Kontakt aufnehmen. Beispielsweise E-Mail oder Telefonnummer.",
                },
                "description": {
                    "type": "string",
                    "description": "Beschreibung zu welchem Thema sich das Praxisteam beim Anrufer melden soll.",
                },
                "name": {"type": "string", "description": "Name des Kunden."},
            },
            "required": ["description", "name", "preferred_contact"],
            "additionalProperties": False,
        },
    }

    @classmethod
    def get_create_call_back_description(self) -> str:
        return self.create_call_back_description

    @classmethod
    def create_call_back() -> str:
        """Not yet implemented.
        TODO: Add database interaction.
        """
        return ("Rückrufbitte erfolgreich notiert.")
