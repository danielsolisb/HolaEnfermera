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
