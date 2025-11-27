import pandas as pd
import re
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings

# Importamos tus modelos
from CoreApps.users.models import User, CustomerProfile
from CoreApps.appointments.models import AppointmentReminder
from CoreApps.services.models import Medication, Service

class Command(BaseCommand):
    help = 'Importar pacientes y recordatorios desde Excel (Saneamiento Automático)'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Ruta al archivo Excel (.xlsx)')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        self.stdout.write(self.style.WARNING(f'Iniciando lectura de: {file_path} ...'))

        try:
            # Leemos el Excel con Pandas (detecta automáticamente los tipos)
            df = pd.read_excel(file_path)
            # Limpiamos espacios en nombres de columnas
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
                with transaction.atomic(): # Si algo falla en esta fila, no se guarda nada de esta fila
                    
                    # =================================================
                    # FASE A: SANEAMIENTO DE PACIENTE
                    # =================================================
                    
                    # 1. CÉDULA
                    raw_cedula = str(row.get('CEDULA /RUC', '')).strip()
                    # Limpieza básica de "nan", "0", "0.0" que deja pandas
                    if raw_cedula.lower() in ['nan', '0', '0.0', 'None', '']:
                        # CASO: Sin Cédula -> Generar TMP
                        timestamp = int(time.time())
                        cedula_final = f"TMP-{timestamp}-{index}"
                        es_temporal = True
                    else:
                        # Eliminar decimales si vinieron (ej: 999.0 -> 999)
                        cedula_final = raw_cedula.split('.')[0]
                        # Corrección de ceros (Si tiene 9, asumimos falta el 0 inicial)
                        if len(cedula_final) == 9 and cedula_final.isdigit():
                            cedula_final = "0" + cedula_final
                        es_temporal = False

                    # 2. NOMBRES Y APELLIDOS
                    raw_nombre = str(row.get('NOMBRE DEL CLIENTE', 'Paciente Sin Nombre')).strip()
                    # Quitar prefijos comunes
                    raw_nombre = re.sub(r'^(SRA\.?|SR\.?|DR\.?|DRA\.?)\s+', '', raw_nombre, flags=re.IGNORECASE)
                    
                    parts = raw_nombre.split(' ', 1) # Dividir solo en el primer espacio
                    first_name = parts[0].strip()
                    last_name = parts[1].strip() if len(parts) > 1 else "." # Apellido punto si no hay

                    # 3. TELÉFONOS (Desdoblamiento)
                    raw_telefono = str(row.get('TELEFONO', '')).strip().replace('.0', '') # Quitar .0 de excel
                    telefono_principal = ""
                    telefono_secundario = ""

                    if raw_telefono and raw_telefono.lower() != 'nan':
                        tels = str(raw_telefono).split('/')
                        # Limpiar principal
                        t1 = re.sub(r'[^\d]', '', tels[0])
                        if len(t1) == 9: t1 = "0" + t1
                        telefono_principal = t1

                        # Limpiar secundario si existe
                        if len(tels) > 1:
                            t2 = re.sub(r'[^\d]', '', tels[1])
                            if len(t2) == 9: t2 = "0" + t2
                            telefono_secundario = f" / Alt: {t2}"

                    # 4. EMAIL (Ficticio si falta)
                    raw_email = str(row.get('CORREO', '')).strip()
                    if not raw_email or raw_email.lower() == 'nan':
                        email_final = f"{cedula_final}@holaenfermera.com"
                    else:
                        email_final = raw_email

                    # =================================================
                    # FASE B: PERSISTENCIA USUARIO (Upsert)
                    # =================================================
                    user_created = False
                    
                    # Buscamos por cédula (que es el username)
                    user = User.objects.filter(cedula=cedula_final).first()

                    if not user:
                        # Crear Nuevo
                        user = User.objects.create_user(
                            username=cedula_final,
                            email=email_final,
                            password=cedula_final, # Clave = Cédula
                            first_name=first_name,
                            last_name=last_name,
                            cedula=cedula_final,
                            telefono=telefono_principal,
                            rol=User.Roles.CLIENTE
                        )
                        user_created = True
                        count_creados += 1
                    else:
                        # Actualizar Existente (Opcional, actualizamos contacto)
                        if telefono_principal:
                            user.telefono = telefono_principal
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                        count_actualizados += 1

                    # Crear/Actualizar Perfil
                    perfil, _ = CustomerProfile.objects.get_or_create(user=user)
                    
                    # Guardar datos extra en observaciones del perfil
                    ciudad = str(row.get('CIUDAD', '')).strip()
                    if ciudad and ciudad.lower() != 'nan':
                        perfil.ciudad = ciudad
                    
                    observaciones_perfil = []
                    if telefono_secundario:
                        observaciones_perfil.append(telefono_secundario)
                    if es_temporal:
                        observaciones_perfil.append("⚠️ CÉDULA PENDIENTE (Generada por Sistema)")
                    
                    if observaciones_perfil:
                        perfil.alergias = f"{perfil.alergias or ''} | {' '.join(observaciones_perfil)}"
                    
                    perfil.save()

                    # =================================================
                    # FASE C: INTERPRETACIÓN DEL PRODUCTO
                    # =================================================
                    raw_producto = str(row.get('PRODUCTO', '')).strip()
                    med_obj = None
                    service_obj = None
                    med_externo = None

                    if raw_producto and raw_producto.lower() != 'nan':
                        # Intentar buscar Medicamento (búsqueda insensible a mayúsculas)
                        med_match = Medication.objects.filter(nombre__icontains=raw_producto).first()
                        if med_match:
                            med_obj = med_match
                        else:
                            # Intentar buscar Servicio
                            serv_match = Service.objects.filter(nombre__icontains=raw_producto).first()
                            if serv_match:
                                service_obj = serv_match
                            else:
                                # Texto libre
                                med_externo = raw_producto

                    # =================================================
                    # FASE D: NOTAS MAESTRAS
                    # =================================================
                    raw_enfermero = str(row.get('ENFERMERO', '')).replace('nan', '')
                    raw_comentarios = str(row.get('COMENTARIOS', '')).replace('nan', '')
                    raw_compro = str(row.get('COMPRO', '')).replace('nan', '')
                    raw_fecha_atencion = str(row.get('FECHA DE ATENCION', '')).replace('nan', '')

                    nota_base = (
                        f"IMPORTACIÓN | "
                        f"Atendido el: {raw_fecha_atencion} | "
                        f"Por: {raw_enfermero} | "
                        f"Nota Original: {raw_comentarios} | "
                        f"Compró: {raw_compro}"
                    )

                    # =================================================
                    # FASE E: CREACIÓN DE RECORDATORIOS (Desdoblamiento)
                    # =================================================
                    
                    # Lista de columnas de fechas futuras en tu Excel
                    # Ajusta los nombres EXACTOS según tu Excel real
                    columnas_dosis = [
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(PRIMERA DOSIS)', 'Primera Dosis'),
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(SEGUNDA DOSIS)', 'Segunda Dosis'),
                        ('FECHA DE PROXIMA DOSIS O LLAMADA DE SGTO(TERCERA DOSIS)', 'Tercera Dosis'), 
                    ]

                    for col_name, etiqueta in columnas_dosis:
                        fecha_raw = row.get(col_name)
                        fecha_valida = self.parse_fecha_rara(fecha_raw)

                        if fecha_valida:
                            # Crear Recordatorio
                            AppointmentReminder.objects.create(
                                paciente=user,
                                medicamento_catalogo=med_obj,
                                # Si tenemos servicio pero el modelo reminder no tiene campo servicio, lo ponemos en texto externo
                                medicamento_externo=med_externo or (service_obj.nombre if service_obj else None),
                                fecha_limite_sugerida=fecha_valida,
                                notas=f"{etiqueta} - {nota_base}",
                                estado='PENDIENTE',
                                origen='SISTEMA' 
                            )
                            count_recordatorios += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error en fila {index + 2}: {e}"))
                continue # Seguimos con la siguiente fila

        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS(f"\n=== PROCESO TERMINADO ==="))
        self.stdout.write(f"Pacientes Nuevos: {count_creados}")
        self.stdout.write(f"Pacientes Actualizados: {count_actualizados}")
        self.stdout.write(f"Recordatorios Generados: {count_recordatorios}")

    def parse_fecha_rara(self, fecha_valor):
        """
        Intenta descifrar formatos de fecha locos. Retorna objeto date o None.
        """
        if pd.isna(fecha_valor) or str(fecha_valor).strip() == '':
            return None
        
        # Si Pandas ya lo reconoció como fecha (Timestamp)
        if isinstance(fecha_valor, (datetime, pd.Timestamp)):
            return fecha_valor.date()

        fecha_str = str(fecha_valor).strip()
        
        # Lista de formatos a probar (Basado en tu análisis)
        formatos = [
            '%d %m %Y',   # "30 6 2025"
            '%Y-%m-%d',   # "2025-07-03"
            '%m-%d-%Y',   # "11-27-2024"
            '%d/%m/%Y',   # "30/06/2025"
            '%Y/%m/%d',   # "2025/07/03"
            '%d-%m-%Y',   # "30-06-2025"
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(fecha_str, fmt).date()
            except ValueError:
                continue
        
        return None # No se pudo entender la fecha