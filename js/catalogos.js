// Catálogos locales: vehículos y ciudades copiados de backend/datos_sinteticos (datos de ejemplo).
// Cargas tomadas de backend/dominio.py; carga general se representa como cadena vacía en la UI (null al integrar backend).
// Sin peticiones al backend ni reglas de compatibilidad. Agrega aquí las opciones oficiales cuando existan.
export const CATALOGOS = {
  "carga": [
    {
      "label": "Carga general",
      "value": ""
    },
    {
      "label": "Refrigerada",
      "value": "refrigerado"
    },
    {
      "label": "Sobredimensionada",
      "value": "sobredimensionado"
    },
    {
      "label": "Peligrosa",
      "value": "peligrosa"
    }
  ],
  "vehiculo": [
    {
      "label": "Tractocamión plataforma 40'",
      "value": "TV-PLAT40"
    },
    {
      "label": "Camión sencillo 20'",
      "value": "TV-SENC20"
    },
    {
      "label": "Tractocamión refrigerado 40'",
      "value": "TV-REFRI40"
    },
    {
      "label": "Cama baja",
      "value": "TV-CAMABAJA"
    }
  ],
  "destino": [
    {
      "label": "Bogotá",
      "value": "BOG"
    },
    {
      "label": "Medellín",
      "value": "MED"
    }
  ]
};

