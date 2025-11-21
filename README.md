# HolaEnfermera
Sistema de gestión y agendamiento de reservas para servicios de Hola Enfermera


Este sistema tendra como objetivo ser un sistema de agendamiento de citas para los servicios de Hola Enfermera, el cual permitira a los usuarios agendar citas con los profesionales de la salud, y a los mismos gestionar sus citas.
Como administradores nos permitiran saber detalles como los servicios y quien fue que lo atendio.



Resumen General
El proyecto HolaEnfermera es una aplicación web monolítica construida con Django 4.2.4. Su objetivo principal es la gestión y agendamiento de citas médicas (enfermería) a domicilio o en local. La arquitectura es modular, organizando la lógica de negocio en aplicaciones separadas dentro del directorio CoreApps.

Stack Tecnológico
Backend: Python 3.x, Django 4.2.4
Base de Datos: SQLite (Configuración actual), compatible con PostgreSQL/MySQL.
Frontend: Django Templates (Server-Side Rendering) con django-select2 y widget-tweaks.
Integraciones:
WhatsApp: WASenderAPI / WAAPI.
Mapas: Google Maps API.
Email: SMTP (Gmail).
PDFs: ReportLab.
Imágenes: Pillow.
Arquitectura y Patrones
Modularidad: El uso de CoreApps (users, appointments, services, etc.) demuestra una buena separación de dominios.
Service Layer: Se identificó un patrón de "Capa de Servicios" (e.g., 
AvailabilityService
, 
BookingManager
 en 
appointments/services.py
). Esto es una excelente práctica que mantiene las vistas y modelos más limpios y encapsula la lógica compleja.
Modelos Personalizados: Uso correcto de AUTH_USER_MODEL.
Seguridad: Manejo de secretos vía variables de entorno (python-dotenv).
Puntos Fuertes (Pros) ✅
Lógica de Negocio Desacoplada: La lógica compleja de disponibilidad y reservas está aislada en servicios, facilitando su mantenimiento y reutilización.
Integridad de Datos: Uso de transaction.atomic para asegurar que las reservas complejas (crear usuario + crear cita) sean atómicas.
Escalabilidad Modular: La estructura de carpetas permite agregar nuevas funcionalidades (e.g., payments, chat) sin afectar el núcleo existente.
Estándares Modernos: Uso de versiones recientes de librerías y prácticas de seguridad estándar.