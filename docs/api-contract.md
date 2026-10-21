# Contrato API compartido

**Versión 2**

Este contrato define la integración entre `easy-read-adapter` y
`learning-support-hub`.

## Cambios de la versión 2

- Los pictogramas identifican su fuente, licencia y uso comercial.
- `arasaac_id` se sustituye por `source` e `id`.
- La respuesta incluye la lista `attributions` y mantiene `attribution` para compatibilidad.
- `/api/health` informa de la cadena configurada en `pictogram_providers`.

## Endpoints

```text
POST /api/adaptations
  request: { "text": str (1..20000), "level": "lectura_facil" | "simplificado",
             "pictograms": bool, "source": str | null }
POST /api/adaptations/upload
GET /api/adaptations
GET /api/adaptations/{id}
DELETE /api/adaptations/{id}
GET /api/health
  -> {"status":"ok","ai_enabled":bool,"pictogram_providers":[str]}
```

Los valores por defecto son `level: "lectura_facil"` y `pictograms: true`.

## Respuesta de adaptación

Las creaciones devuelven `201`.

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
          "keyword": "libro",
          "source": "own",
          "id": "libro",
          "image_url": "http://localhost:8000/pictograms/own/libro.svg",
          "license": "proprietary",
          "commercial_use": true
        }
      ]
    }
  ],
  "readability": {
    "original": {"score": 50.0, "label": "algo difícil"},
    "adapted": {"score": 80.0, "label": "muy fácil"}
  },
  "engine": "rules",
  "attributions": [
    "Mulberry Symbols de Steve Lee (mulberrysymbols.org). Licencia: CC BY-SA 4.0"
  ],
  "attribution": "Mulberry Symbols de Steve Lee (mulberrysymbols.org). Licencia: CC BY-SA 4.0"
}
```

`source` puede ser `null`. `engine` es `openai` o `rules`. Cada frase puede
tener cero o más pictogramas. `attributions` solo incluye las fuentes usadas,
en el orden de la cadena. `attribution` une esos mismos valores con ` · ` y
queda vacío cuando no se usa ninguna fuente con atribución.

Fuentes válidas: `own`, `mulberry`, `openmoji` y `arasaac`. ARASAAC usa la
licencia `CC BY-NC-SA 4.0` y `commercial_use: false`. Las otras fuentes
incluidas en la cadena permiten uso comercial según su licencia.

Cuando se configura `API_KEY`, envíala en `X-API-Key`. `/api/health` es público.
