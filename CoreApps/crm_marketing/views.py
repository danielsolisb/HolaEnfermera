import pandas as pd
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView, DetailView, FormView, UpdateView, View, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import CrmContact, Farmacia, Etiqueta, ProductoCRM
from CoreApps.main.models import Ciudad

class GestorCrmMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Solo permite acceso a staff o superusuarios al CRM"""
    def test_func(self):
        return self.request.user.is_staff

class CrmContactListView(GestorCrmMixin, ListView):
    model = CrmContact
    template_name = 'crm_marketing/contact_list.html'
    context_object_name = 'contactos'
    
    def get_queryset(self):
        qs = super().get_queryset()
        # Filtros ampliados (Soportando multi-select con getlist)
        ciudades_ids = self.request.GET.getlist('ciudad')
        farmacias_ids = self.request.GET.getlist('farmacia')
        productos_ids = self.request.GET.getlist('medicamento')
        etiquetas_ids = self.request.GET.getlist('etiqueta')
        edad_min = self.request.GET.get('edad_min')
        edad_max = self.request.GET.get('edad_max')
        
        if ciudades_ids and '' not in ciudades_ids:
            qs = qs.filter(ciudad_id__in=ciudades_ids)
        if farmacias_ids and '' not in farmacias_ids:
            qs = qs.filter(farmacia_origen_id__in=farmacias_ids)
        if productos_ids and '' not in productos_ids:
            qs = qs.filter(medicamentos_comprados__id__in=productos_ids).distinct()
        if etiquetas_ids and '' not in etiquetas_ids:
            qs = qs.filter(etiquetas__id__in=etiquetas_ids).distinct()
            
        # Filtro de Edad calculando con Datetime
        if edad_min or edad_max:
            import datetime
            hoy = datetime.date.today()
            if edad_min:
                try:
                    fecha_tope_min = datetime.date(hoy.year - int(edad_min), hoy.month, hoy.day)
                    qs = qs.filter(fecha_nacimiento__lte=fecha_tope_min)
                except ValueError:
                    pass
            if edad_max:
                try:
                    fecha_tope_max = datetime.date(hoy.year - int(edad_max), hoy.month, hoy.day)
                    qs = qs.filter(fecha_nacimiento__gte=fecha_tope_max)
                except ValueError:
                    pass
                    
        return qs.select_related('ciudad', 'farmacia_origen').prefetch_related('etiquetas', 'medicamentos_comprados')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ciudades'] = Ciudad.objects.filter(activa=True)
        context['farmacias'] = Farmacia.objects.all()
        context['productos'] = ProductoCRM.objects.all()
        context['etiquetas'] = Etiqueta.objects.all()
        return context

class CrmContactDetailView(GestorCrmMixin, DetailView):
    model = CrmContact
    template_name = 'crm_marketing/contact_detail.html'
    context_object_name = 'contacto'

class CrmContactUpdateView(GestorCrmMixin, UpdateView):
    model = CrmContact
    template_name = 'crm_marketing/contact_form.html'
    fields = [
        'nombres', 'apellidos', 'cedula', 'telefono', 'email', 
        'fecha_nacimiento', 'es_edad_estimada', 'ciudad', 'zona_barrio', 
        'farmacia_origen', 'etiquetas', 'medicamentos_comprados'
    ]
    
    def get_success_url(self):
        messages.success(self.request, "Contacto actualizado correctamente.")
        return reverse_lazy('crm_marketing:contact_detail', kwargs={'pk': self.object.pk})

class CrmContactDeleteView(GestorCrmMixin, DeleteView):
    model = CrmContact
    success_url = reverse_lazy('crm_marketing:contact_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Contacto eliminado correctamente.")
        return super().delete(request, *args, **kwargs)

class AssignTagsBulkView(GestorCrmMixin, View):
    """Vista que recibe filtros por GET/POST y una etiqueta, y se la asigna a todos los contactos resultantes"""
    def post(self, request, *args, **kwargs):
        etiqueta_id = request.POST.get('etiqueta_id')
        contact_ids = request.POST.getlist('contact_ids') # IDs seleccionados por checkbox
        
        # Filtros (para fallback si no hay contact_ids o para redirección)
        ciudades_ids = request.POST.getlist('ciudad')
        farmacias_ids = request.POST.getlist('farmacia')
        productos_ids = request.POST.getlist('medicamento')
        filtros_etiquetas_ids = request.POST.getlist('etiqueta')
        edad_min = request.POST.get('edad_min')
        edad_max = request.POST.get('edad_max')

        if not etiqueta_id:
            messages.error(request, "Debes seleccionar una etiqueta.")
            return redirect('crm_marketing:contact_list')

        # Si el usuario seleccionó contactos específicos por checkbox, usamos esos.
        # Si no, aplicamos a todo el resultado del filtro actual.
        if contact_ids:
            qs = CrmContact.objects.filter(id__in=contact_ids)
        else:
            qs = CrmContact.objects.all()
            if ciudades_ids and '' not in ciudades_ids:
                qs = qs.filter(ciudad_id__in=ciudades_ids)
            if farmacias_ids and '' not in farmacias_ids:
                qs = qs.filter(farmacia_origen_id__in=farmacias_ids)
            if productos_ids and '' not in productos_ids:
                qs = qs.filter(medicamentos_comprados__id__in=productos_ids)
            if filtros_etiquetas_ids and '' not in filtros_etiquetas_ids:
                qs = qs.filter(etiquetas__id__in=filtros_etiquetas_ids)
            
            qs = qs.distinct()
            
        if edad_min or edad_max:
            import datetime
            hoy = datetime.date.today()
            if edad_min:
                try:
                    fecha_tope_min = datetime.date(hoy.year - int(edad_min), hoy.month, hoy.day)
                    qs = qs.filter(fecha_nacimiento__lte=fecha_tope_min)
                except ValueError:
                    pass
            if edad_max:
                try:
                    fecha_tope_max = datetime.date(hoy.year - int(edad_max), hoy.month, hoy.day)
                    qs = qs.filter(fecha_nacimiento__gte=fecha_tope_max)
                except ValueError:
                    pass

        try:
            etiqueta = Etiqueta.objects.get(id=etiqueta_id)
            total = qs.count()
            # Asignación masiva m2m es iterativa o requiere loop (debido a validaciones M2M)
            # Para pocos miles es rápido
            for contacto in qs:
                contacto.etiquetas.add(etiqueta)
            
            messages.success(request, f"¡Éxito! Se asignó la etiqueta '{etiqueta.nombre}' a {total} prospectos.")
        except Etiqueta.DoesNotExist:
            messages.error(request, "La etiqueta seleccionada no existe.")

        # Reconstruir la URL de origen con los mismos filtros
        url = reverse_lazy('crm_marketing:contact_list')
        query_params = []
        for cid in ciudades_ids: 
            if cid: query_params.append(f"ciudad={cid}")
        for fid in farmacias_ids: 
            if fid: query_params.append(f"farmacia={fid}")
        for pid in productos_ids: 
            if pid: query_params.append(f"medicamento={pid}")
        for eid in filtros_etiquetas_ids: 
            if eid: query_params.append(f"etiqueta={eid}")
        if edad_min: query_params.append(f"edad_min={edad_min}")
        if edad_max: query_params.append(f"edad_max={edad_max}")
        
        if query_params:
            url = f"{url}?{'&'.join(query_params)}"
        
        return redirect(url)

class ContactImportView(GestorCrmMixin, FormView):
    template_name = 'crm_marketing/import_data.html'
    success_url = reverse_lazy('crm_marketing:contact_list')

    # No usamos form class, manejamos el request directamente en post para simplificar file upload
    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "Por favor sube un archivo Excel válido.")
            return redirect('crm_marketing:import_data')
        
        try:
            df = pd.read_excel(excel_file)
            
            nuevos = 0
            actualizados = 0
            
            # Limpiamos NaN a strings vacíos o None
            df = df.where(pd.notnull(df), None)
            
            for index, row in df.iterrows():
                # Campos mandatorios: telefono ahora pasa a ser recomendado, pero cedula manda. 
                # Sin embargo, exigiremos telefono porque es para WhatsApp
                telefono = str(row.get('TELEFONO', '')).strip()
                
                # Omitir si está vacío o si es uno de los números de ejemplo exactos de la plantilla
                if not telefono or telefono == 'None' or telefono in ['0991234567', '0987654321']:
                    continue
                
                # Cédula como identificador principal (Si no hay cédula, usaremos el mismo teléfono como fallback para evitar fallos si el Excel viene sin cédulas)
                cedula = str(row.get('CEDULA', '')).strip()
                if not cedula or cedula == 'None':
                    cedula = telefono # Fallback de identificación

                # Limpiador básico de teléfono a formato +593...
                if telefono.startswith('09'):
                    telefono = '+593' + telefono[1:]
                elif telefono.startswith('9'):
                    telefono = '+593' + telefono
                
                nombres = str(row.get('NOMBRES', '')).strip()
                apellidos = str(row.get('APELLIDOS', '')).strip()
                if nombres == 'None': nombres = 'Desconocido'
                if apellidos == 'None': apellidos = ''
                
                # Procesamiento de Correo y Dirección
                email = str(row.get('EMAIL', '')).strip()
                if email == 'None': email = ''
                
                direccion = str(row.get('DIRECCION', '')).strip()
                if direccion == 'None': direccion = ''
                
                # Procesamiento de Ciudad
                ciudad_nombre = str(row.get('CIUDAD', '')).strip()
                ciudad_obj = None
                if ciudad_nombre and ciudad_nombre != 'None':
                    ciudad_obj, _ = Ciudad.objects.get_or_create(nombre__iexact=ciudad_nombre, defaults={'nombre': ciudad_nombre.title()})
                
                # Procesamiento de Farmacia
                farmacia_codigo = str(row.get('CODIGO_FARMACIA', '')).strip()
                farmacia_obj = None
                if farmacia_codigo and farmacia_codigo != 'None':
                    farmacia_obj, _ = Farmacia.objects.get_or_create(codigo=farmacia_codigo, defaults={'nombre': f"Farmacia {farmacia_codigo}", 'ciudad': ciudad_obj})
                
                # Procesamiento de Edad o Fecha de nacimiento
                import datetime
                fecha_nac = None
                es_estimada = False
                
                fecha_excel = row.get('FECHA_NACIMIENTO', None)
                edad_excel = row.get('EDAD', None)
                
                if pd.notnull(fecha_excel) and str(fecha_excel).strip() != 'None' and str(fecha_excel).strip() != '':
                    try:
                        # Puede que venga como datetime de excel o string
                        if isinstance(fecha_excel, datetime.datetime):
                            fecha_nac = fecha_excel.date()
                        else:
                            fecha_nac = pd.to_datetime(fecha_excel).date()
                    except:
                        pass
                
                if not fecha_nac and pd.notnull(edad_excel) and str(edad_excel).strip() != 'None' and str(edad_excel).strip() != '':
                    try:
                        edad_val = int(edad_excel)
                        es_estimada = True
                        hoy = datetime.date.today()
                        fecha_nac = datetime.date(hoy.year - edad_val, 1, 1) # Asumimos 1 Enero
                    except:
                        pass

                contacto, created = CrmContact.objects.update_or_create(
                    cedula=cedula,
                    defaults={
                        'telefono': telefono,
                        'nombres': nombres,
                        'apellidos': apellidos,
                        'email': email if email else None,
                        'zona_barrio': direccion if direccion else None,
                        'ciudad': ciudad_obj,
                        'farmacia_origen': farmacia_obj,
                        'fecha_nacimiento': fecha_nac,
                        'es_edad_estimada': es_estimada
                    }
                )
                
                if created: nuevos += 1
                else: actualizados += 1
                
                # Procesar medicamento (ProductoCRM)
                medicamento_nombre = str(row.get('MEDICAMENTO', '')).strip()
                if medicamento_nombre and medicamento_nombre != 'None':
                    producto_obj, _ = ProductoCRM.objects.get_or_create(nombre__iexact=medicamento_nombre, defaults={'nombre': medicamento_nombre.title()})
                    contacto.medicamentos_comprados.add(producto_obj)

            messages.success(request, f"¡Importación exitosa! {nuevos} contactos creados, {actualizados} actualizados.")
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return redirect('crm_marketing:import_data')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


from io import BytesIO
from django.http import HttpResponse

class DownloadImportTemplateView(GestorCrmMixin, View):
    """Genera y descarga un Excel de plantilla en memoria"""
    def get(self, request, *args, **kwargs):
        # Columnas oficiales ahora con CEDULA
        columnas = [
            'CEDULA', 'TELEFONO', 'NOMBRES', 'APELLIDOS', 'EMAIL', 'FECHA_NACIMIENTO', 'EDAD', 
            'CIUDAD', 'DIRECCION', 'CODIGO_FARMACIA', 'MEDICAMENTO'
        ]
        df = pd.DataFrame(columns=columnas)
        
        # Filas de ejemplo para ayudar al usuario
        df.loc[0] = ['0912345678', '0991234567', 'Ejemplo (Juan S.)', 'Perez', 'juan@ejemplo.com', '1990-05-15', '', 'Guayaquil', 'Av. 9 de Octubre', 'FARM-01', 'Paracetamol']
        df.loc[1] = ['0987654321', '0987654321', 'Ejemplo (Maria R.)', 'Gomez', '', '', '45', 'Quito', 'Sector La Carolina', 'FARM-02', 'Ibuprofeno']

        excel_file = BytesIO()
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Plantilla CRM')

        excel_file.seek(0)
        response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Plantilla_Importacion_Leads_v2.xlsx"'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response


# --- FASE 11: Campañas de Marketing ---
from django.views.generic import CreateView
from .models import CampanaDifusion

class CampanaListView(GestorCrmMixin, ListView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_list.html'
    context_object_name = 'campanas'

class CampanaCreateView(GestorCrmMixin, CreateView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_form.html'
    fields = [
        'nombre', 'mensaje_plantilla', 
        'ciudades_objetivo', 'etiquetas_objetivo', 'farmacias_objetivo', 'medicamentos_objetivo',
        'edad_minima', 'edad_maxima', 'fecha_programada'
    ]
    success_url = reverse_lazy('crm_marketing:campaign_list')

    def get_form(self, form_class=None):
        from django import forms
        form = super().get_form(form_class)
        form.fields['fecha_programada'].widget = forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control input-lg'})
        return form
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Convertir campo de fecha_programada a datetime-local
        form.fields['fecha_programada'].widget = forms.DateTimeInput(attrs={'type': 'datetime-local'})
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Cargamos los querysets para que el template pinte selectores bonitos (Select2)
        context['ciudades'] = Ciudad.objects.filter(activa=True)
        context['farmacias'] = Farmacia.objects.all()
        context['etiquetas'] = Etiqueta.objects.all()
        context['productos'] = ProductoCRM.objects.all()
        return context

class CampanaDetailView(GestorCrmMixin, DetailView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_detail.html'
    context_object_name = 'campana'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Inyecta al template los usuarios que pasaron el filtro para previsualizar
        audiencia_qs = self.object.get_audiencia()
        context['audiencia_total'] = audiencia_qs.count()
        context['contactos_preview'] = audiencia_qs[:50] # Mostrar los primeros 50 para no colgar el navegador
        return context

from django.shortcuts import redirect
from .models import MensajeCampana
from django import forms

class CampanaUpdateView(GestorCrmMixin, UpdateView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_form.html'
    fields = [
        'nombre', 'mensaje_plantilla', 
        'ciudades_objetivo', 'etiquetas_objetivo', 'farmacias_objetivo', 'medicamentos_objetivo',
        'edad_minima', 'edad_maxima', 'fecha_programada'
    ]
    success_url = reverse_lazy('crm_marketing:campaign_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['fecha_programada'].widget = forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control input-lg'})
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ciudades'] = Ciudad.objects.filter(activa=True)
        context['farmacias'] = Farmacia.objects.all()
        context['etiquetas'] = Etiqueta.objects.all()
        context['productos'] = ProductoCRM.objects.all()
        context['is_update'] = True
        return context

class CampaignPreviewView(GestorCrmMixin, DetailView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_preview.html'
    context_object_name = 'campana'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.estado != 'BORRADOR':
            messages.warning(self.request, "Esta campaña ya no está en borrador.")
        audiencia_qs = self.object.get_audiencia()
        context['audiencia_total'] = audiencia_qs.count()
        context['contactos_preview'] = audiencia_qs[:50]
        return context

class CampaignExecuteView(GestorCrmMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            campana = CampanaDifusion.objects.get(pk=pk, estado='BORRADOR')
            audiencia = campana.get_audiencia()
            
            mensajes_creados = 0
            for contacto in audiencia:
                obj, created = MensajeCampana.objects.get_or_create(
                    campana=campana,
                    contacto=contacto,
                    defaults={'estado': 'PENDIENTE'}
                )
                if created: mensajes_creados += 1
            
            campana.estado = 'PROGRAMADA'
            campana.save()
            
            messages.success(request, f"🚀 Campaña iniciada. Se han encolado {mensajes_creados} mensajes exitosamente.")
        except CampanaDifusion.DoesNotExist:
            messages.error(request, "La campaña no existe o ya fue lanzada.")
        
        return redirect('crm_marketing:campaign_list')

class CampaignReportView(GestorCrmMixin, DetailView):
    model = CampanaDifusion
    template_name = 'crm_marketing/campaign_report.html'
    context_object_name = 'campana'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traemos todos los mensajes que se generaron en la cola para esta campaña
        mensajes = self.object.mensajes_cola.all().select_related('contacto', 'contacto__ciudad').order_by('-fecha_creacion')
        context['mensajes'] = mensajes
        
        # Estadísticas rápidas
        context['total'] = mensajes.count()
        context['enviados'] = mensajes.filter(estado='ENVIADO').count()
        context['leidos'] = mensajes.filter(estado='LEIDO').count()
        context['pendientes'] = mensajes.filter(estado='PENDIENTE').count()
        context['errores'] = mensajes.filter(estado='ERROR').count()
        return context

# --- FASE 11.5: Gestión de Etiquetas CRM ---
class EtiquetaListView(GestorCrmMixin, ListView):
    model = Etiqueta
    template_name = 'crm_marketing/etiqueta_list.html'
    context_object_name = 'etiquetas'
    
class EtiquetaCreateView(GestorCrmMixin, CreateView):
    model = Etiqueta
    template_name = 'crm_marketing/etiqueta_form.html'
    fields = ['nombre', 'color']
    success_url = reverse_lazy('crm_marketing:etiqueta_list')
    
    def get_success_url(self):
        messages.success(self.request, "Etiqueta creada exitosamente.")
        return super().get_success_url()

class EtiquetaUpdateView(GestorCrmMixin, UpdateView):
    model = Etiqueta
    template_name = 'crm_marketing/etiqueta_form.html'
    fields = ['nombre', 'color']
    success_url = reverse_lazy('crm_marketing:etiqueta_list')

    def get_success_url(self):
        messages.success(self.request, "Etiqueta actualizada exitosamente.")
        return super().get_success_url()

class EtiquetaDeleteView(GestorCrmMixin, DeleteView):
    model = Etiqueta
    template_name = 'crm_marketing/etiqueta_confirm_delete.html'
    success_url = reverse_lazy('crm_marketing:etiqueta_list')
from django.views.generic import ListView, DetailView, FormView, UpdateView, View, CreateView, DeleteView, TemplateView
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

class PipelineBoardView(GestorCrmMixin, TemplateView):
    """Renderiza el tablero Kanban con las columnas de etapas comerciales"""
    template_name = 'crm_marketing/pipeline_board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        etapas = [
            {'id': 'LEAD', 'nombre': 'Lead Entrante'},
            {'id': 'CONTACTADO', 'nombre': 'Primer Contacto'},
            {'id': 'NEGOCIACION', 'nombre': 'En Negociación'},
            {'id': 'GANADO', 'nombre': 'Venta Cerrada (Éxito)'},
            {'id': 'PERDIDO', 'nombre': 'Venta Perdida'},
        ]
        
        # Agrupar contactos por etapa
        columnas = []
        for e in etapas:
            contactos_en_etapa = CrmContact.objects.filter(etapa_comercial=e['id']).order_by('-fecha_registro')
            columnas.append({
                'etapa': e,
                'contactos': contactos_en_etapa
            })
            
        context['columnas'] = columnas
        return context

@method_decorator(csrf_exempt, name='dispatch')
class UpdateContactStageAPIView(GestorCrmMixin, View):
    """Endpoint para actualizar la etapa de un contacto al moverlo en el Kanban"""
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            contacto_id = data.get('contacto_id')
            nueva_etapa = data.get('etapa')
            
            # Validar etapa
            valid_stages = [e[0] for e in CrmContact.ETAPAS_CHOICES]
            if nueva_etapa not in valid_stages:
                return JsonResponse({'error': 'Etapa no válida'}, status=400)
            
            contacto = CrmContact.objects.get(id=contacto_id)
            contacto.etapa_comercial = nueva_etapa
            contacto.save(update_fields=['etapa_comercial'])
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


