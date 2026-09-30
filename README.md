# Plataforma EdTech de Cursos y Bootcamps

Backend desarrollado con Django REST Framework y PostgreSQL para estudiantes y coordinadores académicos.

## Configuración

1. Crear una base PostgreSQL llamada `edtech_db` y copiar `.env.example` a `.env` o definir esas variables en el sistema.
2. Instalar dependencias: `env\Scripts\python.exe -m pip install -r requirements.txt`.
3. Ejecutar migraciones: `env\Scripts\python.exe manage.py migrate`.
4. Crear un administrador: `env\Scripts\python.exe manage.py createsuperuser`.
5. Iniciar: `env\Scripts\python.exe manage.py runserver`.

El administrador puede crear áreas, cursos y perfiles. Para gestionar catálogo y estados, el usuario debe tener un `UserProfile` con rol `COORDINATOR` o ser superusuario.

## API

- `GET /api/areas/` y `GET /api/cursos/`: catálogo público.
- `GET /api/cursos/?area=1&price__lte=100000`: filtros por área, precio y fecha.
- `POST /api/token/` y `POST /api/token/refresh/`: JWT. El token contiene el claim `role`.
- `GET/POST /api/carrito/` y `DELETE /api/carrito/{item_id}/`: carro persistente 1:1 por usuario.
- `POST /api/ordenes/checkout/`: valida cupos, descuenta atómicamente y crea matrículas.
- `GET /api/ordenes/` y `GET /api/mis-matriculas/`: historial del estudiante.
- `PATCH /api/ordenes/{id}/estado/` con `{"status":"CANCELLED"}`: gestión del coordinador y reposición de cupos.
- `/api/docs/`: Swagger UI. `/api/schema/`: esquema OpenAPI.

El carro y las matrículas viven en PostgreSQL, por lo que cerrar sesión o cambiar de dispositivo no elimina los ítems guardados.