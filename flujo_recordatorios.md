# Flujo de Trabajo de Recordatorios - HolaEnfermera

## Análisis del Sistema Actual

### Resumen de la Funcionalidad
El sistema HolaEnfermera cuenta con un módulo de **Recordatorios/Leads** ([AppointmentReminder](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/appointments/models.py#85-162)) que permite gestionar seguimientos de pacientes para:
- **Próximas dosis de medicamentos** (Ej: Aclasta cada 12 meses, Prolia cada 6 meses)
- **Continuidad de tratamientos** (Ej: Neurobión durante 3 días)
- **Captación de leads desde landing page** (Sin datos previos)

El modelo está diseñado para recibir recordatorios de **dos orígenes**:
1. **SISTEMA**: Generados automáticamente al cerrar una cita (vía [ServiceReport](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/reports/models.py#6-72))
2. **WEB**: Solicitudes desde formularios públicos (sin cita previa)

---

## Flujo 1: Recordatorios CON DATOS (Desde Citas/Medicamentos)

Este flujo ocurre cuando ya existe **una cita completada** y el enfermero identifica la necesidad de seguimiento.

```mermaid
graph TD
    A[Enfermero completa servicio al paciente] --> B{¿Requiere seguimiento?}
    B -->|NO| Z1[Fin - Solo reporte básico]
    B -->|SÍ| C[Enfermero llena ServiceReport]
    
    C --> D[Marca: requiere_seguimiento = True]
    D --> E[Completa datos del seguimiento]
    
    E --> F{Tipo de Tratamiento}
    
    F -->|Medicamento del Catálogo| G[Selecciona medicamento_catalogo<br/>Ej: Aclasta, Prolia]
    G --> H[Sistema calcula fecha automáticamente<br/>según frecuencia del medicamento]
    
    F -->|Medicamento NO catalogado| I[Enfermero ingresa manualmente:<br/>- medicamento_externo<br/>- fecha_sugerida_seguimiento]
    
    F -->|Servicio Repetitivo| J[Sugiere mismo servicio<br/>Ej: 2da dosis de suero]
    J --> K[Enfermero establece fecha_sugerida_seguimiento]
    
    H --> L[Enfermero agrega notas_seguimiento<br/>Ej: Neurobión cada 24h por 3 días]
    I --> L
    K --> L
    
    L --> M[GUARDAR ServiceReport]
    M --> N[🤖 TRIGGER AUTOMÁTICO en save]
    
    N --> O[Sistema crea AppointmentReminder]
    O --> P[Datos copiados automáticamente:<br/>✓ paciente<br/>✓ servicio_sugerido<br/>✓ enfermero_sugerido mismo<br/>✓ cita_origen vinculada<br/>✓ fecha_limite_sugerida<br/>✓ estado: PENDIENTE<br/>✓ origen: SISTEMA]
    
    P --> Q[Recordatorio visible en Admin Django]
    Q --> R{Gestión del Recordatorio}
    
    R --> S1[Administrador lo visualiza]
    S1 --> S2[Contacta al paciente vía WhatsApp/Phone]
    S2 --> S3{Paciente acepta?}
    
    S3 -->|SÍ| T1[Admin cambia estado a CONTACTADO]
    T1 --> T2[Crea nueva Appointment desde recordatorio]
    T2 --> T3[Marca: es_reagendada = True en Appointment]
    T3 --> T4[Cambia estado recordatorio a AGENDADO]
    
    S3 -->|NO| U1[Cambia estado a CANCELADO]
    
    style N fill:#e1f5ff
    style P fill:#fff4e6
    style Q fill:#e8f5e9
```

### Datos Clave en este Flujo

| Campo | Origen | Valor Ejemplo |
|-------|--------|---------------|
| **paciente** | Copiado de `cita.paciente` | Juan Pérez |
| **servicio_sugerido** | Copiado de `cita.servicio` | Aplicación IM |
| **medicamento_catalogo** | Seleccionado por enfermero | Aclasta (cada 12 meses) |
| **fecha_limite_sugerida** | Auto-calculada O manual | 2025-11-24 (+1 año si es Aclasta) |
| **enfermero_sugerido** | Copiado de `cita.enfermero` | María González |
| **cita_origen** | Referencia a cita | Appointment #123 |
| **origen** | Automático | `SISTEMA` |
| **estado** | Inicial | `PENDIENTE` |

---

## Flujo 2: Recordatorios SIN DATOS (Solicitud desde Cero)

Este flujo maneja **leads puros** que llegan desde landing pages, formularios de contacto, o solicitudes manuales del administrador.

```mermaid
graph TD
    A[Usuario visita Landing Page] --> B[Llena formulario de contacto]
    B --> C[Datos solicitados:<br/>✓ Nombre completo<br/>✓ Email<br/>✓ Teléfono<br/>✓ Cédula opcional<br/>✓ Servicio de interés opcional<br/>✓ Comentarios]
    
    C --> D[Usuario envía formulario]
    
    D --> E{¿Sistema tiene endpoint API?}
    E -->|NO - Opción Temporal| F1[Email con los datos se envía<br/>a admin@holaenfermera.com]
    F1 --> F2[Administrador recibe email]
    F2 --> F3[Admin ingresa manualmente<br/>a Django Admin]
    
    E -->|SÍ - Implementación Futura| G1[POST /api/recordatorios/crear/]
    G1 --> G2[Backend recibe JSON]
    
    F3 --> H[Crear AppointmentReminder manualmente]
    G2 --> I[Sistema crea AppointmentReminder automático]
    
    H --> J[Completar datos mínimos]
    I --> J
    
    J --> K[Datos del recordatorio sin cita:<br/>✓ paciente buscar/crear<br/>✓ servicio_sugerido NULL o seleccionado<br/>✓ medicamento_catalogo NULL<br/>✓ medicamento_externo NULL<br/>✓ fecha_limite_sugerida NULL<br/>✓ notas comentarios del usuario<br/>✓ origen: WEB<br/>✓ estado: PENDIENTE]
    
    K --> L[Recordatorio guardado en sistema]
    
    L --> M{Gestión del Lead}
    M --> N1[Administrador revisa leads nuevos]
    N1 --> N2[Filtra por origen: WEB]
    N2 --> N3[Contacta al paciente]
    
    N3 --> O{Paciente responde?}
    O -->|SÍ| P1[Cambia estado a CONTACTADO]
    P1 --> P2[Define: servicio + fecha + enfermero]
    P2 --> P3[Crea Appointment formal]
    P3 --> P4[Cambia estado a AGENDADO]
    
    O -->|NO| Q1[Marca como CANCELADO]
    
    style G1 fill:#fff4e6
    style I fill:#e8f5e9
    style F1 fill:#ffebee
```

### Datos Clave en este Flujo

| Campo | Origen | Valor Ejemplo |
|-------|--------|---------------|
| **paciente** | Usuario del formulario (buscar/crear) | nueva.persona@gmail.com |
| **servicio_sugerido** | Opcional desde formulario | NULL o "Aplicación IM" |
| **medicamento_catalogo** | No aplica | NULL |
| **medicamento_externo** | No aplica | NULL |
| **fecha_limite_sugerida** | No aplica | NULL |
| **enfermero_sugerido** | No aplica | NULL |
| **cita_origen** | No existe | NULL |
| **origen** | Formulario web | `WEB` |
| **estado** | Inicial | `PENDIENTE` |
| **notas** | Comentarios del usuario | "Me interesa agendar aplicación de Prolia" |

---

## Flujo 3: Enfermero Solicita Recordatorio (Sin Frontend)

Actualmente **NO existe interfaz frontend**, por lo que el enfermero debe usar **Django Admin** para crear recordatorios.

```mermaid
graph TD
    A[Enfermero identifica necesidad<br/>durante o después del servicio] --> B{¿Está llenando ServiceReport?}
    
    B -->|SÍ| C[Usa opción en ServiceReport:<br/>requiere_seguimiento = True]
    C --> D[Completa fecha y notas]
    D --> E[Sistema genera recordatorio AUTOMÁTICO]
    E --> Z1[Fin - Ver Flujo 1]
    
    B -->|NO - Caso excepcional| F[Enfermero accede a Django Admin]
    F --> G[Navega a: Recordatorios y Leads]
    G --> H[Click en: Agregar Recordatorio]
    
    H --> I[Completa formulario manualmente]
    I --> J[Datos requeridos:<br/>✓ Paciente seleccionar<br/>✓ Origen: SISTEMA<br/>✓ Estado: PENDIENTE]
    
    J --> K{¿Tiene medicamento catalogado?}
    K -->|SÍ| L1[Selecciona medicamento_catalogo]
    L1 --> L2[Fecha se calcula AUTO]
    
    K -->|NO| M1[Completa manualmente:<br/>- servicio_sugerido<br/>- fecha_limite_sugerida<br/>- notas]
    
    L2 --> N[Guarda recordatorio]
    M1 --> N
    
    N --> O[Recordatorio creado con:<br/>✓ origen: SISTEMA<br/>✓ estado: PENDIENTE]
    
    O --> P[Administrador gestiona posteriormente]
    
    style F fill:#ffebee
    style H fill:#fff9c4
```

---

## Flujo 4: Paciente Usuario Solicita Recordatorio (Sin Frontend App/Web)

Sin aplicación web o móvil, el paciente **NO puede crear recordatorios directamente**. Debe pasar por canales externos.

```mermaid
graph TD
    A[Paciente necesita recordatorio] --> B{Canal de Contacto}
    
    B -->|WhatsApp| C1[Envía mensaje a número comercial]
    B -->|Llamada| C2[Llama a oficina]
    B -->|Email| C3[Envía correo]
    B -->|Landing Page| C4[Llena formulario web]
    
    C1 --> D[Administrativo recibe solicitud]
    C2 --> D
    C3 --> D
    C4 --> E[Sistema recibe datos vía API/Email]
    
    E --> F{¿Tiene integración automática?}
    F -->|NO| D
    F -->|SÍ| G[Crea AppointmentReminder automático<br/>origen: WEB, estado: PENDIENTE]
    
    D --> H[Administrativo ingresa a Django Admin]
    H --> I[Crea AppointmentReminder manualmente]
    
    I --> J[Datos del recordatorio:<br/>✓ paciente buscar por cédula/email<br/>✓ servicio_sugerido según solicitud<br/>✓ medicamento si aplica<br/>✓ fecha NULL o sugerida por paciente<br/>✓ origen: WEB si es landing<br/>✓ origen: SISTEMA si es llamada<br/>✓ estado: CONTACTADO ya hablaron<br/>✓ notas: detalles de conversación]
    
    G --> K[Recordatorio en sistema]
    J --> K
    
    K --> L[Administración gestiona<br/>y agenda cita formal]
    
    style D fill:#fff4e6
    style H fill:#ffebee
```

---

## Propuesta de Implementación de APIs (Futuro)

Para poder recibir solicitudes **sin intervención manual**, se necesitan estos endpoints:

### API 1: Crear Lead desde Landing Page

```http
POST /api/recordatorios/lead/
Content-Type: application/json

{
  "nombres": "Juan",
  "apellidos": "Pérez",
  "email": "juan@example.com",
  "telefono": "+593987654321",
  "cedula": "1234567890",
  "servicio_interes": "Aplicación IM",
  "comentarios": "Me gustaría agendar aplicación de Prolia"
}
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "recordatorio_id": 45,
  "mensaje": "Solicitud recibida. Nos contactaremos pronto."
}
```

**Lógica Backend:**
1. Buscar o crear `User` con rol `CLIENTE`
2. Crear [AppointmentReminder](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/appointments/models.py#85-162):
   - `origen = 'WEB'`
   - `estado = 'PENDIENTE'`
   - `paciente = usuario_encontrado_o_creado`
   - `servicio_sugerido = Service.objects.get(nombre__icontains=servicio_interes)` si aplica
   - `notas = comentarios`

---

### API 2: Consultar Estado de Recordatorio (Futuro Portal Paciente)

```http
GET /api/recordatorios/mis-recordatorios/
Authorization: Bearer {token_paciente}
```

**Respuesta esperada:**
```json
{
  "recordatorios": [
    {
      "id": 45,
      "servicio": "Aplicación IM",
      "medicamento": "Prolia",
      "fecha_sugerida": "2025-06-15",
      "estado": "CONTACTADO",
      "notas": "Pendiente confirmar horario"
    }
  ]
}
```

---

## Estados del Recordatorio

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE: Recordatorio creado
    
    PENDIENTE --> CONTACTADO: Admin contacta a paciente
    PENDIENTE --> CANCELADO: Paciente no responde/rechaza
    
    CONTACTADO --> AGENDADO: Se crea Appointment formal
    CONTACTADO --> CANCELADO: Paciente finalmente cancela
    
    AGENDADO --> [*]: Proceso completado
    CANCELADO --> [*]: Cerrado sin conversión
```

| Estado | Significado | Acción Siguiente |
|--------|-------------|------------------|
| **PENDIENTE** | Recordatorio creado, aún no gestionado | Contactar al paciente |
| **CONTACTADO** | Ya se habló con el paciente | Coordinar fecha y crear cita |
| **AGENDADO** | Se convirtió en Appointment formal | Ejecutar el servicio |
| **CANCELADO** | Lead descartado o paciente no interesado | Archivar |

---

## Diagrama General del Sistema de Recordatorios

```mermaid
graph TB
    subgraph "ORIGEN: Cierre de Cita"
        A1[Enfermero completa servicio]
        A2[Llena ServiceReport]
        A3[requiere_seguimiento = True]
        A1 --> A2 --> A3
    end
    
    subgraph "ORIGEN: Landing Page / Web"
        B1[Paciente llena formulario]
        B2[Sistema recibe datos]
        B3[origen = WEB]
        B1 --> B2 --> B3
    end
    
    subgraph "ORIGEN: Solicitud Directa"
        C1[Llamada / WhatsApp / Email]
        C2[Admin ingresa manualmente]
        C3[origen = WEB o SISTEMA según caso]
        C1 --> C2 --> C3
    end
    
    A3 --> D[AppointmentReminder creado]
    B3 --> D
    C3 --> D
    
    D --> E{Estado: PENDIENTE}
    
    E --> F[Administración gestiona]
    F --> G{Contactar Paciente}
    
    G -->|Éxito| H[Estado: CONTACTADO]
    G -->|No responde| I[Estado: CANCELADO]
    
    H --> J[Coordinar fecha/hora/enfermero]
    J --> K[Crear Appointment]
    K --> L[Estado: AGENDADO]
    
    L --> M{Vincular}
    M --> N[Appointment.es_reagendada = True]
    M --> O[AppointmentReminder.cita_origen linkado]
    
    style D fill:#e1f5ff
    style H fill:#fff4e6
    style L fill:#e8f5e9
    style I fill:#ffebee
```

---

## Recomendaciones de Implementación

### Corto Plazo (Sin Frontend)

> [!IMPORTANT]
> **Uso exclusivo de Django Admin** hasta que se desarrolle el frontend.

1. **Para Enfermeros:**
   - Capacitar en el uso de [ServiceReport](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/reports/models.py#6-72) con la opción `requiere_seguimiento`
   - Proveer guía de cuándo seleccionar medicamentos del catálogo vs externo
   - Enseñar a calcular fechas para medicamentos no catalogados

2. **Para Administración:**
   - Configurar filtros en Admin Django:
     - Por `estado`
     - Por `origen`
     - Por `fecha_limite_sugerida`
   - Crear vistas personalizadas para priorizar recordatorios próximos a vencer
   - Implementar notificaciones internas (email) cuando se crea un recordatorio nuevo

3. **Para Leads desde Web:**
   - Configurar formulario en landing page que envíe email a admin
   - Template de email estructurado con todos los datos necesarios
   - Admin copia y pega datos en Django Admin

### Mediano Plazo (Con Frontend Básico)

> [!TIP]
> **Portal Web para Administración** que facilite la gestión sin entrar al Django Admin.

1. **Panel de Administración:**
   - Dashboard con recordatorios pendientes
   - Formulario para crear recordatorios manualmente
   - Vista de calendario con fechas sugeridas
   - Botón rápido "Convertir en Cita" desde recordatorio

2. **API Pública:**
   - Endpoint `/api/recordatorios/lead/` para formulario landing page
   - Validaciones automáticas de datos
   - Respuestas JSON estructuradas

### Largo Plazo (App Móvil / Portal Paciente)

> [!NOTE]
> **Aplicación completa** donde pacientes puedan gestionar sus propios recordatorios.

1. **Portal Paciente:**
   - Vista de "Mis Recordatorios"
   - Solicitar nuevo recordatorio
   - Confirmar/Rechazar citas sugeridas
   - Chat directo con administración

2. **App Móvil Enfermero:**
   - Crear recordatorios desde la app después del servicio
   - Sincronización automática con backend
   - Notificaciones push para recordatorios asignados

---

## Ejemplo Práctico Completo

### Caso: Don Carlos necesita Aplicación de Aclasta (cada 12 meses)

#### Paso 1: Servicio Inicial
- **Fecha:** 2024-11-20
- **Servicio:** Aplicación IM - Aclasta (Primera dosis)
- **Enfermera:** María González
- **Paciente:** Carlos Mora (Cédula: 1234567890)

#### Paso 2: Cierre del Servicio
Enfermera María completa el [ServiceReport](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/reports/models.py#6-72):
- ✅ `requiere_seguimiento = True`
- 📅 Selecciona `medicamento_catalogo = Aclasta` (configurado como "cada 12 meses")
- 📝 `notas_seguimiento = "Paciente debe aplicarse próxima dosis en 12 meses"`

#### Paso 3: Sistema Genera Recordatorio Automático
```python
AppointmentReminder.objects.create(
    paciente=carlos_mora,  # Copiado de cita
    servicio_sugerido=aplicacion_im,  # Mismo servicio
    medicamento_catalogo=aclasta,  # Seleccionado por enfermera
    cita_origen=cita_123,  # Referencia a cita original
    enfermero_sugerido=maria_gonzalez,  # Misma enfermera
    fecha_limite_sugerida=date(2025, 11, 20),  # AUTO-CALCULADA: +12 meses
    origen='SISTEMA',
    estado='PENDIENTE',
    notas='Paciente debe aplicarse próxima dosis en 12 meses'
)
```

#### Paso 4: Gestión Administrativa (Octubre 2025)
Admin revisa recordatorios próximos (1 mes antes):
- Filtra: `fecha_limite_sugerida` entre 2025-10-20 y 2025-11-20
- Ve recordatorio de Don Carlos
- Contacta vía WhatsApp: "Don Carlos, es momento de su próxima dosis de Aclasta"

#### Paso 5: Conversión a Cita
Don Carlos acepta:
- Admin cambia estado a `CONTACTADO`
- Crea nueva [Appointment](file:///c:/Users/danie/Documents/PROYECTOS_PROG/HOLAENFERMERA/HolaEnfermera/CoreApps/appointments/models.py#14-83):
  - `fecha = 2025-11-18` (coordinada con paciente)
  - `hora_inicio = 10:00`
  - `enfermero = maria_gonzalez` (si está disponible)
  - `es_reagendada = True` (marca que viene de recordatorio)
- Cambia estado del recordatorio a `AGENDADO`

#### Paso 6: ¡Ciclo se repite!
Cuando María complete el servicio en Nov 2025, nuevamente llenará el reporte y generará otro recordatorio para Nov 2026. 🔄

---

## Conclusión

El sistema de recordatorios de HolaEnfermera está **bien diseñado** para funcionar con o sin frontend, usando dos flujos principales:

1. **CON DATOS:** Automatización completa desde citas existentes (ideal para tratamientos continuos)
2. **SIN DATOS:** Captación manual de leads desde web o contactos externos

**Estado Actual:** Funcional 100% vía Django Admin  
**Próximos Pasos:** APIs para formularios + Panel administrativo básico  
**Visión Futura:** Portal paciente + App móvil enfermero

