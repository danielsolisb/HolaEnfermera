# Guía de Implementación: Importación Masiva de Pacientes desde Excel

Este documento detalla el proceso para implementar y ejecutar el script de carga masiva de pacientes y recordatorios en el sistema **HolaEnfermera**.

El script (`import_patients.py`) se encarga de:

1.  **Sanear Datos:** Corrige cédulas incompletas, separa nombres/apellidos y gestiona teléfonos múltiples.
2.  **Crear Usuarios:** Genera usuarios automáticamente. Si no tienen cédula, crea un ID temporal. Si no tienen correo, genera uno ficticio (`cedula@holaenfermera.com`).
3.  **Gestionar Perfiles:** Crea el `CustomerProfile` asociado con la ciudad y observaciones.
4.  **Generar Recordatorios:** Lee las columnas de "Primera Dosis", "Segunda Dosis", etc., y crea múltiples recordatorios (`AppointmentReminder`) agendados a futuro.

---

## 1. Requisitos Previos

El script utiliza librerías especializadas para leer Excel y manejar fechas. Debes instalarlas en tu entorno virtual:

```bash
pip install pandas openpyxl

# Estructura de carpetas

CoreApps/
└── users/
    └── management/
        ├── __init__.py
        └── commands/
            ├── __init__.py
            └── import_patients.py  <-- (Crear este archivo)


# Código del script

import pandas as pd
import re
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings

# Importamos los modelos del proyecto
from CoreApps.users.models import User, CustomerProfile
from CoreApps.appointments.models import AppointmentReminder
from CoreApps.services.models import Medication, Service

class Command(BaseCommand):
    help = 'Importar pacientes y recordatorios desde Excel con saneamiento automático e inteligencia de fechas.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Ruta al archivo Excel (.xlsx)')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        self.stdout.write(self.style.WARNING(f'Iniciando lectura de: {file_path} ...'))

        try:
            # Leemos el Excel con Pandas
            df = pd.read_excel(file_path)
            # Limpiamos espacios en los nombres de las columnas
            df.columns = df.columns.str.strip()

            total_rows = len(df)
            self.stdout.write(f'Filas detectadas: {total_rows}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error leyendo archivo: {e}'))
            return

        count_creados = 0
        count_actualizados = 0
        count_recordatorios = 0

        # --- ITERACIÓN FILA POR FILA ---
        for index, row in df.iterrows():
            try:
                with transaction.atomic(): # Transacción atómica por fila

                    # =================================================
                    # FASE A: SANEAMIENTO DE DATOS DEL PACIENTE
                    # =================================================

                    # 1. CÉDULA DE IDENTIDAD
                    raw_cedula = str(row.get('CEDULA /RUC', '')).strip()

                    # Detectar valores vacíos o inválidos de Excel
                    if raw_cedula.lower() in ['nan', '0', '0.0', 'none', '']:
                        # CASO: Sin Cédula -> Generar ID Temporal
                        timestamp = int(time.time())
                        cedula_final = f"TMP-{timestamp}-{index}"
                        es_temporal = True
                    else:
                        # Limpiar decimales (.0) si existen
                        cedula_final = raw_cedula.split('.')[0]

                        # Corrección de ceros a la izquierda (Caso común en Ecuador: 9 dígitos -> 10 dígitos)
                        if len(cedula_final) == 9 and cedula_final.isdigit():
                            cedula_final = "0" + cedula_final
                        es_temporal = False

                    # 2. NOMBRES Y APELLIDOS
                    raw_nombre = str(row.get('NOMBRE DEL CLIENTE', 'Paciente Sin Nombre')).strip()
                    # Quitar prefijos comunes (ruido)
                    raw_nombre = re.sub(r'^(SRA\.?|SR\.?|DR\.?|DRA\.?)\s+', '', raw_nombre, flags=re.IGNORECASE)

                    # Separar Nombres y Apellidos
                    parts = raw_nombre.split(' ', 1) # Dividir en el primer espacio
                    first_name = parts[0].strip()
                    last_name = parts[1].strip() if len(parts) > 1 else "." # Apellido punto si no existe

                    # 3. TELÉFONOS (Manejo de múltiples números)
                    raw_telefono = str(row.get('TELEFONO', '')).strip().replace('.0', '')
                    telefono_principal = ""
                    telefono_secundario = ""

                    if raw_telefono and raw_telefono.lower() != 'nan':
                        # Separar si hay barra "/"
                        tels = str(raw_telefono).split('/')

                        # Procesar Principal
                        t1 = re.sub(r'[^\d]', '', tels[0])
                        if len(t1) == 9: t1 = "0" + t1 # Agregar cero inicial
                        telefono_principal = t1

                        # Procesar Secundario (si existe)
                        if len(tels) > 1:
                            t2 = re.sub(r'[^\d]', '', tels[1])
                            if len(t2) == 9: t2 = "0" + t2
                            telefono_secundario = f" / Alt: {t2}"

                    # 4. EMAIL (Generación de Ficticio si falta)
                    raw_email = str(row.get('CORREO', '')).strip()
                    if not raw_email or raw_email.lower() == 'nan':
                        email_final = f"{cedula_final}@holaenfermera.com"
                    else:
                        email_final = raw_email

                    # =================================================
                    # FASE B: PERSISTENCIA DEL USUARIO (Upsert)
                    # =================================================

                    # Buscamos por cédula (que es el username único)
                    user = User.objects.filter(cedula=cedula_final).first()

                    if not user:
                        # Crear Nuevo Usuario
                        user = User.objects.create_user(
                            username=cedula_final,
                            email=email_final,
                            password=cedula_final, # Contraseña inicial = Cédula
                            first_name=first_name,
                            last_name=last_name,
                            cedula=cedula_final,
                            telefono=telefono_principal,
                            rol=User.Roles.CLIENTE
                        )
                        count_creados += 1
                    else:
                        # Actualizar Existente (Solo datos de contacto)
                        if telefono_principal:
                            user.telefono = telefono_principal
                        user.first_name = first_name
                        user.last_name = last_name
                        # No sobreescribimos email si ya existe para no dañar logins actuales
                        user.save()
                        count_actualizados += 1

                    # Crear o Actualizar el Perfil de Cliente
                    perfil, _ = CustomerProfile.objects.get_or_create(user=user)

                    # Datos adicionales al perfil
                    ciudad = str(row.get('CIUDAD', '')).strip()
                    if ciudad and ciudad.lower() != 'nan':
                        perfil.ciudad = ciudad

                    # Construir observaciones del perfil
                    observaciones_perfil = []
                    if telefono_secundario:
                        observaciones_perfil.append(f"Telf. Secundario: {telefono_secundario}")
                    if es_temporal:
                        observaciones_perfil.append("⚠️ CÉDULA PENDIENTE (ID Temporal generado en importación)")

                    # Guardar observaciones sin borrar las anteriores si existen
                    if observaciones_perfil:
                        texto_obs = " | ".join(observaciones_perfil)
                        if perfil.alergias: # Usamos el campo 'alergias' como notas generales por ahora
                            perfil.alergias = f"{perfil.alergias} | {texto_obs}"
                        else:
                            perfil.alergias = texto_obs

                    perfil.save()

                    # =================================================
                    # FASE C: INTERPRETACIÓN DEL PRODUCTO
                    # =================================================
                    raw_producto = str(row.get('PRODUCTO', '')).strip()
                    med_obj = None
                    service_obj = None
                    med_externo = None

                    if raw_producto and raw_producto.lower() != 'nan':
                        # 1. Buscar en Medicamentos (Coincidencia parcial insensible a mayúsculas)
                        med_match = Medication.objects.filter(nombre__icontains=raw_producto).first()
                        if med_match:
                            med_obj = med_match
                        else:
                            # 2. Buscar en Servicios
                            serv_match = Service.objects.filter(nombre__icontains=raw_producto).first()
                            if serv_match:
                                service_obj = serv_match
                            else:
                                # 3. Texto libre
                                med_externo = raw_producto

                    # =================================================
                    # FASE D: CONSTRUCCIÓN DE LA "NOTA MAESTRA"
                    # =================================================
                    raw_enfermero = str(row.get('ENFERMERO', '')).replace('nan', '')
                    raw_comentarios = str(row.get('COMENTARIOS', '')).replace('nan', '')
                    raw_compro = str(row.get('COMPRO', '')).replace('nan', '')
                    raw_fecha_atencion = str(row.get('FECHA DE ATENCION', '')).replace('nan', '')

                    # Nota base con el historial
                    nota_base = (
                        f"IMPORTACIÓN | "
                        f"Atención Base: {raw_fecha_atencion} | "
                        f"Enfermero Original: {raw_enfermero} | "
                        f"Comentarios: {raw_comentarios} | "
                        f"Compró: {raw_compro}"
                    )

                    # =================================================
                    # FASE E: CREACIÓN DE RECORDATORIOS (Desdoblamiento)
                    # =================================================

                    # Mapeo de columnas del Excel a etiquetas lógicas
                    columnas_dosis = [
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(PRIMERA DOSIS)', '1ra Dosis'),
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(SEGUNDA DOSIS)', '2da Dosis'),
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(TERCERA DOSIS)', '3ra Dosis'),
                    ]

                    for col_name, etiqueta in columnas_dosis:
                        # Obtenemos el valor de la celda
                        fecha_raw = row.get(col_name)

                        # Intentamos convertirlo a fecha real
                        fecha_valida = self.parse_fecha_rara(fecha_raw)

                        if fecha_valida:
                            # Crear Recordatorio en Base de Datos
                            AppointmentReminder.objects.create(
                                paciente=user,
                                medicamento_catalogo=med_obj,
                                # Si encontramos un servicio pero el modelo reminder no tiene campo fk a servicio,
                                # guardamos el nombre en texto externo para no perder el dato.
                                medicamento_externo=med_externo or (service_obj.nombre if service_obj else None),
                                fecha_limite_sugerida=fecha_valida,
                                notas=f"[{etiqueta}] {nota_base}",
                                estado='PENDIENTE',
                                origen='SISTEMA'
                            )
                            count_recordatorios += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error procesando fila {index + 2}: {e}"))
                continue # Continuamos con la siguiente fila a pesar del error

        # --- RESUMEN FINAL ---
        self.stdout.write(self.style.SUCCESS(f"\n=== PROCESO TERMINADO ==="))
        self.stdout.write(f"Pacientes Nuevos Creados: {count_creados}")
        self.stdout.write(f"Pacientes Existentes Actualizados: {count_actualizados}")
        self.stdout.write(f"Recordatorios Agendados: {count_recordatorios}")

    def parse_fecha_rara(self, fecha_valor):
        """
        Intenta descifrar formatos de fecha irregulares del Excel.
        Retorna un objeto date de Python o None si falla.
        """
        if pd.isna(fecha_valor) or str(fecha_valor).strip() == '' or str(fecha_valor).lower() == 'nan':
            return None

        # Si Pandas ya lo reconoció como fecha (Timestamp), lo usamos directo
        if isinstance(fecha_valor, (datetime, pd.Timestamp)):
            return fecha_valor.date()

        fecha_str = str(fecha_valor).strip()

        # Lista de formatos posibles encontrados en el análisis
        formatos = [
            '%d %m %Y',   # "30 6 2025"
            '%Y-%m-%d',   # "2025-07-03" (ISO)
            '%m-%d-%Y',   # "11-27-2024" (EEUU)
            '%d/%m/%Y',   # "30/06/2025" (Latino)
            '%Y/%m/%d',   # "2025/07/03"
            '%d-%m-%Y',   # "30-06-2025"
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(fecha_str, fmt).date()
            except ValueError:
                continue

        return None # Fecha no entendible


# Ejecución del script


python manage.py import_patients "ARCHIVO CLIENTES RECURRENTES.xlsx"
```
