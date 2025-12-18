# Guía de Consumo de API - HolaEnfermera Android

**Base URL Producción:** `https://holaenfermera.ecuapulselab.com`

---

## 1. Autenticación (JWT)

> **Nota:** Todos los endpoints (excepto Login) requieren el header:
> `Authorization: Bearer <access_token>`

### **Iniciar Sesión**

- **Método:** `POST`
- **Endpoint:** `/api/auth/login/`
- **Body:**
  ```json
  {
    "email": "admin@ejemplo.com",
    "password": "tu_password"
  }
  ```
- **Respuesta:** Retorna `access` y `refresh` tokens.

### **Perfil de Usuario (Quién soy)**

- **Método:** `GET`
- **Endpoint:** `/api/auth/me/`
- **Uso:** Obtener nombre, rol y foto para mostrar en el perfil o drawer.

---

## 2. Funcionalidad: Recordatorios (Leads)

_Botón Principal: "Recordatorios"_

### **Listar Recordatorios**

- **Método:** `GET`
- **Endpoint:** `/api/leads/`
- **Parámetros (Filtros Opcionales):**
  - `?estado=PENDIENTE` (o `COMPLETADO`, `CANCELADO`)
  - `?origen=WEB` (o `MANUAL`)
  - `?search=NombrePaciente` (Busca por nombre o cédula)
  - `?ordering=fecha_limite_sugerida` (Orden por fecha)

### **Ver Detalle**

- **Método:** `GET`
- **Endpoint:** `/api/leads/{id}/`

### **Actualizar Estado (Ej: Marcar como realizado)**

- **Método:** `PATCH`
- **Endpoint:** `/api/leads/{id}/`
- **Body:**
  ```json
  {
    "estado": "COMPLETADO",
    "notas": "Paciente contactado y agendado."
  }
  ```

---

## 3. Funcionalidad: Servicios

_Botón Principal: "Servicios"_

### **Listar Catálogo de Servicios**

- **Método:** `GET`
- **Endpoint:** `/api/config/services/`
- **Uso:** Muestra la lista de precios y servicios disponibles.
- **Búsqueda:** `?search=Inyeccion`

### **Listar Categorías**

- **Método:** `GET`
- **Endpoint:** `/api/config/categories/`
- **Uso:** Para llenar dropdowns de filtros.

---

## 4. Funcionalidad: Medicamentos

_Botón Principal: "Medicamentos"_

### **Listar Catálogo de Medicamentos**

- **Método:** `GET`
- **Endpoint:** `/api/config/medications/`
- **Uso:** Lista de medicamentos registrados para configuración de precios/frecuencias.
- **Búsqueda:** `?search=Paracetamol`

---

## 5. Funcionalidad: Gestión de Usuarios

_API para registrar y listar actores._

### **Listar Pacientes**

- **Método:** `GET`
- **Endpoint:** `/api/users/patients/`
- **Búsqueda:** `?search=Nombre o Cedula`
- **Respuesta:** Lista de objetos (id, fullname, cedula, email).

### **Listar Enfermeros**

- **Método:** `GET`
- **Endpoint:** `/api/users/nurses/`
- **Búsqueda:** `?search=Nombre o Cedula`

### **Crear Paciente**

- **Método:** `POST`
- **Endpoint:** `/api/users/patients/create/`
- **Body:**
  ```json
  {
    "first_name": "Juan",
    "last_name": "Perez",
    "cedula": "0912345678", // Obligatorio, único
    "telefono": "099999999",
    "email": "", // Opcional (Si vacío -> genera cedula@holaenfermera.com)
    "direccion": "Av. 123", // Opcional
    "ciudad": "Guayaquil", // Opcional
    "alergias": "Ninguna", // Opcional
    "lat": -2.123, // Opcional
    "lng": -79.123 // Opcional
  }
  ```
- **Respuesta Exitosa:** Retorna objeto User creado.

### **Crear Enfermero**

- **Método:** `POST`
- **Endpoint:** `/api/users/nurses/create/`
- **Body:**
  ```json
  {
    "first_name": "Maria",
    "last_name": "Suarez",
    "cedula": "0987654321",
    "email": "maria@gmail.com", // Obligatorio para enfermeros
    "telefono": "098888888",
    "registro_profesional": "", // Opcional
    "es_motorizado": true,
    "zona_cobertura": "Norte"
  }
  ```

---

## 6. Funcionalidad: Crear Recordatorio Manual

_Endpoint exclusivo para que Admins creen recordatorios desde la App._

### **Crear Recordatorio**

- **Método:** `POST`
- **Endpoint:** `/api/leads/create/`
- **Body:**
  ```json
  {
    "paciente_id": 123, // ID Numérico del Paciente (Obligatorio)
    "medicamento_externo": "Vitamina C", // Opción A: Texto libre
    "medicamento_catalogo_id": null, // Opción B: ID del catálogo (si aplica)
    "fecha_limite_sugerida": "2024-05-20", // YYYY-MM-DD
    "notas": "Nota opcional"
  }
  ```

---

## 💡 RESUMEN DE FLUJO: Crear Recordatorio Manual

_(Instrucciones para Lógica de UI en Android)_

El proceso correcto para evitar errores debe ser:

1.  **🔍 Buscar Usuario:**
    - Usar Endpoint `/api/leads/?search=cedula_o_nombre` para ver si ya existe.
    - O endpoint de búsqueda específica si existiera.
2.  **➕ Si NO existe:**
    - Usar botón flotante "+" -> Llamar a **Crear Paciente** (`/api/users/patients/create/`).
    - Obtener el `id` de la respuesta.
3.  **✅ Con el Usuario listo (ID):**
    - Llamar a **Crear Recordatorio** (`/api/leads/create/`) enviando ese `paciente_id`.
