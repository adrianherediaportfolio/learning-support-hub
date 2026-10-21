# Shared API contract

`learning-support-hub` uses this contract to request text adaptations. Keep the request and response fields stable.

## Endpoints

```text
POST /api/adaptations            (JSON)
  request:  { "text": str (1..20000), "level": "lectura_facil" | "simplificado" (default "lectura_facil"),
              "pictograms": bool (default true), "source": str | null (optional free label, e.g. "learning-support-hub") }
POST /api/adaptations/upload     (multipart: file, level, pictograms)
GET /api/adaptations             -> list of AdaptationSummary {id, created_at, level, preview}
GET /api/adaptations/{id}        -> Adaptation
DELETE /api/adaptations/{id}     -> 204
GET /api/health                  -> {"status":"ok","ai_enabled":bool}
```

## Adaptation response

Create endpoints return `201`.

```json
{
  "id": "uuid",
  "created_at": "ISO8601",
  "level": "lectura_facil",
  "source": "learning-support-hub",
  "original_text": "Texto original.",
  "adapted_text": "Texto adaptado.",
  "sentences": [
    {
      "text": "Texto adaptado.",
      "pictograms": [
        {
          "keyword": "texto",
          "arasaac_id": 1234,
          "image_url": "https://static.arasaac.org/pictograms/1234/1234_300.png"
        }
      ]
    }
  ],
  "readability": {
    "original": {"score": 50.0, "label": "algo difícil"},
    "adapted": {"score": 80.0, "label": "muy fácil"}
  },
  "engine": "rules",
  "attribution": "Pictogramas: Sergio Palao. Origen: ARASAAC (http://www.arasaac.org). Licencia: CC (BY-NC-SA). Propiedad: Gobierno de Aragón (España)"
}
```

`source` may be `null`. `engine` is `openai` or `rules`. Each sentence has zero or more pictograms. When `API_KEY` is configured, send it in the `X-API-Key` header. `/api/health` remains public.
