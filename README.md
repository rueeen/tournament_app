# MTG Match Manager (MVP)

Aplicación web Django mobile-first para gestionar jugadores, mazos y partidas de **Magic: The Gathering** con confirmación consensuada de resultados y rankings globales.

## Stack
- Django (backend + templates)
- SQLite (por defecto)
- Bootstrap 5 (UI responsiva)
- Django Auth nativo
- Django ORM + ImageField (almacenamiento local)

## Arquitectura
Proyecto dividido por dominios:
- `accounts`: registro, perfil, avatar, estadísticas de jugador
- `decks`: CRUD de mazos y colores
- `matches`: creación de partidas, invitaciones, propuesta/aceptación/rechazo de resultados
- `rankings`: rankings globales y métricas
- `core`: dashboard, errores 404/500, estáticos compartidos

## Modelo de datos principal
- `User` (Django)
- `Profile` (1:1 con User)
- `Deck`
- `DeckColor` (N:M con Deck)
- `Match`
- `MatchPlayer` (usuario + mazo elegido en partida)
- `MatchInvitation`
- `MatchResultProposal`
- `MatchResultAcceptance`

## Reglas de negocio implementadas
- Partidas de 2 a 4 jugadores (validación en formulario).
- Participantes únicos por partida (`unique_together`).
- Ganador debe ser participante de la partida.
- Resultado pendiente hasta confirmación total.
- Rechazo mueve la partida a estado `disputed`.
- Estadísticas de jugador/mazo se actualizan **solo** cuando todos los participantes aceptan.
- No se permite doble aceptación por usuario/propuesta (`unique_together`).

## Vistas incluidas
- Login / Registro
- Dashboard
- Perfil
- Listado / creación / edición / eliminación de mazos
- Listado de partidas
- Creación de partida
- Detalle de partida
- Invitaciones
- Propuesta de resultado
- Confirmación (aceptar/rechazar)
- Rankings globales

## Instalación local
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install django pillow
python manage.py migrate
python manage.py loaddata fixtures/deck_colors.json
python manage.py seed_demo_data
python manage.py runserver
```

Credenciales demo (generadas por `seed_demo_data`):
- usuarios: `alice`, `bob`, `carla`, `dario`
- password: `Pass1234!`

## Archivos estáticos y media
- `STATIC_URL=/static/`
- `MEDIA_URL=/media/`
- `MEDIA_ROOT=media/`

## Migración futura a PostgreSQL
El código usa ORM y capas desacopladas, por lo que basta cambiar `DATABASES` en `settings.py`, instalar `psycopg` y correr migraciones.

## Notas MVP
- Incluye trazabilidad de propuestas y decisiones con timestamp.
- Incluye feedback con mensajes flash.
- Incluye estados vacíos y loaders básicos en frontend.
