from src.schemas import MaterialOutput


def test_legacy_arasaac_materials_are_normalized_to_contract_v2() -> None:
    material = MaterialOutput.model_validate(
        {
            "id": 4,
            "student_id": 2,
            "title": "Lectura",
            "original_text": "La niña lee.",
            "adapted_text": "La niña lee.",
            "adaptation_id": "old-adaptation",
            "adapter_url": "http://localhost:8000",
            "sentences": [
                {
                    "text": "La niña lee.",
                    "pictograms": [
                        {
                            "keyword": "lectura",
                            "arasaac_id": 1234,
                            "image_url": "https://static.arasaac.org/pictograms/1234/1234_300.png",
                        }
                    ],
                }
            ],
            "attributions": None,
            "attribution": (
                "Pictogramas: Sergio Palao. Origen: ARASAAC (http://www.arasaac.org). "
                "Licencia: CC (BY-NC-SA). Propiedad: Gobierno de Aragón (España)"
            ),
        }
    )

    assert material.sentences[0]["pictograms"][0] == {
        "keyword": "lectura",
        "source": "arasaac",
        "id": "1234",
        "image_url": "https://static.arasaac.org/pictograms/1234/1234_300.png",
        "license": "CC BY-NC-SA 4.0",
        "commercial_use": False,
    }
    assert material.attributions == [material.attribution]
